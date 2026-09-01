#!/usr/bin/env python3
"""Replay causal breath-rate filters against the same paced raw logs.

Invalid input (absence, zero, NaN, out-of-distance, or missing data) produces
no output and resets filter state. This deliberately never fills a missing
sensor value with a previous normal value.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Trial:
    target_rpm: float
    rows: list[dict]
    source: str


class Filter:
    def __init__(self, transform: Callable[[list[float]], float | None]) -> None:
        self.values: deque[float] = deque(maxlen=5)
        self.transform = transform
        self.ema: float | None = None

    def reset(self) -> None:
        self.values.clear()
        self.ema = None

    def raw(self, value: float) -> float:
        return value

    def windowed(self, value: float) -> float | None:
        self.values.append(value)
        return self.transform(list(self.values))

    def ema_only(self, value: float, alpha: float = 0.3) -> float:
        self.ema = value if self.ema is None else alpha * value + (1.0 - alpha) * self.ema
        return self.ema

    def median_ema(self, value: float, alpha: float = 0.3) -> float | None:
        median = self.windowed(value)
        if median is None:
            return None
        self.ema = median if self.ema is None else alpha * median + (1.0 - alpha) * self.ema
        return self.ema


def mean5(values: list[float]) -> float | None:
    return statistics.fmean(values) if len(values) >= 3 else None


def median5(values: list[float]) -> float | None:
    return statistics.median(values) if len(values) >= 3 else None


def load_trial(path: Path) -> Trial:
    records = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
    cues = [
        row for row in records
        if row.get("kind") == "cue" and row.get("stage") == "measurement"
    ]
    if not cues:
        raise ValueError(f"measurement cues missing: {path}")
    target = float(cues[0]["target_bpm"])
    half_period_ns = int((30.0 / target) * 1e9)
    start_ns = int(cues[0]["host_monotonic_ns"])
    end_ns = int(cues[-1]["host_monotonic_ns"]) + half_period_ns
    rows = [
        row for row in records
        if row.get("kind") == "sensor"
        and start_ns <= int(row["host_monotonic_ns"]) < end_ns
    ]
    return Trial(target_rpm=target, rows=rows, source=str(path))


def valid_raw(row: dict, distance_min_cm: float, distance_max_cm: float) -> float | None:
    value = row.get("breath_rate_raw")
    distance = row.get("distance_cm_raw")
    if row.get("human_detected_raw") is not True:
        return None
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    if not isinstance(distance, (int, float)) or not math.isfinite(distance):
        return None
    if not distance_min_cm <= float(distance) <= distance_max_cm:
        return None
    return float(value)


def evaluate(trials: list[Trial], name: str, mode: str, delay_s: float,
             distance_min_cm: float, distance_max_cm: float) -> dict:
    per_trial: list[dict] = []
    all_errors: list[float] = []
    all_outputs: list[float] = []
    total_samples = total_valid = raw_outliers = recovered_outliers = introduced_outliers = 0

    for trial in trials:
        filt = Filter(median5 if mode == "median_ema" else (
            mean5 if mode == "mean" else median5
        ))
        outputs: list[float] = []
        errors: list[float] = []
        trial_raw_outliers = trial_recovered = trial_introduced = 0
        for row in trial.rows:
            total_samples += 1
            value = valid_raw(row, distance_min_cm, distance_max_cm)
            if value is None:
                filt.reset()
                continue
            raw_is_outlier = abs(value - trial.target_rpm) > 2.0
            if raw_is_outlier:
                raw_outliers += 1
                trial_raw_outliers += 1
            if mode == "raw":
                output = filt.raw(value)
            elif mode in {"mean", "median"}:
                output = filt.windowed(value)
            elif mode == "ema":
                output = filt.ema_only(value)
            elif mode == "median_ema":
                output = filt.median_ema(value)
            else:
                raise ValueError(mode)
            if output is None:
                continue
            total_valid += 1
            outputs.append(output)
            error = abs(output - trial.target_rpm)
            errors.append(error)
            if raw_is_outlier and error <= 2.0:
                recovered_outliers += 1
                trial_recovered += 1
            if not raw_is_outlier and error > 2.0:
                introduced_outliers += 1
                trial_introduced += 1

        all_outputs.extend(outputs)
        all_errors.extend(errors)
        per_trial.append({
            "target_rpm": trial.target_rpm,
            "samples": len(trial.rows),
            "valid_ratio": len(outputs) / len(trial.rows),
            "mean_rpm": statistics.fmean(outputs) if outputs else None,
            "median_rpm": statistics.median(outputs) if outputs else None,
            "std_rpm": statistics.pstdev(outputs) if len(outputs) > 1 else 0.0,
            "mae_rpm": statistics.fmean(errors) if errors else None,
            "within_2rpm_ratio_all": sum(error <= 2.0 for error in errors) / len(trial.rows),
            "raw_outliers": trial_raw_outliers,
            "recovered_outliers": trial_recovered,
            "introduced_outliers": trial_introduced,
        })

    return {
        "filter": name,
        "estimated_additional_delay_s": delay_s,
        "valid_ratio": total_valid / total_samples,
        "pooled_output_std_rpm": statistics.pstdev(all_outputs) if len(all_outputs) > 1 else 0.0,
        "pooled_mae_rpm": statistics.fmean(all_errors) if all_errors else None,
        "raw_outlier_recovery_ratio": recovered_outliers / raw_outliers if raw_outliers else 0.0,
        "introduced_outliers": introduced_outliers,
        "per_trial": per_trial,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("inputs", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--distance-min-cm", type=float, default=40.0)
    parser.add_argument("--distance-max-cm", type=float, default=150.0)
    args = parser.parse_args()
    trials = [load_trial(path) for path in args.inputs]
    candidates = [
        ("raw", "raw", 0.0),
        ("moving_average_5_min3", "mean", 0.2),
        ("median_5_min3", "median", 0.2),
        ("ema_alpha_0_3", "ema", 0.233),
        ("median_5_min3_plus_ema_0_3", "median_ema", 0.433),
    ]
    result = {
        "sources": [trial.source for trial in trials],
        "validity": {
            "presence_required": True,
            "zero_nan_missing_are_unknown": True,
            "distance_min_cm": args.distance_min_cm,
            "distance_max_cm": args.distance_max_cm,
            "invalid_samples_reset_filter_and_are_not_filled": True,
        },
        "delay_note": "Causal-filter group-delay estimate at 10 Hz; not a measured physiological response delay.",
        "candidates": [
            evaluate(
                trials, name, mode, delay,
                args.distance_min_cm, args.distance_max_cm,
            )
            for name, mode, delay in candidates
        ],
    }
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
