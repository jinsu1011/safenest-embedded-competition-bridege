#!/usr/bin/env python3
"""Historical MR60 replay에서 rolling 품질 정책을 production 변경 없이 비교한다."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys
import time
from typing import Any

import numpy as np


TOOL_VERSION = "0.1.0"
REPO_ROOT = Path(__file__).resolve().parents[3]
ONDEVICE_AI_ROOT = REPO_ROOT / "ondevice_ai"
for search_path in (REPO_ROOT, ONDEVICE_AI_ROOT, Path(__file__).resolve().parent):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

from devices.mmwave.src.mr60_esp_adapter import MR60ESPAdapter
from inference.mmwave_interpreter import MMWaveInterpreter
from mmwave_v5_replay_benchmark import (
    EXPECTED_HISTORY_ERRORS,
    DatasetSpec,
    dataset_status,
    entry_exit_metrics,
    finite_number,
    git_value,
    load_jsonl,
    load_specs,
    numeric_stats,
    provenance_path,
    quality_metrics,
    resolve_analysis_bounds,
    sensor_records,
    sha256_file,
)


@dataclass(frozen=True)
class PolicyConfig:
    name: str
    enter_peak_ratio: float | None = None
    remain_peak_ratio: float | None = None
    temporal_floor_peak_ratio: float | None = None
    temporal_max_delta_rpm: float | None = None
    minimum_peak_dominance: float | None = None
    reanchor_peak_ratio: float | None = None


POLICIES = {
    "baseline": PolicyConfig("baseline"),
    "candidate_a_rolling_peak": PolicyConfig(
        "candidate_a_rolling_peak", enter_peak_ratio=2.0
    ),
    "candidate_b_temporal": PolicyConfig(
        "candidate_b_temporal",
        enter_peak_ratio=2.0,
        temporal_floor_peak_ratio=1.5,
        temporal_max_delta_rpm=2.0,
    ),
    "candidate_c_hysteresis": PolicyConfig(
        "candidate_c_hysteresis", enter_peak_ratio=2.0, remain_peak_ratio=1.5
    ),
    "candidate_d_peak_dominance": PolicyConfig(
        "candidate_d_peak_dominance",
        enter_peak_ratio=2.0,
        minimum_peak_dominance=2.0,
    ),
    "candidate_e_temporal_reanchor": PolicyConfig(
        "candidate_e_temporal_reanchor",
        enter_peak_ratio=5.0,
        temporal_floor_peak_ratio=1.5,
        temporal_max_delta_rpm=2.0,
        reanchor_peak_ratio=5.0,
    ),
}


@dataclass(frozen=True)
class QualityDecision:
    accept: bool
    reason: str
    threshold: float | None


class QualityPolicy:
    """Adapter 밖에서 동작하는 diagnostic-only state machine."""

    def __init__(self, config: PolicyConfig) -> None:
        self.config = config
        self.previous_valid_rpm: float | None = None
        self.valid_latched = False

    def physical_reset(self) -> None:
        self.previous_valid_rpm = None
        self.valid_latched = False

    def decide(
        self,
        rate_rpm: float,
        peak_ratio: float,
        peak_dominance: float | None = None,
    ) -> QualityDecision:
        if self.config.name == "baseline":
            return QualityDecision(True, "BASELINE_ACCEPT", None)

        if self.config.name == "candidate_e_temporal_reanchor":
            reanchor = float(self.config.reanchor_peak_ratio)
            if peak_ratio >= reanchor:
                self.previous_valid_rpm = rate_rpm
                self.valid_latched = True
                return QualityDecision(True, "STRONG_REANCHOR_ACCEPT", reanchor)
            temporal_floor = float(self.config.temporal_floor_peak_ratio)
            temporally_consistent = (
                self.previous_valid_rpm is not None
                and peak_ratio >= temporal_floor
                and abs(rate_rpm - self.previous_valid_rpm)
                <= float(self.config.temporal_max_delta_rpm)
            )
            if temporally_consistent:
                self.previous_valid_rpm = rate_rpm
                self.valid_latched = True
                return QualityDecision(True, "TEMPORAL_ACCEPT", temporal_floor)
            return QualityDecision(False, "MMWAVE_TEMPORAL_REANCHOR_WEAK", reanchor)

        if self.config.name == "candidate_b_temporal":
            threshold = (
                self.config.enter_peak_ratio
                if self.previous_valid_rpm is None
                else self.config.temporal_floor_peak_ratio
            )
            rate_consistent = (
                self.previous_valid_rpm is None
                or abs(rate_rpm - self.previous_valid_rpm)
                <= float(self.config.temporal_max_delta_rpm)
            )
            if threshold is not None and peak_ratio >= threshold and rate_consistent:
                self.previous_valid_rpm = rate_rpm
                self.valid_latched = True
                return QualityDecision(True, "TEMPORAL_ACCEPT", threshold)
            return QualityDecision(False, "MMWAVE_TEMPORAL_QUALITY_WEAK", threshold)

        threshold = self.config.enter_peak_ratio
        if (
            self.config.remain_peak_ratio is not None
            and self.valid_latched
        ):
            threshold = self.config.remain_peak_ratio
        dominance_ok = (
            self.config.minimum_peak_dominance is None
            or (
                peak_dominance is not None
                and peak_dominance >= self.config.minimum_peak_dominance
            )
        )
        if threshold is not None and peak_ratio >= threshold and dominance_ok:
            self.previous_valid_rpm = rate_rpm
            self.valid_latched = True
            return QualityDecision(True, "SPECTRUM_ACCEPT", threshold)

        return QualityDecision(False, "MMWAVE_SPECTRAL_QUALITY_WEAK", threshold)


def spectral_peak_dominance(adapter: MR60ESPAdapter) -> float | None:
    """현행 estimator와 같은 spectrum에서 1·2위 local peak의 비를 계산한다."""
    timestamps = np.asarray(adapter.estimator.timestamps, dtype=np.float64)
    values = np.asarray(adapter.estimator.values, dtype=np.float64)
    if len(values) < adapter.estimator.window_samples:
        return None
    target = timestamps[0] + np.arange(adapter.estimator.window_samples) / adapter.estimator.sample_rate_hz
    uniform = np.interp(target, timestamps, values)
    relative_t = target - target[0]
    trend = np.polyval(np.polyfit(relative_t, uniform, 1), relative_t)
    detrended = uniform - trend
    nfft = max(4096, 1 << (len(detrended) - 1).bit_length())
    spectrum = np.abs(np.fft.rfft(detrended * np.hanning(len(detrended)), n=nfft))
    frequencies = np.fft.rfftfreq(nfft, d=1.0 / adapter.estimator.sample_rate_hz)
    band_indices = np.flatnonzero(
        (frequencies >= adapter.estimator.band_min_hz)
        & (frequencies <= adapter.estimator.band_max_hz)
    )
    local_peaks = [
        int(index)
        for index in band_indices
        if 0 < index < len(spectrum) - 1
        and spectrum[index] >= spectrum[index - 1]
        and spectrum[index] > spectrum[index + 1]
    ]
    if len(local_peaks) < 2:
        return None
    strongest = sorted((float(spectrum[index]) for index in local_peaks), reverse=True)[:2]
    return strongest[0] / max(strongest[1], 1e-12)


def respiration_metrics(reference_rpm: float | None, estimates: list[float]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "ground_truth_rpm": reference_rpm,
        "window_estimates_rpm": estimates,
        "estimated_rpm_mean": statistics.fmean(estimates) if estimates else None,
        "absolute_errors_rpm": [],
        "mae_rpm": None,
        "max_absolute_error_rpm": None,
        "within_2rpm_count": None,
        "within_2rpm_rate": None,
    }
    if reference_rpm is not None and estimates:
        errors = [abs(value - reference_rpm) for value in estimates]
        result.update({
            "absolute_errors_rpm": errors,
            "mae_rpm": statistics.fmean(errors),
            "max_absolute_error_rpm": max(errors),
            "within_2rpm_count": sum(error <= 2.0 for error in errors),
            "within_2rpm_rate": sum(error <= 2.0 for error in errors) / len(errors),
        })
    return result


def diagnostic_dataset(
    spec: DatasetSpec,
    interpreter: Any,
    policy_config: PolicyConfig,
    *,
    git_commit: str | None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    records, total_lines, invalid_json = load_jsonl(spec.path)
    sensors = sensor_records(records)
    if not sensors:
        raise ValueError(f"{spec.id}: 센서 레코드가 없습니다")
    adapter = MR60ESPAdapter(strict_provenance=spec.strict_provenance)
    policy = QualityPolicy(policy_config)
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
    active = analysis_started = False
    current_valid_run = longest_valid_run = 0
    reset_reasons: Counter[str] = Counter()
    adapter_reasons: Counter[str] = Counter()
    decision_reasons: Counter[str] = Counter()
    predictions: Counter[str] = Counter()
    respiration_estimates: list[float] = []
    model_latencies: list[float] = []
    recovery_delays: list[float] = []
    rejected_quality_samples = rejected_quality_episodes = recovered_quality_episodes = 0
    first_quality_reject_s: float | None = None
    windows: list[dict[str, Any]] = []

    for item in sensors:
        timestamp_ms = item.get("ts_monotonic_ms")
        if not finite_number(timestamp_ms):
            continue
        timestamp_ms = float(timestamp_ms)
        if timestamp_ms < start_ms:
            prehistory_packet = adapter.process(item)
            prehistory_mmwave = prehistory_packet["mmwave_mr60"]
            if prehistory_mmwave["valid"]:
                policy.decide(
                    float(prehistory_mmwave["breath_rpm"]),
                    float(prehistory_mmwave["breath_spectral_peak_ratio"]),
                    spectral_peak_dominance(adapter),
                )
            elif prehistory_mmwave.get("fault_reason") not in EXPECTED_HISTORY_ERRORS:
                policy.physical_reset()
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

        if not active and after_count > 0:
            active = True
            attempted += 1

        if mmwave["valid"]:
            rate_rpm = float(mmwave["breath_rpm"])
            peak_ratio = float(mmwave["breath_spectral_peak_ratio"])
            peak_dominance = spectral_peak_dominance(adapter)
            decision = policy.decide(rate_rpm, peak_ratio, peak_dominance)
            decision_reasons[decision.reason] += 1
            if not decision.accept:
                rejected_quality_samples += 1
                current_valid_run = 0
                if first_quality_reject_s is None:
                    first_quality_reject_s = float(packet["timestamp_s"])
                    rejected_quality_episodes += 1
                continue

            recovery_delay_s = 0.0
            if first_quality_reject_s is not None:
                recovery_delay_s = float(packet["timestamp_s"]) - first_quality_reject_s
                recovery_delays.append(recovery_delay_s)
                recovered_quality_episodes += 1
                first_quality_reject_s = None
            window = np.asarray(adapter.estimator.values, dtype=np.float32)
            prediction = interpreter.predict(window)
            fallback_count += int(prediction.fallback_used)
            if not prediction.fallback_used:
                predictions[prediction.class_name] += 1
                model_latencies.append(float(prediction.latency_ms))
            completed += 1
            current_valid_run += 1
            longest_valid_run = max(longest_valid_run, current_valid_run)
            respiration_estimates.append(rate_rpm)
            windows.append({
                "kind": "quality_policy_window",
                "policy": policy_config.name,
                "dataset_id": spec.id,
                "window_index": completed,
                "window_end_timestamp_s": float(packet["timestamp_s"]),
                "window_samples": len(window),
                "estimated_respiration_rpm": rate_rpm,
                "spectral_peak_ratio": peak_ratio,
                "spectral_peak_dominance": peak_dominance,
                "quality_decision": decision.reason,
                "quality_threshold": decision.threshold,
                "recovery_delay_s": recovery_delay_s,
                "reference_respiration_rpm": spec.reference_respiration_rpm,
                "class_name": prediction.class_name,
                "model_id": prediction.model_id,
                "model_version": prediction.model_version,
                "model_inference_latency_ms": prediction.latency_ms,
                "fallback_used": prediction.fallback_used,
                "fallback_reason": prediction.fallback_reason,
            })
            adapter.estimator.reset("MMWAVE_REPLAY_WINDOW_COMPLETE")
            active = False
        else:
            if reason not in EXPECTED_HISTORY_ERRORS:
                current_valid_run = 0
                policy.physical_reset()
            reset_during_window = active and before_count > 0 and after_count == 0
            invalid_full_window = (
                active
                and after_count >= adapter.estimator.window_samples
                and reason not in EXPECTED_HISTORY_ERRORS
            )
            if reset_during_window or invalid_full_window:
                rejected += 1
                reset_reasons[reason or "MMWAVE_WINDOW_INVALID"] += 1
                active = False
                first_quality_reject_s = None
                policy.physical_reset()
                if invalid_full_window:
                    adapter.estimator.reset(reason or "MMWAVE_WINDOW_INVALID")

    if active and len(adapter.estimator.values):
        rejected += 1
        reset_reasons["MMWAVE_INSUFFICIENT_HISTORY"] += 1

    presence_total = (
        analysis_quality["presence_true"]
        + analysis_quality["presence_false"]
        + analysis_quality["presence_unknown"]
    )
    presence = {"ground_truth": spec.presence_ground_truth, "detection_rate": None, "false_presence_rate": None}
    if spec.presence_ground_truth == "PRESENT" and presence_total:
        presence["detection_rate"] = analysis_quality["presence_true"] / presence_total
    elif spec.presence_ground_truth == "ABSENT" and presence_total:
        presence["false_presence_rate"] = analysis_quality["presence_true"] / presence_total

    class_accuracy = None
    if spec.ai_class_ground_truth and completed and fallback_count == 0:
        class_accuracy = predictions[spec.ai_class_ground_truth] / completed
    summary: dict[str, Any] = {
        "policy": asdict(policy_config),
        "dataset_id": spec.id,
        "scenario": spec.scenario,
        "classification": spec.classification,
        "source_file": provenance_path(spec.path),
        "source_sha256": sha256_file(spec.path),
        "source_total_lines": total_lines,
        "valid_json_lines": len(records),
        "invalid_json_lines": invalid_json,
        "strict_provenance": spec.strict_provenance,
        "raw_quality": raw_quality,
        "analysis_quality": analysis_quality,
        "presence": presence,
        "entry_exit": entry_exit_metrics(records) if spec.presence_ground_truth == "ENTRY_EXIT" else None,
        "attempted_windows": attempted,
        "completed_windows": completed,
        "rejected_windows": rejected,
        "window_success_rate": completed / (completed + rejected) if completed + rejected else None,
        "quality_rejected_samples": rejected_quality_samples,
        "quality_rejected_episodes": rejected_quality_episodes,
        "quality_recovered_episodes": recovered_quality_episodes,
        "quality_decision_reasons": dict(decision_reasons),
        "quality_recovery_delay_s": numeric_stats(recovery_delays),
        "reset_reasons": dict(reset_reasons),
        "adapter_event_reasons": dict(adapter_reasons),
        "longest_continuous_valid_inference_windows": longest_valid_run,
        "longest_continuous_valid_inference_s": longest_valid_run * 30.0,
        "tflite_runs": completed - fallback_count,
        "fallback_count": fallback_count,
        "prediction_distribution": dict(predictions),
        "model_latency_ms": numeric_stats(model_latencies),
        "respiration_rate": respiration_metrics(spec.reference_respiration_rpm, respiration_estimates),
        "ai_class_ground_truth": spec.ai_class_ground_truth,
        "classification_accuracy": class_accuracy,
        "model_id": getattr(interpreter, "model_meta", {}).get("model_id"),
        "model_version": getattr(interpreter, "model_meta", {}).get("version"),
        "model_sha256": getattr(interpreter, "sha256_hash", None),
        "model_sha256_matches": getattr(interpreter, "sha256_matches", None),
        "benchmark_tool_version": TOOL_VERSION,
        "benchmark_tool_git_commit": git_commit,
    }
    summary["result"] = dataset_status(spec, summary)
    return summary, windows


def baseline_parity(
    diagnostic: list[dict[str, Any]], baseline_path: Path
) -> dict[str, Any]:
    expected_payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    expected = {item["dataset_id"]: item for item in expected_payload["datasets"]}
    checks = []
    for actual in diagnostic:
        prior = expected[actual["dataset_id"]]
        actual_rates = actual["respiration_rate"]["window_estimates_rpm"]
        expected_rates = prior["respiration_rate"]["window_estimates_rpm"]
        checks.append({
            "dataset_id": actual["dataset_id"],
            "source_sha256_match": actual["source_sha256"] == prior["source_sha256"],
            "attempted_match": actual["attempted_windows"] == prior["attempted_windows"],
            "completed_match": actual["completed_windows"] == prior["completed_windows"],
            "rejected_match": actual["rejected_windows"] == prior["rejected_windows"],
            "rates_match": len(actual_rates) == len(expected_rates) and bool(
                np.allclose(actual_rates, expected_rates, rtol=0.0, atol=1e-9)
            ),
            "fallback_match": actual["fallback_count"] == prior["fallback_count"],
        })
    return {"checks": checks, "all_passed": all(all(value for key, value in item.items() if key != "dataset_id") for item in checks)}


def candidate_verdict(
    candidate: list[dict[str, Any]], baseline: list[dict[str, Any]]
) -> dict[str, Any]:
    actual = {item["dataset_id"]: item for item in candidate}
    prior = {item["dataset_id"]: item for item in baseline}
    coverage_ids = [
        "occupied_31min_v120", "distance_0_6m", "distance_0_9m",
        "distance_1_2m", "distance_1_5m", "accepted_occupied_6min_v2",
    ]
    checks = {
        "20rpm_all_valid_within_2rpm": (
            actual["paced_20rpm"]["completed_windows"] > 0
            and actual["paced_20rpm"]["respiration_rate"]["within_2rpm_rate"] == 1.0
        ),
        "paced_12_coverage_preserved": actual["paced_12rpm"]["completed_windows"] >= prior["paced_12rpm"]["completed_windows"],
        "paced_15_coverage_preserved": actual["paced_15rpm"]["completed_windows"] >= prior["paced_15rpm"]["completed_windows"],
        "paced_12_all_within_2rpm": actual["paced_12rpm"]["respiration_rate"]["within_2rpm_rate"] == 1.0,
        "paced_15_all_within_2rpm": actual["paced_15rpm"]["respiration_rate"]["within_2rpm_rate"] == 1.0,
        "coverage_preserved": all(actual[key]["completed_windows"] >= prior[key]["completed_windows"] for key in coverage_ids),
        "occupied_longest_continuous_preserved": (
            actual["occupied_31min_v120"]["longest_continuous_valid_inference_s"]
            >= prior["occupied_31min_v120"]["longest_continuous_valid_inference_s"]
        ),
        "entry_exit_window_preserved": (
            actual["entry_exit_20"]["completed_windows"]
            >= prior["entry_exit_20"]["completed_windows"]
        ),
        "entry_exit_events_preserved": (
            actual["entry_exit_20"]["entry_exit"] == prior["entry_exit_20"]["entry_exit"]
        ),
        "empty_fail_closed": all(actual[key]["completed_windows"] == 0 for key in ("empty_30min_v120", "accepted_empty_6min_v2")),
        "fallback_zero": all(item["fallback_count"] == 0 for item in candidate),
        "model_hash_valid": all(item["model_sha256_matches"] is True for item in candidate),
    }
    return {"checks": checks, "accepted": all(checks.values())}


def render_report(payload: dict[str, Any]) -> str:
    baseline = {item["dataset_id"]: item for item in payload["policies"]["baseline"]}
    lines = [
        "# mmWave rolling 품질 정책 Historical Replay Diagnostic",
        "",
        "- Production 변경: 없음",
        f"- 모델 SHA-256: `{payload['provenance']['model_sha256']}`",
        f"- Baseline parity: **{'PASS' if payload['baseline_parity']['all_passed'] else 'FAIL'}**",
        "",
        "## 후보 판정",
        "",
        "| 후보 | 최종 판정 | 20 rpm windows | 20 rpm MAE | occupied | 0.9 m | quality recovery p95 | fallback |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for name, datasets in payload["policies"].items():
        if name == "baseline":
            verdict = "기준"
        else:
            verdict = "채택 가능" if payload["verdicts"][name]["accepted"] else "거부"
        by_id = {item["dataset_id"]: item for item in datasets}
        recovery_p95_values = [
            item["quality_recovery_delay_s"]["p95"]
            for item in datasets
            if item["quality_recovery_delay_s"]["p95"] is not None
        ]
        recovery_p95 = max(recovery_p95_values) if recovery_p95_values else 0.0
        lines.append(
            f"| {name} | {verdict} | {by_id['paced_20rpm']['completed_windows']}/{by_id['paced_20rpm']['attempted_windows']} "
            f"| {by_id['paced_20rpm']['respiration_rate']['mae_rpm']} "
            f"| {by_id['occupied_31min_v120']['completed_windows']}/{baseline['occupied_31min_v120']['completed_windows']} "
            f"| {by_id['distance_0_9m']['completed_windows']}/{baseline['distance_0_9m']['completed_windows']} "
            f"| {recovery_p95:.3f}s | {sum(item['fallback_count'] for item in datasets)} |"
        )
    lines.extend(["", "## 자동 판정 상세", ""])
    for name, verdict in payload["verdicts"].items():
        lines.append(f"### {name}: {'PASS' if verdict['accepted'] else 'FAIL'}")
        lines.append("")
        for check, passed in verdict["checks"].items():
            lines.append(f"- [{'x' if passed else ' '}] `{check}`")
        lines.append("")
    lines.extend([
        "## 해석 제한",
        "",
        "Temporal consistency와 hysteresis는 historical suite에서 실제 호흡수 전환 ground truth가 없으므로 전환 지연 안전성을 완전히 입증하지 못한다. 이 결과는 production 변경 승인이 아니라 후보 선별 근거다.",
        "",
    ])
    return "\n".join(lines)


def write_outputs(output_dir: Path, payload: dict[str, Any], windows: dict[str, dict[str, list[dict[str, Any]]]]) -> None:
    output_dir.mkdir(parents=True, exist_ok=False)
    (output_dir / "diagnostic_summary.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    (output_dir / "FINAL_REPORT_KO.md").write_text(render_report(payload), encoding="utf-8")
    windows_root = output_dir / "windows"
    windows_root.mkdir()
    for policy_name, datasets in windows.items():
        policy_dir = windows_root / policy_name
        policy_dir.mkdir()
        for dataset_id, items in datasets.items():
            with (policy_dir / f"{dataset_id}.jsonl").open("x", encoding="utf-8") as stream:
                for item in items:
                    stream.write(json.dumps(item, ensure_ascii=False, allow_nan=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--baseline-summary", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--policies", nargs="+", choices=tuple(POLICIES), default=list(POLICIES))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_args = argparse.Namespace(input=None, input_dir=None, manifest=args.manifest)
    specs = load_specs(load_args)
    interpreter = MMWaveInterpreter(project_root=ONDEVICE_AI_ROOT)
    git_commit = git_value("rev-parse", "HEAD")
    policy_results: dict[str, list[dict[str, Any]]] = {}
    policy_windows: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for policy_index, policy_name in enumerate(args.policies, 1):
        print(f"[{policy_index}/{len(args.policies)}] {policy_name}")
        policy_results[policy_name] = []
        policy_windows[policy_name] = {}
        for dataset_index, spec in enumerate(specs, 1):
            started = time.perf_counter()
            summary, windows = diagnostic_dataset(
                spec, interpreter, POLICIES[policy_name], git_commit=git_commit
            )
            summary["diagnostic_elapsed_s"] = time.perf_counter() - started
            policy_results[policy_name].append(summary)
            policy_windows[policy_name][spec.id] = windows
            print(
                f"  [{dataset_index}/{len(specs)}] {spec.id}: "
                f"{summary['completed_windows']}/{summary['attempted_windows']} "
                f"quality_reject={summary['quality_rejected_samples']}"
            )

    if "baseline" not in policy_results:
        raise ValueError("baseline policy는 parity 검증을 위해 필수입니다")
    parity = baseline_parity(policy_results["baseline"], args.baseline_summary)
    verdicts = {
        name: candidate_verdict(datasets, policy_results["baseline"])
        for name, datasets in policy_results.items()
        if name != "baseline"
    }
    payload = {
        "diagnostic_id": args.output_dir.name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "git_commit": git_commit,
            "tool_version": TOOL_VERSION,
            "model_id": interpreter.model_meta["model_id"],
            "model_version": interpreter.model_meta["version"],
            "model_sha256": interpreter.sha256_hash,
            "model_sha256_matches": interpreter.sha256_matches,
            "fallback_load_reason": interpreter.load_error_reason,
            "baseline_summary": provenance_path(args.baseline_summary),
        },
        "baseline_parity": parity,
        "verdicts": verdicts,
        "policies": policy_results,
    }
    write_outputs(args.output_dir, payload, policy_windows)
    print(f"Baseline parity: {'PASS' if parity['all_passed'] else 'FAIL'}")
    for name, verdict in verdicts.items():
        print(f"{name}: {'PASS' if verdict['accepted'] else 'FAIL'}")
    return 0 if parity["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
