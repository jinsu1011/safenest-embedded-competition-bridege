#!/usr/bin/env python3
"""Analyze a paced-breathing JSONL capture without modifying the raw log."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and np.isfinite(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.input.open(encoding="utf-8")]
    all_cues = [row for row in rows if row.get("kind") == "cue"]
    measurement_cues = [
        row for row in all_cues if row.get("stage") == "measurement"
    ]
    # Backward compatibility for captures created before stage markers existed.
    cues = measurement_cues or all_cues
    sensors = [row for row in rows if row.get("kind") == "sensor"]
    inhales = [row for row in cues if row.get("event") == "inhale"]
    exhales = [row for row in cues if row.get("event") == "exhale"]
    if not inhales:
        raise SystemExit("no inhale cue in capture")

    target_bpm = float(inhales[0]["target_bpm"])
    period_s = 60.0 / target_bpm
    start_ns = int(inhales[0]["host_monotonic_ns"])
    # A capture may end after an inhale half-cycle (for example, 30 s at
    # 15 bpm is 7.5 cycles), so derive the boundary from the final phase cue.
    tail_s = period_s / 2.0 if exhales else period_s
    end_ns = int(cues[-1]["host_monotonic_ns"]) + int(tail_s * 1e9)
    measured = [
        row for row in sensors
        if start_ns <= int(row["host_monotonic_ns"]) < end_ns
    ]
    if len(measured) < 3:
        raise SystemExit("not enough sensor samples inside cue window")

    times = np.array([row["host_monotonic_ns"] for row in measured], dtype=float) / 1e9
    times -= times[0]
    phases = np.array([row.get("breath_phase", np.nan) for row in measured], dtype=float)
    good_phase = np.isfinite(phases)
    phase_times = times[good_phase]
    phases = phases[good_phase]

    dominant_rpm = None
    if len(phases) >= 20:
        sample_step = float(np.median(np.diff(phase_times)))
        uniform_times = np.arange(phase_times[0], phase_times[-1], sample_step)
        uniform_phase = np.interp(uniform_times, phase_times, phases)
        trend = np.polyval(np.polyfit(uniform_times, uniform_phase, 1), uniform_times)
        spectrum = np.abs(np.fft.rfft((uniform_phase - trend) * np.hanning(len(uniform_phase))))
        frequencies = np.fft.rfftfreq(len(uniform_phase), sample_step)
        band = (frequencies >= 5.0 / 60.0) & (frequencies <= 40.0 / 60.0)
        dominant_rpm = float(frequencies[band][np.argmax(spectrum[band])] * 60.0)

    rates = np.array([
        row.get("breath_rate_raw", np.nan) for row in measured
    ], dtype=float)
    positive_rates = rates[np.isfinite(rates) & (rates > 0)]
    distances = np.array([
        row.get("distance_cm_raw", np.nan) for row in measured
    ], dtype=float)
    distances = distances[np.isfinite(distances) & (distances > 0)]
    inhale_times = np.array([row["host_monotonic_ns"] for row in inhales], dtype=float) / 1e9
    all_cue_times = np.array([row["host_monotonic_ns"] for row in cues], dtype=float) / 1e9

    result = {
        "input": str(args.input),
        "target_bpm": target_bpm,
        "measurement_samples": len(measured),
        "measurement_duration_s": float(times[-1] - times[0]),
        "presence_true_ratio": float(np.mean([
            bool(row.get("human_detected_raw")) for row in measured
        ])),
        "distance_median_cm": float(np.median(distances)) if len(distances) else None,
        "breath_rate_positive_ratio": float(len(positive_rates) / len(measured)),
        "breath_rate_positive_mean_rpm": float(np.mean(positive_rates)) if len(positive_rates) else None,
        "breath_rate_positive_median_rpm": float(np.median(positive_rates)) if len(positive_rates) else None,
        "breath_rate_positive_std_rpm": float(np.std(positive_rates)) if len(positive_rates) else None,
        "breath_rate_within_2rpm_all_ratio": float(np.mean(
            np.isfinite(rates) & (rates > 0) & (np.abs(rates - target_bpm) <= 2.0)
        )),
        "breath_rate_mae_positive_rpm": float(np.mean(np.abs(positive_rates - target_bpm))) if len(positive_rates) else None,
        "breath_phase_std": float(np.std(phases)) if len(phases) else None,
        "breath_phase_dominant_rpm": dominant_rpm,
        "inhale_cue_count": len(inhales),
        "exhale_cue_count": len(exhales),
        "inhale_interval_mean_s": float(np.mean(np.diff(inhale_times))) if len(inhale_times) > 1 else None,
        "inhale_interval_std_s": float(np.std(np.diff(inhale_times))) if len(inhale_times) > 1 else None,
        "all_cue_interval_mean_s": float(np.mean(np.diff(all_cue_times))) if len(all_cue_times) > 1 else None,
        "checksum_error_delta": int(measured[-1]["checksum_errors"] - measured[0]["checksum_errors"]),
        "parse_error_delta": int(measured[-1]["parse_errors"] - measured[0]["parse_errors"]),
        "uart_frame_delta": int(measured[-1]["uart_frames_total"] - measured[0]["uart_frames_total"]),
    }

    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
