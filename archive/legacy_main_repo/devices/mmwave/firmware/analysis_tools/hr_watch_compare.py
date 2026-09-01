#!/usr/bin/env python3
"""Pair Apple Watch prompts with ESP telemetry using host monotonic receipts."""

from __future__ import annotations

import argparse
import json
import math
import statistics as stats
from pathlib import Path


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    mean_x, mean_y = stats.mean(xs), stats.mean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = math.sqrt(
        sum((x - mean_x) ** 2 for x in xs)
        * sum((y - mean_y) ** 2 for y in ys)
    )
    return numerator / denominator if denominator else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sensor-log", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--window-seconds", type=float, default=5.0)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    sensors = load_jsonl(args.sensor_log)
    receipts = load_jsonl(args.receipts)
    prompts = load_jsonl(args.prompts)
    reference_doc = json.loads(args.reference.read_text(encoding="utf-8"))
    references = reference_doc["watch_bpm"]
    if len(prompts) != len(references):
        raise SystemExit("prompt/reference count mismatch")

    sensor_by_seq = {item.get("seq"): item for item in sensors}
    paired = []
    half_window_ns = int(args.window_seconds * 1_000_000_000)
    for prompt, watch in zip(prompts, references):
        prompt_ns = prompt["host_monotonic_ns"]
        window = []
        for receipt in receipts:
            if abs(receipt["host_monotonic_ns"] - prompt_ns) > half_window_ns:
                continue
            sensor = sensor_by_seq.get(receipt.get("seq"))
            if not sensor or sensor.get("heart_raw_valid") is not True:
                continue
            value = sensor.get("heart_rate_raw")
            if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
                window.append(float(value))
        mr60 = stats.median(window) if window else None
        error = mr60 - watch if mr60 is not None and watch is not None else None
        paired.append({
            "index": prompt["index"],
            "scheduled_elapsed_s": prompt["scheduled_elapsed_s"],
            "watch_bpm": watch,
            "mr60_median_bpm": mr60,
            "error_bpm": error,
            "mr60_samples": len(window),
        })

    valid_pairs = [item for item in paired if item["error_bpm"] is not None]
    errors = [item["error_bpm"] for item in valid_pairs]
    watch_values = [float(item["watch_bpm"]) for item in valid_pairs]
    mr60_values = [float(item["mr60_median_bpm"]) for item in valid_pairs]
    seqs = [item["seq"] for item in sensors if isinstance(item.get("seq"), int)]
    missing_sequences = sum(max(0, right - left - 1) for left, right in zip(seqs, seqs[1:]))
    elapsed_s = (
        (sensors[-1]["ts_monotonic_ms"] - sensors[0]["ts_monotonic_ms"]) / 1000.0
        if sensors else 0.0
    )
    stable_count = sum(item.get("human_detected_stable") is True for item in sensors)
    heart_valid_count = sum(item.get("heart_raw_valid") is True for item in sensors)
    checksum_increase = max(item.get("checksum_errors", 0) for item in sensors) - min(
        item.get("checksum_errors", 0) for item in sensors
    )
    parse_increase = max(item.get("parse_errors", 0) for item in sensors) - min(
        item.get("parse_errors", 0) for item in sensors
    )
    sequence_gap_rate = missing_sequences / max(1, len(seqs) + missing_sequences)

    metrics = {
        "paired_points": len(valid_pairs),
        "mae_bpm": stats.mean(abs(value) for value in errors) if errors else None,
        "bias_bpm": stats.mean(errors) if errors else None,
        "max_abs_error_bpm": max((abs(value) for value in errors), default=None),
        "within_5_bpm_count": sum(abs(value) <= 5.0 for value in errors),
        "within_5_bpm_rate": (
            sum(abs(value) <= 5.0 for value in errors) / len(errors) if errors else None
        ),
        "pearson_r": pearson(watch_values, mr60_values),
    }
    gates = {
        "1_session_complete": elapsed_s >= 295.0 and len(sensors) >= 2950 and len(prompts) == 10,
        "2_transport_integrity": checksum_increase == 0 and parse_increase == 0 and sequence_gap_rate <= 0.001,
        "3_stable_presence": stable_count / max(1, len(sensors)) >= 0.95,
        "4_heart_availability": heart_valid_count / max(1, len(sensors)) >= 0.90 and len(valid_pairs) >= 9,
        "5_absolute_error": (
            metrics["mae_bpm"] is not None
            and metrics["mae_bpm"] <= 5.0
            and metrics["within_5_bpm_rate"] >= 0.80
        ),
        "6_recovery_tracking": None,
    }
    result = {
        "session_id": reference_doc["session_id"],
        "interpretation": "consumer_wearable_exploratory_reference",
        "heart_verified": False,
        "window_seconds": args.window_seconds,
        "source_files": {
            "sensor_log": str(args.sensor_log),
            "receipts": str(args.receipts),
            "prompts": str(args.prompts),
            "reference": str(args.reference),
        },
        "session_quality": {
            "elapsed_s": elapsed_s,
            "sensor_records": len(sensors),
            "prompt_count": len(prompts),
            "missing_sequences": missing_sequences,
            "sequence_gap_rate": sequence_gap_rate,
            "checksum_errors_increase": checksum_increase,
            "parse_errors_increase": parse_increase,
            "stable_presence_rate": stable_count / max(1, len(sensors)),
            "heart_valid_rate": heart_valid_count / max(1, len(sensors)),
        },
        "paired_points": paired,
        "metrics": metrics,
        "gates": gates,
    }
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
