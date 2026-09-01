#!/usr/bin/env python3
"""Calculate reproducible baseline metrics from ESP MR60 JSONL telemetry."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any


def numeric_stats(values: list[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "stddev": None, "min": None, "max": None}
    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "stddev": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def positive_values(records: list[dict[str, Any]], field: str) -> list[float]:
    values: list[float] = []
    for record in records:
        value = record.get(field)
        if isinstance(value, (int, float)) and math.isfinite(value) and value > 0:
            values.append(float(value))
    return values


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-seconds", type=float, default=0.0)
    args = parser.parse_args()

    records: list[dict[str, Any]] = []
    invalid_json_lines = 0
    with args.input.open(encoding="utf-8") as source:
        for line in source:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                invalid_json_lines += 1
                continue
            if "seq" in item:
                records.append(item)
    if not records:
        raise SystemExit("no telemetry records")

    all_records = records
    original_start_ms = int(all_records[0]["ts_monotonic_ms"])
    cutoff_ms = original_start_ms + int(args.skip_seconds * 1000)
    records = [item for item in all_records if int(item["ts_monotonic_ms"]) >= cutoff_ms]
    if not records:
        raise SystemExit("no telemetry records after skip interval")

    first = records[0]
    last = records[-1]
    elapsed_ms = int(last["ts_monotonic_ms"]) - int(first["ts_monotonic_ms"])
    elapsed_s = elapsed_ms / 1000.0
    uart_delta = int(last.get("uart_frames_total", 0)) - int(first.get("uart_frames_total", 0))
    checksum_delta = int(last.get("checksum_errors", 0)) - int(first.get("checksum_errors", 0))
    parse_delta = int(last.get("parse_errors", 0)) - int(first.get("parse_errors", 0))

    presence_true = sum(item.get("human_detected_raw") is True for item in records)
    presence_false = sum(item.get("human_detected_raw") is False for item in records)
    presence_unknown = len(records) - presence_true - presence_false
    stable_true = sum(item.get("human_detected_stable") is True for item in records)
    stable_false = sum(item.get("human_detected_stable") is False for item in records)
    stable_unknown = len(records) - stable_true - stable_false
    sensor_states = Counter(str(item.get("sensor_state", "MISSING")) for item in records)
    reboots = sum(
        int(current["ts_monotonic_ms"]) < int(previous["ts_monotonic_ms"])
        or int(current["seq"]) <= int(previous["seq"])
        for previous, current in zip(records, records[1:])
    )

    result = {
        "source": str(args.input),
        "skip_seconds": args.skip_seconds,
        "records_skipped": len(all_records) - len(records),
        "records": len(records),
        "invalid_json_lines": invalid_json_lines,
        "elapsed_s": elapsed_s,
        "telemetry_rate_hz": len(records) / elapsed_s if elapsed_s > 0 else None,
        "uart_frames": uart_delta,
        "uart_frame_rate_hz": uart_delta / elapsed_s if elapsed_s > 0 else None,
        "checksum_errors": checksum_delta,
        "checksum_error_rate": checksum_delta / uart_delta if uart_delta > 0 else None,
        "parse_errors": parse_delta,
        "parse_error_rate": parse_delta / uart_delta if uart_delta > 0 else None,
        "reboots_detected": reboots,
        "presence": {
            "true_count": presence_true,
            "false_count": presence_false,
            "unknown_count": presence_unknown,
            "true_rate": presence_true / len(records),
        },
        "presence_stable": {
            "true_count": stable_true,
            "false_count": stable_false,
            "unknown_count": stable_unknown,
            "true_rate": stable_true / len(records),
        },
        "sensor_states": dict(sorted(sensor_states.items())),
        "uart_frame_not_ok_count": sum(item.get("uart_frame_ok") is not True for item in records),
        "checksum_not_ok_count": sum(item.get("checksum_ok") is not True for item in records),
        "firmware_versions": sorted({
            str(item["firmware_version"])
            for item in records if item.get("firmware_version") is not None
        }),
        "config_hashes": sorted({
            str(item["config_hash"])
            for item in records if item.get("config_hash") is not None
        }),
        "distance_cm_raw": numeric_stats(positive_values(records, "distance_cm_raw")),
        "breath_rate_raw": numeric_stats(positive_values(records, "breath_rate_raw")),
        "heart_rate_raw": numeric_stats(positive_values(records, "heart_rate_raw")),
        "breath_positive_rate": len(positive_values(records, "breath_rate_raw")) / len(records),
        "heart_positive_rate": len(positive_values(records, "heart_rate_raw")) / len(records),
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
