#!/usr/bin/env python3
"""SCD40 실측 CSV의 재현 가능한 통계와 시나리오 판정을 JSON으로 생성한다."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="SCD40 원시 CSV를 분석해 *_summary.json을 만듭니다.")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--logs-dir", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    if bool(args.input) == bool(args.logs_dir):
        parser.error("--input 또는 --logs-dir 중 하나만 지정해야 합니다.")
    if args.input and not args.output:
        parser.error("--input 사용 시 --output이 필요합니다.")
    if args.logs_dir and not args.output_dir:
        parser.error("--logs-dir 사용 시 --output-dir이 필요합니다.")
    return args


def read_bool(value: str | None) -> bool:
    return str(value).strip().lower() == "true"


def read_float(value: str | None) -> float | None:
    try:
        number = float(value) if value not in (None, "") else None
    except ValueError:
        return None
    return number if number is not None and math.isfinite(number) else None


def scenario_from(rows: list[dict[str, str]], path: Path) -> str:
    scenarios = {row.get("scenario", "").strip() for row in rows if row.get("scenario", "").strip()}
    if len(scenarios) == 1:
        return next(iter(scenarios))
    name = path.stem.lower()
    for scenario in ("preflight", "baseline", "breath-rise-recovery", "disconnect"):
        if scenario in name:
            return scenario
    return "unknown"


def judge(scenario: str, valid_values: list[float], rows: list[dict[str, str]]) -> tuple[str, list[str]]:
    reasons: list[str] = []
    invalid_count = sum(not read_bool(row.get("valid")) for row in rows)
    missing_rate = invalid_count / len(rows) if rows else 1.0
    if scenario == "disconnect":
        zero_as_valid = any(read_bool(r.get("valid")) and read_float(r.get("co2_ppm")) == 0 for r in rows)
        passed = invalid_count > 0 and not zero_as_valid
        reasons.append(f"invalid_samples={invalid_count}")
        reasons.append(f"zero_ppm_valid_samples={int(zero_as_valid)}")
        return ("PASS" if passed else "FAIL"), reasons
    if not valid_values:
        return "FAIL", ["유효한 CO2 표본이 없음"]
    if scenario == "breath-rise-recovery":
        baseline_window = valid_values[: max(1, min(30, len(valid_values) // 4))]
        baseline = statistics.mean(baseline_window)
        peak = max(valid_values)
        peak_index = valid_values.index(peak)
        post_peak = valid_values[peak_index + 1 :]
        recovery_observed = bool(post_peak) and min(post_peak) < peak
        rise = peak - baseline
        passed = rise > 0 and recovery_observed
        reasons.extend(
            [
                f"baseline_mean_ppm={baseline:.3f}",
                f"peak_ppm={peak:.3f}",
                f"rise_ppm={rise:.3f}",
                f"recovery_observed={str(recovery_observed).lower()}",
                f"missing_rate={missing_rate:.6f}",
            ]
        )
        if not passed:
            return "FAIL", reasons
        return ("PASS" if missing_rate == 0.0 else "PASS_WITH_WARNINGS"), reasons
    reasons = [
        "유효 표본과 계산 가능한 통계가 존재함",
        f"missing_rate={missing_rate:.6f}",
    ]
    return ("PASS" if missing_rate == 0.0 else "FAIL"), reasons


def analyze(path: Path) -> dict:
    raw_bytes = path.read_bytes()
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    valid_values = [
        value
        for row in rows
        if read_bool(row.get("valid"))
        for value in [read_float(row.get("co2_ppm"))]
        if value is not None
    ]
    timestamps = [read_float(row.get("host_unix_s")) for row in rows]
    timestamps = [value for value in timestamps if value is not None]
    intervals = [b - a for a, b in zip(timestamps, timestamps[1:]) if b >= a]
    scenario = scenario_from(rows, path)
    verdict, reasons = judge(scenario, valid_values, rows)
    sample_count = len(rows)
    missing_count = sum(not read_bool(row.get("valid")) for row in rows)
    return {
        "schema": "safenest.scd40.evidence-summary.v1",
        "source": f"logs/{path.name}",
        "source_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "scenario": scenario,
        "sample_count": sample_count,
        "valid_sample_count": len(valid_values),
        "missing_sample_count": missing_count,
        "missing_rate": missing_count / sample_count if sample_count else None,
        "elapsed_seconds": timestamps[-1] - timestamps[0] if len(timestamps) >= 2 else 0.0,
        "sample_interval_seconds": {
            "minimum": min(intervals) if intervals else None,
            "maximum": max(intervals) if intervals else None,
            "mean": statistics.mean(intervals) if intervals else None,
        },
        "co2_ppm": {
            "minimum": min(valid_values) if valid_values else None,
            "maximum": max(valid_values) if valid_values else None,
            "mean": statistics.mean(valid_values) if valid_values else None,
        },
        "sensor_states": dict(Counter((row.get("sensor_state") or "MISSING") for row in rows)),
        "errors": dict(Counter((row.get("error") or "NONE") for row in rows)),
        "verdict": verdict,
        "verdict_reasons": reasons,
    }


def write_summary(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(analyze(input_path), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(f"summary={output_path}")


def main() -> None:
    args = parse_args()
    if args.input:
        write_summary(args.input, args.output)
        return
    inputs = sorted(args.logs_dir.glob("*.csv"))
    if not inputs:
        raise SystemExit(f"분석할 CSV가 없습니다: {args.logs_dir}")
    for input_path in inputs:
        write_summary(input_path, args.output_dir / f"{input_path.stem}_summary.json")


if __name__ == "__main__":
    main()
