#!/usr/bin/env python3
"""기존 실제 MR60 JSONL을 현행 adapter와 V5 TFLite로 batch replay한다."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time
from typing import Any, Callable, Iterable

import numpy as np


TOOL_VERSION = "0.1.0"
REPO_ROOT = Path(__file__).resolve().parents[3]
ONDEVICE_AI_ROOT = REPO_ROOT / "ondevice_ai"
for search_path in (REPO_ROOT, ONDEVICE_AI_ROOT):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

from devices.mmwave.src.mr60_esp_adapter import MR60ESPAdapter
from inference.mmwave_interpreter import MMWaveInterpreter


ProgressCallback = Callable[[str, int, int, int, int], None]
EXPECTED_HISTORY_ERRORS = {"MMWAVE_WARMUP", "MMWAVE_WINDOW_NOT_READY"}


def finite_number(value: object) -> bool:
    return (
        not isinstance(value, (bool, np.bool_))
        and isinstance(value, (int, float, np.number))
        and bool(np.isfinite(value))
    )


def percentile(values: Iterable[float], fraction: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def numeric_stats(values: Iterable[float]) -> dict[str, float | int | None]:
    samples = [float(value) for value in values]
    if not samples:
        return {"count": 0, "mean": None, "p50": None, "p95": None, "max": None}
    return {
        "count": len(samples),
        "mean": statistics.fmean(samples),
        "p50": percentile(samples, 0.5),
        "p95": percentile(samples, 0.95),
        "max": max(samples),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def provenance_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT))
    except ValueError:
        return str(path.resolve())


def git_value(*args: str) -> str | None:
    result = subprocess.run(
        ["git", *args], cwd=REPO_ROOT, text=True, capture_output=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


@dataclass(frozen=True)
class DatasetSpec:
    id: str
    path: Path
    scenario: str = "unknown"
    classification: str = "UNKNOWN"
    real_hardware: bool | None = None
    strict_provenance: bool = False
    presence_ground_truth: str | None = None
    ai_class_ground_truth: str | None = None
    reference_respiration_rpm: float | None = None
    analysis_start_s: float = 0.0
    analysis_duration_s: float | None = None
    measurement_stage: str | None = None

    @classmethod
    def from_dict(cls, item: dict[str, Any]) -> "DatasetSpec":
        source = Path(item["path"])
        if not source.is_absolute():
            source = REPO_ROOT / source
        return cls(
            id=str(item["id"]),
            path=source,
            scenario=str(item.get("scenario", "unknown")),
            classification=str(item.get("classification", "UNKNOWN")),
            real_hardware=(
                bool(item["real_hardware"])
                if "real_hardware" in item
                else str(item.get("classification", "UNKNOWN")).startswith("REAL_")
            ),
            strict_provenance=bool(item.get("strict_provenance", False)),
            presence_ground_truth=item.get("presence_ground_truth"),
            ai_class_ground_truth=item.get("ai_class_ground_truth"),
            reference_respiration_rpm=(
                float(item["reference_respiration_rpm"])
                if item.get("reference_respiration_rpm") is not None
                else None
            ),
            analysis_start_s=float(item.get("analysis_start_s", 0.0)),
            analysis_duration_s=(
                float(item["analysis_duration_s"])
                if item.get("analysis_duration_s") is not None
                else None
            ),
            measurement_stage=item.get("measurement_stage"),
        )


def load_jsonl(path: Path) -> tuple[list[dict[str, Any]], int, int]:
    records: list[dict[str, Any]] = []
    invalid_json = 0
    total_lines = 0
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            total_lines += 1
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                invalid_json += 1
                continue
            if isinstance(item, dict):
                records.append(item)
            else:
                invalid_json += 1
    return records, total_lines, invalid_json


def sensor_records(records: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in records if item.get("kind", "sensor") == "sensor"]


def resolve_analysis_bounds(
    spec: DatasetSpec,
    records: list[dict[str, Any]],
    sensors: list[dict[str, Any]],
) -> tuple[float, float | None]:
    first_sensor_ms = next(
        float(item["ts_monotonic_ms"])
        for item in sensors
        if finite_number(item.get("ts_monotonic_ms"))
    )
    start_ms = first_sensor_ms + spec.analysis_start_s * 1000.0
    if spec.measurement_stage:
        cue_ns = [
            int(item["host_monotonic_ns"])
            for item in records
            if item.get("kind") == "cue"
            and item.get("stage") == spec.measurement_stage
            and isinstance(item.get("host_monotonic_ns"), int)
        ]
        if not cue_ns:
            raise ValueError(f"{spec.id}: measurement stage cue가 없습니다")
        first_cue_ns = min(cue_ns)
        matching = [
            item for item in sensors
            if isinstance(item.get("host_monotonic_ns"), int)
            and item["host_monotonic_ns"] >= first_cue_ns
            and finite_number(item.get("ts_monotonic_ms"))
        ]
        if not matching:
            raise ValueError(f"{spec.id}: measurement cue 이후 센서 샘플이 없습니다")
        start_ms = float(matching[0]["ts_monotonic_ms"])
    end_ms = (
        start_ms + spec.analysis_duration_s * 1000.0
        if spec.analysis_duration_s is not None
        else None
    )
    return start_ms, end_ms


def counter_increase(records: list[dict[str, Any]], key: str) -> int:
    total = 0
    previous: int | None = None
    for item in records:
        value = item.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            continue
        if previous is not None and value > previous:
            total += value - previous
        previous = value
    return total


def quality_metrics(
    sensors: list[dict[str, Any]], config: dict[str, Any]
) -> dict[str, Any]:
    timestamps = [
        float(item["ts_monotonic_ms"]) / 1000.0
        for item in sensors
        if finite_number(item.get("ts_monotonic_ms"))
    ]
    intervals = [b - a for a, b in zip(timestamps, timestamps[1:]) if b > a]
    sequences = [
        int(item["seq"])
        for item in sensors
        if isinstance(item.get("seq"), int) and not isinstance(item.get("seq"), bool)
    ]
    dropped = sum(max(0, b - a - 1) for a, b in zip(sequences, sequences[1:]) if b > a)
    nonmonotonic = sum(b <= a for a, b in zip(sequences, sequences[1:]))
    presence = [
        item.get("human_detected_stable", item.get("human_detected_raw"))
        for item in sensors
    ]
    distance_valid = 0
    phase_finite = 0
    phase_usable = 0
    stale = 0
    for item, present in zip(sensors, presence):
        distance = item.get("distance_cm_raw")
        distance_ok = (
            finite_number(distance)
            and float(config["distance_min_cm"]) <= float(distance) <= float(config["distance_max_cm"])
        )
        phase = item.get("breath_phase")
        phase_ok = finite_number(phase)
        phase_age = item.get("phase_age_ms")
        fresh = finite_number(phase_age) and float(phase_age) <= float(config["max_phase_age_ms"])
        distance_valid += int(distance_ok)
        phase_finite += int(phase_ok)
        phase_usable += int(present is True and distance_ok and phase_ok and fresh)
        stale += int(not fresh)
    duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else None
    return {
        "sensor_records": len(sensors),
        "schema_versions": dict(Counter(str(item.get("schema_version")) for item in sensors)),
        "duration_s": duration,
        "effective_sample_rate_hz": (
            (len(timestamps) - 1) / duration if duration and duration > 0 else None
        ),
        "sample_interval_s": numeric_stats(intervals),
        "sequence_drops": dropped,
        "nonmonotonic_sequences": nonmonotonic,
        "uart_bad_records": sum(item.get("uart_frame_ok") is not True for item in sensors),
        "checksum_bad_records": sum(item.get("checksum_ok") is not True for item in sensors),
        "checksum_error_increase": counter_increase(sensors, "checksum_errors"),
        "parser_error_increase": counter_increase(sensors, "parse_errors"),
        "presence_true": sum(value is True for value in presence),
        "presence_false": sum(value is False for value in presence),
        "presence_unknown": sum(value not in (True, False) for value in presence),
        "distance_valid": distance_valid,
        "breath_phase_finite": phase_finite,
        "breath_phase_usable": phase_usable,
        "invalid_or_nonfinite_phase": len(sensors) - phase_finite,
        "stale_phase_records": stale,
        "stream_gap_count": sum(
            interval > float(config["max_gap_seconds"]) for interval in intervals
        ),
        "maximum_gap_s": max(intervals) if intervals else None,
    }


def entry_exit_metrics(records: list[dict[str, Any]]) -> dict[str, Any] | None:
    sensors = sorted(
        [item for item in records if item.get("kind") == "sensor"],
        key=lambda item: item.get("host_monotonic_ns", 0),
    )
    beeps = sorted(
        [item for item in records if item.get("kind") == "beep"],
        key=lambda item: item.get("host_monotonic_ns", 0),
    )
    if not beeps:
        return None

    def entry_latency(beep_ns: int, max_wait_s: float = 20.0) -> float | None:
        for item in sensors:
            host_ns = item.get("host_monotonic_ns")
            if not isinstance(host_ns, int) or host_ns < beep_ns:
                continue
            elapsed = (host_ns - beep_ns) / 1e9
            if elapsed > max_wait_s:
                return None
            if item.get("human_detected_raw") is True:
                return elapsed
        return None

    def exit_latency(beep_ns: int, max_wait_s: float = 20.0) -> float | None:
        consecutive = 0
        started_ns: int | None = None
        for item in sensors:
            host_ns = item.get("host_monotonic_ns")
            if not isinstance(host_ns, int) or host_ns < beep_ns:
                continue
            elapsed = (host_ns - beep_ns) / 1e9
            if elapsed > max_wait_s:
                return None
            if item.get("human_detected_raw") is False:
                if consecutive == 0:
                    started_ns = host_ns
                consecutive += 1
                if consecutive >= 5 and started_ns is not None:
                    return (started_ns - beep_ns) / 1e9
            else:
                consecutive = 0
                started_ns = None
        return None

    trials: list[dict[str, Any]] = []
    for beep in beeps:
        event = beep.get("event")
        host_ns = beep.get("host_monotonic_ns")
        if not isinstance(host_ns, int) or event not in {"enter", "exit"}:
            continue
        latency = entry_latency(host_ns) if event == "enter" else exit_latency(host_ns)
        trials.append({"trial": beep.get("trial"), "event": event, "latency_s": latency})
    entry = [item["latency_s"] for item in trials if item["event"] == "enter" and item["latency_s"] is not None]
    exit_values = [item["latency_s"] for item in trials if item["event"] == "exit" and item["latency_s"] is not None]
    enter_total = sum(item["event"] == "enter" for item in trials)
    exit_total = sum(item["event"] == "exit" for item in trials)
    return {
        "trials": trials,
        "entry_total": enter_total,
        "entry_success": len(entry),
        "entry_missed": enter_total - len(entry),
        "entry_latency_s": numeric_stats(entry),
        "entry_kpi_le_2s": sum(value <= 2.0 for value in entry),
        "exit_total": exit_total,
        "exit_release_success": len(exit_values),
        "exit_release_missed": exit_total - len(exit_values),
        "exit_latency_s": numeric_stats(exit_values),
        "exit_kpi_le_2s": sum(value <= 2.0 for value in exit_values),
        "vendor_hysteresis_dominates": bool(exit_values and statistics.median(exit_values) >= 10.0),
    }


def dataset_status(spec: DatasetSpec, summary: dict[str, Any]) -> str:
    if summary["fallback_count"]:
        return "FAIL"
    if spec.presence_ground_truth == "ABSENT":
        if summary["completed_windows"] or summary["prediction_distribution"]:
            return "FAIL"
        return "PASS"
    if summary["attempted_windows"] and not summary["completed_windows"]:
        return "PARTIAL"
    detection_rate = summary["presence"]["detection_rate"]
    if detection_rate is not None and detection_rate < 0.95:
        return "PARTIAL"
    success_rate = summary["window_success_rate"]
    if success_rate is not None and success_rate < 0.8:
        return "PARTIAL"
    return "PASS"


def benchmark_dataset(
    spec: DatasetSpec,
    interpreter: Any,
    *,
    git_commit: str | None,
    progress: ProgressCallback | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not spec.path.is_file():
        raise FileNotFoundError(spec.path)
    records, total_lines, invalid_json = load_jsonl(spec.path)
    sensors = sensor_records(records)
    if not sensors:
        raise ValueError(f"{spec.id}: 센서 레코드가 없습니다")
    adapter = MR60ESPAdapter(strict_provenance=spec.strict_provenance)
    raw_quality = quality_metrics(sensors, adapter.config)
    start_ms, end_ms = resolve_analysis_bounds(spec, records, sensors)
    analysis_sensors = [
        item for item in sensors
        if finite_number(item.get("ts_monotonic_ms"))
        and float(item["ts_monotonic_ms"]) >= start_ms
        and (end_ms is None or float(item["ts_monotonic_ms"]) < end_ms)
    ]
    analysis_quality = quality_metrics(analysis_sensors, adapter.config)

    attempted = completed = rejected = fallback_count = 0
    active = False
    reset_reasons: Counter[str] = Counter()
    adapter_reasons: Counter[str] = Counter()
    predictions: Counter[str] = Counter()
    model_latencies: list[float] = []
    respiration_estimates: list[float] = []
    windows: list[dict[str, Any]] = []
    current_valid_run = longest_valid_run = 0
    analysis_started = False
    processed_analysis = 0
    progress_step = max(1, len(analysis_sensors) // 20)

    for item in sensors:
        timestamp_ms = item.get("ts_monotonic_ms")
        if not finite_number(timestamp_ms):
            continue
        timestamp_ms = float(timestamp_ms)
        if timestamp_ms < start_ms:
            adapter.process(item)
            continue
        if end_ms is not None and timestamp_ms >= end_ms:
            break
        if not analysis_started:
            adapter.estimator.reset("MMWAVE_REPLAY_ANALYSIS_START")
            analysis_started = True

        before_count = len(adapter.estimator.values)
        packet = adapter.process(item)
        mmwave = packet["mmwave_mr60"]
        after_count = len(adapter.estimator.values)
        reason = mmwave.get("fault_reason")
        adapter_reasons[reason or "VALID"] += 1
        processed_analysis += 1

        if not active and after_count > 0:
            active = True
            attempted += 1

        if mmwave["valid"]:
            window = np.asarray(adapter.estimator.values, dtype=np.float32)
            estimate_rpm = mmwave.get("breath_rpm")
            if finite_number(estimate_rpm):
                respiration_estimates.append(float(estimate_rpm))
            prediction = interpreter.predict(window)
            fallback_count += int(prediction.fallback_used)
            if not prediction.fallback_used:
                predictions[prediction.class_name] += 1
                model_latencies.append(float(prediction.latency_ms))
            completed += 1
            current_valid_run += 1
            longest_valid_run = max(longest_valid_run, current_valid_run)
            windows.append({
                "kind": "replay_window",
                "dataset_id": spec.id,
                "source_file": provenance_path(spec.path),
                "window_index": completed,
                "window_end_timestamp_s": float(packet["timestamp_s"]),
                "window_samples": len(window),
                "estimated_respiration_rpm": float(estimate_rpm) if finite_number(estimate_rpm) else None,
                "reference_respiration_rpm": spec.reference_respiration_rpm,
                "model_id": prediction.model_id,
                "model_version": prediction.model_version,
                "class_index": prediction.class_index,
                "class_name": prediction.class_name,
                "confidence": prediction.confidence,
                "probabilities": prediction.probabilities,
                "model_inference_latency_ms": prediction.latency_ms,
                "fallback_used": prediction.fallback_used,
                "fallback_reason": prediction.fallback_reason,
                "ai_class_ground_truth": spec.ai_class_ground_truth,
            })
            adapter.estimator.reset("MMWAVE_REPLAY_WINDOW_COMPLETE")
            active = False
        else:
            if reason not in EXPECTED_HISTORY_ERRORS:
                current_valid_run = 0
            reset_during_window = active and before_count > 0 and after_count == 0
            invalid_full_window = (
                active
                and after_count >= adapter.estimator.window_samples
                and reason not in EXPECTED_HISTORY_ERRORS
            )
            if reset_during_window or invalid_full_window:
                rejected += 1
                reset_reasons[reason or "MMWAVE_WINDOW_INVALID"] += 1
                current_valid_run = 0
                active = False
                if invalid_full_window:
                    adapter.estimator.reset(reason or "MMWAVE_WINDOW_INVALID")

        if progress and (processed_analysis % progress_step == 0 or processed_analysis == len(analysis_sensors)):
            progress(spec.id, processed_analysis, len(analysis_sensors), completed, fallback_count)

    if active and len(adapter.estimator.values):
        rejected += 1
        reset_reasons["MMWAVE_INSUFFICIENT_HISTORY"] += 1
        current_valid_run = 0

    presence_total = (
        analysis_quality["presence_true"]
        + analysis_quality["presence_false"]
        + analysis_quality["presence_unknown"]
    )
    presence_metrics: dict[str, Any] = {
        "ground_truth": spec.presence_ground_truth,
        "detection_rate": None,
        "false_presence_rate": None,
    }
    if spec.presence_ground_truth == "PRESENT" and presence_total:
        presence_metrics["detection_rate"] = analysis_quality["presence_true"] / presence_total
    elif spec.presence_ground_truth == "ABSENT" and presence_total:
        presence_metrics["false_presence_rate"] = analysis_quality["presence_true"] / presence_total

    respiration_metrics: dict[str, Any] = {
        "ground_truth_rpm": spec.reference_respiration_rpm,
        "window_estimates_rpm": respiration_estimates,
        "estimated_rpm_mean": statistics.fmean(respiration_estimates) if respiration_estimates else None,
        "absolute_errors_rpm": [],
        "mae_rpm": None,
        "max_absolute_error_rpm": None,
        "within_2rpm_count": None,
        "within_2rpm_rate": None,
    }
    if spec.reference_respiration_rpm is not None and respiration_estimates:
        errors = [abs(value - spec.reference_respiration_rpm) for value in respiration_estimates]
        respiration_metrics.update({
            "absolute_errors_rpm": errors,
            "mae_rpm": statistics.fmean(errors),
            "max_absolute_error_rpm": max(errors),
            "within_2rpm_count": sum(error <= 2.0 for error in errors),
            "within_2rpm_rate": sum(error <= 2.0 for error in errors) / len(errors),
        })

    class_accuracy = None
    if spec.ai_class_ground_truth and completed and fallback_count == 0:
        class_accuracy = predictions[spec.ai_class_ground_truth] / completed

    summary: dict[str, Any] = {
        "dataset_id": spec.id,
        "scenario": spec.scenario,
        "classification": spec.classification,
        "real_hardware": spec.real_hardware,
        "source_file": provenance_path(spec.path),
        "source_sha256": sha256_file(spec.path),
        "source_git_commit": (
            git_value("log", "-1", "--format=%H", "--", provenance_path(spec.path))
            if spec.path.resolve().is_relative_to(REPO_ROOT)
            else None
        ),
        "source_total_lines": total_lines,
        "valid_json_lines": len(records),
        "invalid_json_lines": invalid_json,
        "strict_provenance": spec.strict_provenance,
        "analysis_start_s": (start_ms - float(sensors[0]["ts_monotonic_ms"])) / 1000.0,
        "analysis_duration_requested_s": spec.analysis_duration_s,
        "raw_quality": raw_quality,
        "analysis_quality": analysis_quality,
        "presence": presence_metrics,
        "entry_exit": entry_exit_metrics(records) if spec.presence_ground_truth == "ENTRY_EXIT" else None,
        "attempted_windows": attempted,
        "completed_windows": completed,
        "rejected_windows": rejected,
        "window_success_rate": completed / (completed + rejected) if completed + rejected else None,
        "reset_reasons": dict(reset_reasons),
        "adapter_event_reasons": dict(adapter_reasons),
        "longest_continuous_valid_inference_windows": longest_valid_run,
        "longest_continuous_valid_inference_s": longest_valid_run * 30.0,
        "tflite_runs": completed - fallback_count,
        "fallback_count": fallback_count,
        "prediction_distribution": dict(predictions),
        "model_latency_ms": numeric_stats(model_latencies),
        "respiration_rate": respiration_metrics,
        "ai_class_ground_truth": spec.ai_class_ground_truth,
        "classification_accuracy": class_accuracy,
        "classification_accuracy_note": (
            None
            if spec.ai_class_ground_truth
            else "해당 데이터에는 신뢰 가능한 NORMAL/ABNORMAL/APNEA ground truth가 없으므로 분류 정확도를 계산하지 않았습니다."
        ),
        "model_id": getattr(interpreter, "model_meta", {}).get("model_id"),
        "model_version": getattr(interpreter, "model_meta", {}).get("version"),
        "model_sha256": getattr(interpreter, "sha256_hash", None),
        "model_sha256_matches": getattr(interpreter, "sha256_matches", None),
        "benchmark_tool_version": TOOL_VERSION,
        "benchmark_tool_git_commit": git_commit,
    }
    summary["result"] = dataset_status(spec, summary)
    return summary, windows


def terminal_progress(dataset_id: str, current: int, total: int, windows: int, fallback: int) -> None:
    ratio = current / total if total else 1.0
    width = 20
    filled = round(ratio * width)
    bar = "█" * filled + "-" * (width - filled)
    print(
        f"\r{dataset_id:<28} [{bar}] {ratio:6.1%}  records={current}/{total} "
        f"windows={windows} fallback={fallback}",
        end="",
        flush=True,
    )
    if current >= total:
        print()


def short_result(summary: dict[str, Any]) -> None:
    latency = summary["model_latency_ms"]
    print(
        f"  결과={summary['result']} windows={summary['completed_windows']}/"
        f"{summary['attempted_windows']} TFLite={summary['tflite_runs']} "
        f"prediction={summary['prediction_distribution']} fallback={summary['fallback_count']} "
        f"latency_p95={latency['p95']} ms"
    )


def write_outputs(
    output_dir: Path,
    summaries: list[dict[str, Any]],
    windows_by_dataset: dict[str, list[dict[str, Any]]],
    provenance: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    summaries_dir = output_dir / "datasets"
    windows_dir = output_dir / "windows"
    summaries_dir.mkdir()
    windows_dir.mkdir()
    for summary in summaries:
        dataset_id = summary["dataset_id"]
        (summaries_dir / f"{dataset_id}.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        with (windows_dir / f"{dataset_id}.jsonl").open("x", encoding="utf-8") as stream:
            for window in windows_by_dataset[dataset_id]:
                stream.write(json.dumps(window, ensure_ascii=False, allow_nan=False) + "\n")

    total = {
        "benchmark_id": output_dir.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provenance": provenance,
        "datasets": summaries,
    }
    (output_dir / "benchmark_summary.json").write_text(
        json.dumps(total, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    columns = [
        "dataset_id", "scenario", "classification", "result", "source_total_lines",
        "attempted_windows", "completed_windows", "rejected_windows", "window_success_rate",
        "tflite_runs", "fallback_count", "prediction_distribution", "model_latency_p95_ms",
        "presence_detection_rate", "false_presence_rate", "respiration_mae_rpm",
    ]
    with (output_dir / "benchmark_summary.csv").open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for summary in summaries:
            writer.writerow({
                "dataset_id": summary["dataset_id"],
                "scenario": summary["scenario"],
                "classification": summary["classification"],
                "result": summary["result"],
                "source_total_lines": summary["source_total_lines"],
                "attempted_windows": summary["attempted_windows"],
                "completed_windows": summary["completed_windows"],
                "rejected_windows": summary["rejected_windows"],
                "window_success_rate": summary["window_success_rate"],
                "tflite_runs": summary["tflite_runs"],
                "fallback_count": summary["fallback_count"],
                "prediction_distribution": json.dumps(summary["prediction_distribution"], ensure_ascii=False),
                "model_latency_p95_ms": summary["model_latency_ms"]["p95"],
                "presence_detection_rate": summary["presence"]["detection_rate"],
                "false_presence_rate": summary["presence"]["false_presence_rate"],
                "respiration_mae_rpm": summary["respiration_rate"]["mae_rpm"],
            })
    (output_dir / "REPORT_KO.md").write_text(render_report(summaries, provenance), encoding="utf-8")


def percent(value: float | None) -> str:
    return "-" if value is None else f"{value * 100:.2f}%"


def render_report(summaries: list[dict[str, Any]], provenance: dict[str, Any]) -> str:
    lines = [
        "# 기존 MR60 실측 데이터 V5 Replay Benchmark",
        "",
        f"- 도구 버전: `{TOOL_VERSION}`",
        f"- Git commit: `{provenance.get('git_commit')}`",
        f"- 모델: `{provenance.get('model_id')}` v{provenance.get('model_version')}",
        f"- 모델 SHA-256: `{provenance.get('model_sha256')}`",
        "",
        "| Dataset | Scenario | Records | Windows | Success | TFLite | Prediction | Fallback | p95 ms | Result |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---|",
    ]
    for summary in summaries:
        lines.append(
            f"| {summary['dataset_id']} | {summary['scenario']} | {summary['analysis_quality']['sensor_records']} "
            f"| {summary['completed_windows']}/{summary['attempted_windows']} | {percent(summary['window_success_rate'])} "
            f"| {summary['tflite_runs']} | `{summary['prediction_distribution']}` | {summary['fallback_count']} "
            f"| {summary['model_latency_ms']['p95'] if summary['model_latency_ms']['p95'] is not None else '-'} "
            f"| {summary['result']} |"
        )
    lines.extend(["", "분류 정확도는 명시적인 AI class ground truth가 있는 데이터에서만 계산합니다.", ""])
    return "\n".join(lines)


def load_specs(args: argparse.Namespace) -> list[DatasetSpec]:
    if args.input:
        source = args.input.resolve()
        return [DatasetSpec(id=source.stem, path=source, classification="UNKNOWN")]
    if args.input_dir:
        return [
            DatasetSpec(id=path.stem, path=path.resolve(), classification="UNKNOWN")
            for path in sorted(args.input_dir.glob("*.jsonl"))
        ]
    manifest = args.manifest or Path(__file__).with_name("mmwave_replay_suite.json")
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    return [DatasetSpec.from_dict(item) for item in payload["datasets"]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--input", type=Path)
    source.add_argument("--input-dir", type=Path)
    source.add_argument("--manifest", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--no-progress", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    specs = load_specs(args)
    if not specs:
        print("Replay 대상이 없습니다.", file=sys.stderr)
        return 2
    interpreter = MMWaveInterpreter(project_root=ONDEVICE_AI_ROOT)
    git_commit = git_value("rev-parse", "HEAD")
    provenance = {
        "git_commit": git_commit,
        "benchmark_tool_version": TOOL_VERSION,
        "model_id": interpreter.model_meta["model_id"],
        "model_version": interpreter.model_meta["version"],
        "model_sha256": interpreter.sha256_hash,
        "model_sha256_matches": interpreter.sha256_matches,
        "fallback_load_reason": interpreter.load_error_reason,
    }
    summaries: list[dict[str, Any]] = []
    windows_by_dataset: dict[str, list[dict[str, Any]]] = {}
    callback = None if args.no_progress else terminal_progress
    print("SafeNest mmWave V5 Replay Benchmark")
    print("=" * 72)
    for index, spec in enumerate(specs, 1):
        print(f"[{index}/{len(specs)}] {spec.id}: {spec.scenario}")
        started = time.perf_counter()
        summary, windows = benchmark_dataset(
            spec, interpreter, git_commit=git_commit, progress=callback
        )
        summary["benchmark_elapsed_s"] = time.perf_counter() - started
        summaries.append(summary)
        windows_by_dataset[spec.id] = windows
        short_result(summary)

    output_dir = args.output_dir
    if output_dir is None:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = REPO_ROOT / "devices/mmwave/validation_results/replay_v5" / stamp
    elif not output_dir.is_absolute():
        output_dir = REPO_ROOT / output_dir
    write_outputs(output_dir, summaries, windows_by_dataset, provenance)
    print("=" * 72)
    print(f"완료: {len(summaries)}개 데이터셋, 결과={output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
