#!/usr/bin/env python3
"""기존 paced MR60 로그에서 20 rpm 저추정 원인을 진단한다.

Production 코드는 변경하지 않고 PhaseRateEstimator와 동일한 300-sample
전처리/FFT/peak 선택을 재현해 중간 수치와 diagnostic 후보를 저장한다.
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys
from typing import Any

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from devices.mmwave.src.mr60_esp_adapter import MR60ESPAdapter


CASES = (
    (12.0, REPO_ROOT / "devices/mmwave/firmware/logs/breath/2026-07-28_breath_paced_12rpm_explicit_v2_attempt03.jsonl"),
    (15.0, REPO_ROOT / "devices/mmwave/firmware/logs/breath/2026-07-28_breath_paced_15rpm_explicit_full_v3.jsonl"),
    (20.0, REPO_ROOT / "devices/mmwave/firmware/logs/breath/2026-07-28_breath_paced_20rpm_explicit_full_v2.jsonl"),
)
ANALYSIS_DURATION_S = 180.0
SPECTRAL_GATE_CANDIDATE = 2.0


def finite_number(value: object) -> bool:
    return (
        not isinstance(value, (bool, np.bool_))
        and isinstance(value, (int, float, np.number))
        and bool(np.isfinite(value))
    )


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_measurement(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    records: list[dict[str, Any]] = []
    invalid_json = 0
    with path.open(encoding="utf-8", errors="replace") as stream:
        for line in stream:
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                invalid_json += 1
                continue
            if isinstance(item, dict):
                records.append(item)
            else:
                invalid_json += 1
    sensors = [item for item in records if item.get("kind") == "sensor"]
    measurement_cues = [
        int(item["host_monotonic_ns"])
        for item in records
        if item.get("kind") == "cue"
        and item.get("stage") == "measurement"
        and isinstance(item.get("host_monotonic_ns"), int)
    ]
    if not sensors or not measurement_cues:
        raise ValueError(f"measurement sensor/cue가 없습니다: {path}")
    first_cue_ns = min(measurement_cues)
    matching = [
        item for item in sensors
        if isinstance(item.get("host_monotonic_ns"), int)
        and item["host_monotonic_ns"] >= first_cue_ns
        and finite_number(item.get("ts_monotonic_ms"))
    ]
    if not matching:
        raise ValueError(f"measurement cue 이후 sensor가 없습니다: {path}")
    start_ms = float(matching[0]["ts_monotonic_ms"])
    end_ms = start_ms + ANALYSIS_DURATION_S * 1000.0
    measurement = [
        item for item in sensors
        if finite_number(item.get("ts_monotonic_ms"))
        and start_ms <= float(item["ts_monotonic_ms"]) < end_ms
    ]
    return records, measurement, {
        "invalid_json": invalid_json,
        "total_records": len(records),
        "sensor_records": len(sensors),
        "start_ms": int(start_ms),
        "end_ms": int(end_ms),
    }


def quality_metrics(measurement: list[dict[str, Any]]) -> dict[str, Any]:
    timestamps = np.asarray(
        [float(item["ts_monotonic_ms"]) / 1000.0 for item in measurement], dtype=np.float64
    )
    intervals = np.diff(timestamps)
    sequences = [int(item["seq"]) for item in measurement if isinstance(item.get("seq"), int)]
    phases = np.asarray([float(item["breath_phase"]) for item in measurement], dtype=np.float64)
    present = np.asarray([
        item.get("human_detected_stable", item.get("human_detected_raw")) is True
        for item in measurement
    ])
    distance_valid = np.asarray([
        finite_number(item.get("distance_cm_raw"))
        and 40.0 <= float(item["distance_cm_raw"]) <= 150.0
        for item in measurement
    ])
    fresh = np.asarray([
        finite_number(item.get("phase_age_ms")) and float(item["phase_age_ms"]) <= 500.0
        for item in measurement
    ])
    finite = np.isfinite(phases)
    usable = present & distance_valid & fresh & finite
    duration = float(timestamps[-1] - timestamps[0])
    return {
        "records": len(measurement),
        "duration_s": duration,
        "effective_hz": float((len(timestamps) - 1) / duration),
        "interval_min_s": float(np.min(intervals)),
        "interval_median_s": float(np.median(intervals)),
        "interval_max_s": float(np.max(intervals)),
        "sequence_gaps": sum(max(0, b - a - 1) for a, b in zip(sequences, sequences[1:])),
        "stream_gaps": int(np.sum(intervals > 0.5)),
        "presence_valid_rate": float(np.mean(present)),
        "distance_valid_rate": float(np.mean(distance_valid)),
        "phase_finite_rate": float(np.mean(finite)),
        "stale_records": int(np.sum(~fresh)),
        "usable_rate": float(np.mean(usable)),
        "phase": {
            "min": float(np.min(phases[finite])),
            "max": float(np.max(phases[finite])),
            "mean": float(np.mean(phases[finite])),
            "std": float(np.std(phases[finite])),
            "range": float(np.ptp(phases[finite])),
        },
        "distance_median_cm": float(np.median([
            float(item["distance_cm_raw"])
            for item in measurement if finite_number(item.get("distance_cm_raw"))
        ])),
    }


def spectral_diagnostic(
    timestamps: np.ndarray,
    values: np.ndarray,
    *,
    target_rpm: float | None = None,
    detrend_degree: int = 1,
    window: str = "hann",
    actual_sample_rate: bool = False,
) -> dict[str, Any]:
    if actual_sample_rate:
        sample_rate_hz = float((len(timestamps) - 1) / (timestamps[-1] - timestamps[0]))
        target_timestamps = np.linspace(timestamps[0], timestamps[-1], len(timestamps))
    else:
        sample_rate_hz = 10.0
        target_timestamps = timestamps[0] + np.arange(len(values)) / sample_rate_hz
    uniform = np.interp(target_timestamps, timestamps, values)
    base = target_timestamps - target_timestamps[0]
    trend = np.polyval(np.polyfit(base, uniform, detrend_degree), base)
    detrended = uniform - trend
    if window == "rectangular":
        weights = np.ones(len(detrended))
    elif window == "blackman":
        weights = np.blackman(len(detrended))
    else:
        weights = np.hanning(len(detrended))
    nfft = max(4096, 1 << (len(detrended) - 1).bit_length())
    spectrum = np.abs(np.fft.rfft(detrended * weights, n=nfft))
    frequencies = np.fft.rfftfreq(nfft, d=1.0 / sample_rate_hz)
    band_indices = np.flatnonzero((frequencies >= 5.0 / 60.0) & (frequencies <= 40.0 / 60.0))
    peak_index = int(band_indices[np.argmax(spectrum[band_indices])])

    def interpolated_rpm(index: int) -> float:
        frequency = float(frequencies[index])
        if 0 < index < len(spectrum) - 1:
            left, center, right = spectrum[index - 1:index + 2]
            denominator = left - 2.0 * center + right
            if abs(denominator) > 1e-12:
                frequency += float(0.5 * (left - right) / denominator) * float(frequencies[1])
        return frequency * 60.0

    local_peaks = [
        int(index) for index in band_indices
        if 0 < index < len(spectrum) - 1
        and spectrum[index] >= spectrum[index - 1]
        and spectrum[index] > spectrum[index + 1]
    ]
    strongest = sorted(local_peaks, key=lambda index: spectrum[index], reverse=True)[:6]
    band_floor = float(np.median(spectrum[band_indices]))
    expected_index = (
        int(np.argmin(np.abs(frequencies - target_rpm / 60.0)))
        if target_rpm is not None else None
    )
    return {
        "selected_rpm": interpolated_rpm(peak_index),
        "peak_ratio": float(spectrum[peak_index] / max(band_floor, 1e-12)),
        "phase_std": float(np.std(detrended)),
        "actual_duration_s": float(timestamps[-1] - timestamps[0]),
        "effective_hz": float((len(timestamps) - 1) / (timestamps[-1] - timestamps[0])),
        "assumed_hz": sample_rate_hz,
        "nfft": nfft,
        "zero_padded_bin_hz": float(frequencies[1]),
        "observation_resolution_hz": float(sample_rate_hz / len(detrended)),
        "top_peaks": [
            {
                "rpm": interpolated_rpm(index),
                "hz": interpolated_rpm(index) / 60.0,
                "magnitude": float(spectrum[index]),
                "relative": float(spectrum[index] / spectrum[peak_index]),
            }
            for index in strongest
        ],
        "target_bin": (
            {
                "rpm": float(frequencies[expected_index] * 60.0),
                "magnitude": float(spectrum[expected_index]),
                "relative_to_selected": float(spectrum[expected_index] / spectrum[peak_index]),
            }
            if expected_index is not None else None
        ),
        "uniform": uniform,
        "detrended": detrended,
        "frequencies": frequencies,
        "spectrum": spectrum,
    }


def capture_production_windows(
    records: list[dict[str, Any]], measurement: list[dict[str, Any]], bounds: dict[str, int],
    target_rpm: float | None = None,
) -> tuple[list[dict[str, Any]], Counter[str]]:
    sensors = [item for item in records if item.get("kind") == "sensor"]
    adapter = MR60ESPAdapter(strict_provenance=False)
    windows: list[dict[str, Any]] = []
    resets: Counter[str] = Counter()
    active = False
    started = False
    for item in sensors:
        timestamp_ms = item.get("ts_monotonic_ms")
        if not finite_number(timestamp_ms):
            continue
        if float(timestamp_ms) < bounds["start_ms"]:
            adapter.process(item)
            continue
        if float(timestamp_ms) >= bounds["end_ms"]:
            break
        if not started:
            adapter.estimator.reset("MMWAVE_REPLAY_ANALYSIS_START")
            started = True
        before = len(adapter.estimator.values)
        packet = adapter.process(item)
        mmwave = packet["mmwave_mr60"]
        after = len(adapter.estimator.values)
        if not active and after > 0:
            active = True
        if mmwave["valid"]:
            timestamps = np.asarray(adapter.estimator.timestamps, dtype=np.float64)
            values = np.asarray(adapter.estimator.values, dtype=np.float64)
            diagnostic = spectral_diagnostic(timestamps, values, target_rpm=target_rpm)
            windows.append({
                "window_index": len(windows) + 1,
                "window_start_s": float(timestamps[0]),
                "window_end_s": float(timestamps[-1]),
                "timestamps": timestamps,
                "values": values,
                "raw_phase": {
                    "min": float(np.min(values)),
                    "max": float(np.max(values)),
                    "mean": float(np.mean(values)),
                    "std": float(np.std(values)),
                    "range": float(np.ptp(values)),
                },
                **diagnostic,
            })
            adapter.estimator.reset("MMWAVE_REPLAY_WINDOW_COMPLETE")
            active = False
        elif active and before > 0 and after == 0:
            resets[mmwave.get("fault_reason") or "MMWAVE_WINDOW_INVALID"] += 1
            active = False
    if active and adapter.estimator.values:
        resets["MMWAVE_INSUFFICIENT_HISTORY"] += 1
    return windows, resets


def summarize_method(values: dict[float, list[float]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    all_errors: list[float] = []
    for target, estimates in values.items():
        errors = [abs(value - target) for value in estimates]
        all_errors.extend(errors)
        result[str(int(target))] = {
            "estimates_rpm": estimates,
            "valid_windows": len(estimates),
            "mae_rpm": statistics.fmean(errors) if errors else None,
            "max_error_rpm": max(errors) if errors else None,
            "within_2rpm": sum(error <= 2.0 for error in errors),
        }
    result["overall"] = {
        "valid_windows": len(all_errors),
        "mae_rpm": statistics.fmean(all_errors) if all_errors else None,
        "max_error_rpm": max(all_errors) if all_errors else None,
        "within_2rpm": sum(error <= 2.0 for error in all_errors),
    }
    return result


def diagnostic_methods(windows_by_target: dict[float, list[dict[str, Any]]]) -> dict[str, Any]:
    methods = {
        "current": {},
        "actual_sample_rate": {},
        "rectangular_window": {},
        "blackman_window": {},
        "mean_detrend": {},
        "quadratic_detrend": {},
        "spectral_peak_ratio_gate_2_0": {},
    }
    for target, windows in windows_by_target.items():
        methods["current"][target] = [float(item["selected_rpm"]) for item in windows]
        variants = {
            "actual_sample_rate": {"actual_sample_rate": True},
            "rectangular_window": {"window": "rectangular"},
            "blackman_window": {"window": "blackman"},
            "mean_detrend": {"detrend_degree": 0},
            "quadratic_detrend": {"detrend_degree": 2},
        }
        for name, kwargs in variants.items():
            methods[name][target] = [
                float(spectral_diagnostic(
                    np.asarray(item["timestamps"]), np.asarray(item["values"]), **kwargs
                )["selected_rpm"])
                for item in windows
            ]
        methods["spectral_peak_ratio_gate_2_0"][target] = [
            float(item["selected_rpm"])
            for item in windows if float(item["peak_ratio"]) >= SPECTRAL_GATE_CANDIDATE
        ]
    return {name: summarize_method(values) for name, values in methods.items()}


def json_safe_window(window: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value for key, value in window.items()
        if key not in {"uniform", "detrended", "frequencies", "spectrum", "timestamps", "values"}
    }


def create_plots(
    output_dir: Path,
    measurements: dict[float, list[dict[str, Any]]],
    windows_by_target: dict[float, list[dict[str, Any]]],
) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True)
    for axis, target in zip(axes, (12.0, 15.0, 20.0)):
        records = measurements[target]
        timestamps = np.asarray([float(item["ts_monotonic_ms"]) / 1000.0 for item in records])
        phase = np.asarray([float(item["breath_phase"]) for item in records])
        axis.plot(timestamps - timestamps[0], phase, linewidth=0.7)
        axis.set_title(f"Real MR60 breath_phase — {int(target)} rpm")
        axis.set_ylabel("phase")
        axis.grid(alpha=0.25)
    axes[-1].set_xlabel("measurement time (s)")
    fig.tight_layout()
    fig.savefig(output_dir / "time_domain_12_15_20rpm.png", dpi=150)
    plt.close(fig)

    for target in (12.0, 15.0, 20.0):
        selected = windows_by_target[target]
        plot_windows = selected[:1] if target != 20.0 else selected
        fig, axis = plt.subplots(figsize=(10, 5))
        for item in plot_windows:
            frequencies = np.asarray(item["frequencies"])
            spectrum = np.asarray(item["spectrum"])
            band = (frequencies >= 5.0 / 60.0) & (frequencies <= 40.0 / 60.0)
            peak = float(np.max(spectrum[band]))
            axis.plot(
                frequencies[band] * 60.0,
                spectrum[band] / max(peak, 1e-12),
                label=f"window {item['window_index']} → {item['selected_rpm']:.2f} rpm",
            )
            axis.axvline(item["selected_rpm"], linewidth=0.7, alpha=0.45)
        axis.axvline(target, color="black", linestyle="--", linewidth=1.5, label=f"GT {target:.0f} rpm")
        axis.set_xlim(5, 40)
        axis.set_xlabel("respiration rate (rpm)")
        axis.set_ylabel("normalized magnitude")
        axis.set_title(f"Production-equivalent spectra — {int(target)} rpm")
        axis.grid(alpha=0.25)
        axis.legend(fontsize=8)
        fig.tight_layout()
        fig.savefig(output_dir / f"spectrum_{int(target)}rpm.png", dpi=150)
        plt.close(fig)


def write_csv(output_dir: Path, windows_by_target: dict[float, list[dict[str, Any]]]) -> None:
    columns = [
        "target_rpm", "window_index", "selected_rpm", "absolute_error_rpm",
        "peak_ratio", "phase_std", "actual_duration_s", "effective_hz",
        "strongest_peak_rpm", "second_peak_rpm", "second_peak_relative",
    ]
    with (output_dir / "production_windows.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        for target, windows in windows_by_target.items():
            for item in windows:
                peaks = item["top_peaks"]
                writer.writerow({
                    "target_rpm": target,
                    "window_index": item["window_index"],
                    "selected_rpm": item["selected_rpm"],
                    "absolute_error_rpm": abs(float(item["selected_rpm"]) - target),
                    "peak_ratio": item["peak_ratio"],
                    "phase_std": item["phase_std"],
                    "actual_duration_s": item["actual_duration_s"],
                    "effective_hz": item["effective_hz"],
                    "strongest_peak_rpm": peaks[0]["rpm"] if peaks else None,
                    "second_peak_rpm": peaks[1]["rpm"] if len(peaks) > 1 else None,
                    "second_peak_relative": peaks[1]["relative"] if len(peaks) > 1 else None,
                })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    datasets: dict[str, Any] = {}
    measurements: dict[float, list[dict[str, Any]]] = {}
    windows_by_target: dict[float, list[dict[str, Any]]] = {}
    for target, path in CASES:
        records, measurement, bounds = load_measurement(path)
        windows, resets = capture_production_windows(records, measurement, bounds, target)
        measurements[target] = measurement
        windows_by_target[target] = windows
        datasets[str(int(target))] = {
            "target_rpm": target,
            "source_file": str(path.relative_to(REPO_ROOT)),
            "source_sha256": sha256_file(path),
            "bounds": bounds,
            "quality": quality_metrics(measurement),
            "resets": dict(resets),
            "windows": [json_safe_window(item) for item in windows],
        }

    methods = diagnostic_methods(windows_by_target)
    output = {
        "analysis": "mmwave_20rpm_root_cause",
        "production_config": {
            "sample_rate_hz": 10.0,
            "window_samples": 300,
            "window_seconds": 30.0,
            "respiration_band_rpm": [5.0, 40.0],
            "detrend_degree": 1,
            "window_function": "hann",
            "nfft": 4096,
            "peak_selection": "largest magnitude in band plus 3-bin parabolic interpolation",
            "spectral_peak_ratio_validity_gate": None,
        },
        "datasets": datasets,
        "diagnostic_methods": methods,
        "root_cause": "I. MULTIPLE_CONTRIBUTING_FACTORS",
        "code_change": "CHANGE_RECOMMENDED",
        "recommended_diagnostic_gate": SPECTRAL_GATE_CANDIDATE,
    }
    (output_dir / "analysis_summary.json").write_text(
        json.dumps(output, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    write_csv(output_dir, windows_by_target)
    create_plots(output_dir, measurements, windows_by_target)
    print(json.dumps({
        "output_dir": str(output_dir),
        "windows": {str(int(key)): len(value) for key, value in windows_by_target.items()},
        "current": methods["current"]["overall"],
        "spectral_gate": methods["spectral_peak_ratio_gate_2_0"]["overall"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
