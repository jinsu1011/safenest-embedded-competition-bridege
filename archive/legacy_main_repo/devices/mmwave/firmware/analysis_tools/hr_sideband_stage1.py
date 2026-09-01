#!/usr/bin/env python3
"""Offline Stage 1 test of the MR60 heart/respiration sideband hypothesis."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics as stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


FS_HZ = 10.0
WINDOW_SAMPLES = 300
MAX_GAP_SECONDS = 0.5
MIN_PHASE_STD = 0.05
RESP_BAND_HZ = (5.0 / 60.0, 40.0 / 60.0)
HEART_BAND_HZ = (0.8, 2.0)
SIDE_BAND_ORDERS = (-2, -1, 0, 1, 2)
MATCH_TOLERANCE_BPM = 3.0
NFFT = 4096


def load_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2:
        return None
    if np.std(xs) == 0.0 or np.std(ys) == 0.0:
        return None
    return float(np.corrcoef(xs, ys)[0, 1])


def linear_regression(xs: list[float], ys: list[float]) -> dict:
    if len(xs) < 2 or np.std(xs) == 0.0:
        return {"slope": None, "intercept_bpm": None, "pearson_r": None, "n": len(xs)}
    slope, intercept = np.polyfit(np.asarray(xs), np.asarray(ys), 1)
    return {
        "slope": float(slope),
        "intercept_bpm": float(intercept),
        "pearson_r": pearson(xs, ys),
        "n": len(xs),
    }


def prepare_uniform(rows: list[tuple[int, dict]], field: str) -> tuple[np.ndarray, np.ndarray] | tuple[None, str]:
    samples = []
    for _, record in rows:
        timestamp_ms = record.get("ts_monotonic_ms")
        value = record.get(field)
        if finite_number(timestamp_ms) and finite_number(value):
            samples.append((float(timestamp_ms) / 1000.0, float(value)))
    if len(samples) < 270:
        return None, f"{field.upper()}_INSUFFICIENT_SAMPLES"
    samples.sort()
    timestamps = np.asarray([item[0] for item in samples], dtype=np.float64)
    values = np.asarray([item[1] for item in samples], dtype=np.float64)
    keep = np.concatenate(([True], np.diff(timestamps) > 0.0))
    timestamps, values = timestamps[keep], values[keep]
    if len(values) < 270:
        return None, f"{field.upper()}_DUPLICATE_TIMESTAMPS"
    gaps = np.diff(timestamps)
    if len(gaps) and float(np.max(gaps)) > MAX_GAP_SECONDS:
        return None, f"{field.upper()}_GAP_TOO_LARGE"
    expected_duration = (WINDOW_SAMPLES - 1) / FS_HZ
    if timestamps[-1] - timestamps[0] < expected_duration - MAX_GAP_SECONDS:
        return None, f"{field.upper()}_WINDOW_TOO_SHORT"
    target = timestamps[-1] - expected_duration + np.arange(WINDOW_SAMPLES) / FS_HZ
    if target[0] < timestamps[0] - MAX_GAP_SECONDS:
        return None, f"{field.upper()}_CANNOT_RESAMPLE"
    uniform = np.interp(target, timestamps, values)
    elapsed = target - target[0]
    trend = np.polyval(np.polyfit(elapsed, uniform, 1), elapsed)
    return target, uniform - trend


def spectrum(signal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    amplitudes = np.abs(np.fft.rfft(signal * np.hanning(len(signal)), n=NFFT))
    frequencies = np.fft.rfftfreq(NFFT, d=1.0 / FS_HZ)
    return frequencies, amplitudes


def quadratic_peak(frequencies: np.ndarray, amplitudes: np.ndarray, low: float, high: float) -> tuple[float, float]:
    indices = np.flatnonzero((frequencies >= low) & (frequencies <= high))
    peak = int(indices[np.argmax(amplitudes[indices])])
    peak_frequency = float(frequencies[peak])
    if 0 < peak < len(amplitudes) - 1:
        left, center, right = amplitudes[peak - 1:peak + 2]
        denominator = left - 2.0 * center + right
        if abs(denominator) > 1e-12:
            offset = 0.5 * (left - right) / denominator
            peak_frequency += float(offset) * (frequencies[1] - frequencies[0])
    return peak_frequency, float(amplitudes[peak])


def local_amplitude(frequencies: np.ndarray, amplitudes: np.ndarray, target_hz: float,
                    radius_hz: float = 0.04) -> float | None:
    indices = np.flatnonzero(np.abs(frequencies - target_hz) <= radius_hz)
    if not len(indices):
        return None
    return float(np.max(amplitudes[indices]))


def nearest_order(delta_bpm: float, respiration_rpm: float) -> tuple[int, float]:
    candidates = [(order, abs(delta_bpm - order * respiration_rpm)) for order in SIDE_BAND_ORDERS]
    order, residual = min(candidates, key=lambda item: item[1])
    return int(order), float(residual)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def analyze_cue(prompt: dict, paired: dict, rows: list[tuple[int, dict]]) -> dict:
    breath_prepared = prepare_uniform(rows, "breath_phase")
    total_prepared = prepare_uniform(rows, "total_phase")
    heart_prepared = prepare_uniform(rows, "heart_phase")
    result = {
        "index": prompt["index"],
        "scheduled_elapsed_s": prompt["scheduled_elapsed_s"],
        "watch_bpm": paired["watch_bpm"],
        "vendor_mr60_bpm": paired["mr60_median_bpm"],
        "vendor_error_bpm": paired["error_bpm"],
        "valid": False,
        "exclusion_reason": None,
    }
    for prepared in (breath_prepared, total_prepared, heart_prepared):
        if prepared[0] is None:
            result["exclusion_reason"] = prepared[1]
            return result

    _, breath_signal = breath_prepared
    _, total_signal = total_prepared
    _, heart_signal = heart_prepared
    breath_std = float(np.std(breath_signal))
    if breath_std < MIN_PHASE_STD:
        result["exclusion_reason"] = "BREATH_PHASE_SIGNAL_TOO_FLAT"
        result["breath_phase_std"] = breath_std
        return result

    resp_freqs, resp_amplitudes = spectrum(breath_signal)
    resp_hz, resp_peak_amp = quadratic_peak(resp_freqs, resp_amplitudes, *RESP_BAND_HZ)
    resp_band = (resp_freqs >= RESP_BAND_HZ[0]) & (resp_freqs <= RESP_BAND_HZ[1])
    resp_floor = float(np.median(resp_amplitudes[resp_band]))
    resp_peak_ratio = resp_peak_amp / max(resp_floor, 1e-12)
    respiration_rpm = resp_hz * 60.0

    total_freqs, total_amplitudes = spectrum(total_signal)
    heart_freqs, heart_amplitudes = spectrum(heart_signal)
    dominant_total_hz, dominant_total_amp = quadratic_peak(total_freqs, total_amplitudes, *HEART_BAND_HZ)
    dominant_heart_hz, dominant_heart_amp = quadratic_peak(heart_freqs, heart_amplitudes, *HEART_BAND_HZ)

    watch_hz = float(paired["watch_bpm"]) / 60.0
    vendor_hz = float(paired["mr60_median_bpm"]) / 60.0
    base_amp = local_amplitude(total_freqs, total_amplitudes, watch_hz)
    vendor_amp = local_amplitude(total_freqs, total_amplitudes, vendor_hz)
    predicted = {}
    for order in SIDE_BAND_ORDERS:
        target_hz = watch_hz + order * resp_hz
        if HEART_BAND_HZ[0] <= target_hz <= HEART_BAND_HZ[1]:
            amplitude = local_amplitude(total_freqs, total_amplitudes, target_hz)
            predicted[str(order)] = {
                "frequency_hz": target_hz,
                "bpm": target_hz * 60.0,
                "amplitude": amplitude,
                "to_base_ratio": amplitude / max(base_amp or 0.0, 1e-12),
                "to_vendor_ratio": amplitude / max(vendor_amp or 0.0, 1e-12),
            }

    error_order, error_residual = nearest_order(float(paired["error_bpm"]), respiration_rpm)
    spectral_delta_bpm = dominant_total_hz * 60.0 - float(paired["watch_bpm"])
    spectral_order, spectral_residual = nearest_order(spectral_delta_bpm, respiration_rpm)
    nonzero_ratios = [value["to_base_ratio"] for key, value in predicted.items() if key != "0"]
    breath_valid_rate = sum(record.get("breath_filtered_valid") is True for _, record in rows) / len(rows)

    result.update({
        "valid": True,
        "respiration_rpm": respiration_rpm,
        "breath_phase_std": breath_std,
        "breath_spectral_peak_ratio": resp_peak_ratio,
        "breath_filtered_valid_rate": breath_valid_rate,
        "vendor_error_nearest_order": error_order,
        "vendor_error_order_residual_bpm": error_residual,
        "vendor_error_sideband_match": error_order != 0 and error_residual <= MATCH_TOLERANCE_BPM,
        "dominant_total_peak_bpm": dominant_total_hz * 60.0,
        "dominant_total_peak_amplitude": dominant_total_amp,
        "dominant_heart_phase_peak_bpm": dominant_heart_hz * 60.0,
        "dominant_heart_phase_peak_amplitude": dominant_heart_amp,
        "dominant_spectrum_nearest_order": spectral_order,
        "dominant_spectrum_order_residual_bpm": spectral_residual,
        "dominant_spectrum_sideband_match": spectral_order != 0 and spectral_residual <= MATCH_TOLERANCE_BPM,
        "watch_fundamental_amplitude": base_amp,
        "vendor_frequency_amplitude": vendor_amp,
        "vendor_to_watch_amplitude_ratio": vendor_amp / max(base_amp or 0.0, 1e-12),
        "max_predicted_sideband_to_base_ratio": max(nonzero_ratios, default=None),
        "predicted_frequencies": predicted,
        "_plot": {
            "total_frequencies": total_freqs,
            "total_amplitudes": total_amplitudes,
            "heart_frequencies": heart_freqs,
            "heart_amplitudes": heart_amplitudes,
        },
    })
    return result


def plot_scatter(rows: list[dict], regression: dict, output: Path) -> None:
    xs = np.asarray([row["respiration_rpm"] for row in rows])
    ys = np.asarray([row["vendor_error_bpm"] for row in rows])
    fig, ax = plt.subplots(figsize=(8.5, 5.2))
    ax.scatter(xs, ys, s=50, label="S1 cue pairs")
    for row in rows:
        ax.annotate(str(row["index"]), (row["respiration_rpm"], row["vendor_error_bpm"]),
                    xytext=(5, 4), textcoords="offset points", fontsize=8)
    if regression["slope"] is not None:
        grid = np.linspace(min(xs) - 0.5, max(xs) + 0.5, 100)
        ax.plot(grid, regression["slope"] * grid + regression["intercept_bpm"],
                label=f"fit slope={regression['slope']:.2f}, r={regression['pearson_r']:.2f}")
    grid = np.linspace(max(0.0, min(xs) - 0.5), max(xs) + 0.5, 100)
    ax.plot(grid, grid, linestyle="--", linewidth=1, label="+1 × respiration")
    ax.plot(grid, 2.0 * grid, linestyle=":", linewidth=1, label="+2 × respiration")
    ax.axhline(0.0, color="0.5", linewidth=0.8)
    ax.set_xlabel("Self phase respiration estimate (rpm)")
    ax.set_ylabel("Vendor MR60 − Apple Watch (bpm)")
    ax.set_title("S1 heart error vs respiration")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_spectrum(row: dict, output: Path) -> None:
    plot = row["_plot"]
    fig, axes = plt.subplots(2, 1, figsize=(9, 6.8), sharex=True)
    for ax, frequency_key, amplitude_key, label in (
        (axes[0], "total_frequencies", "total_amplitudes", "total_phase (raw source)"),
        (axes[1], "heart_frequencies", "heart_amplitudes", "heart_phase (vendor-separated auxiliary)"),
    ):
        frequencies = plot[frequency_key]
        amplitudes = plot[amplitude_key]
        band = (frequencies >= HEART_BAND_HZ[0]) & (frequencies <= HEART_BAND_HZ[1])
        normalized = amplitudes[band] / max(float(np.max(amplitudes[band])), 1e-12)
        ax.plot(frequencies[band], normalized, label=label)
        ax.axvline(row["watch_bpm"] / 60.0, linestyle="-", linewidth=1.2,
                   label=f"Watch {row['watch_bpm']:.0f} bpm")
        ax.axvline(row["vendor_mr60_bpm"] / 60.0, linestyle="--", linewidth=1.2,
                   label=f"Vendor {row['vendor_mr60_bpm']:.0f} bpm")
        for order_text, predicted in row["predicted_frequencies"].items():
            order = int(order_text)
            if order == 0:
                continue
            ax.axvline(predicted["frequency_hz"], linestyle=":" if abs(order) == 1 else "-.",
                       linewidth=0.8, alpha=0.75, label=f"Watch {order:+d}×resp")
        ax.set_ylabel("Normalized amplitude")
        ax.grid(alpha=0.2)
        handles, labels = ax.get_legend_handles_labels()
        unique = dict(zip(labels, handles))
        ax.legend(unique.values(), unique.keys(), fontsize=7, ncol=3)
    axes[-1].set_xlabel("Frequency (Hz)")
    fig.suptitle(
        f"Cue {row['index']}: error {row['vendor_error_bpm']:+.0f} bpm, "
        f"resp {row['respiration_rpm']:.1f} rpm"
    )
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_coupling(rows: list[dict], output: Path) -> None:
    indices = [row["index"] for row in rows]
    errors = [abs(row["vendor_error_bpm"]) for row in rows]
    ratios = [row["max_predicted_sideband_to_base_ratio"] for row in rows]
    breath_std = [row["breath_phase_std"] for row in rows]
    fig, ax1 = plt.subplots(figsize=(9, 4.8))
    ax1.plot(indices, errors, marker="o", label="|heart error| (bpm)")
    ax1.plot(indices, ratios, marker="s", label="max sideband/base ratio")
    ax1.set_xlabel("Cue index")
    ax1.set_ylabel("Error / amplitude ratio")
    ax2 = ax1.twinx()
    ax2.plot(indices, breath_std, marker="^", linestyle="--", label="breath phase std")
    ax2.set_ylabel("Breath phase std")
    lines = ax1.get_lines() + ax2.get_lines()
    ax1.legend(lines, [line.get_label() for line in lines], fontsize=8, ncol=3)
    ax1.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def write_csv(rows: list[dict], path: Path) -> None:
    columns = [
        "index", "watch_bpm", "vendor_mr60_bpm", "vendor_error_bpm",
        "respiration_rpm", "breath_phase_std", "breath_spectral_peak_ratio",
        "breath_filtered_valid_rate", "vendor_error_nearest_order",
        "vendor_error_order_residual_bpm", "vendor_error_sideband_match",
        "dominant_total_peak_bpm", "dominant_heart_phase_peak_bpm",
        "dominant_spectrum_nearest_order", "dominant_spectrum_order_residual_bpm",
        "dominant_spectrum_sideband_match", "vendor_to_watch_amplitude_ratio",
        "max_predicted_sideband_to_base_ratio",
    ]
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=columns, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sensor-log", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--prompts", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    sensors = load_jsonl(args.sensor_log)
    receipts = load_jsonl(args.receipts)
    prompts = load_jsonl(args.prompts)
    comparison = json.loads(args.comparison.read_text(encoding="utf-8"))
    paired_by_index = {item["index"]: item for item in comparison["paired_points"]}
    sensor_by_seq = {record.get("seq"): record for record in sensors}
    receipt_rows = [
        (receipt["host_monotonic_ns"], sensor_by_seq[receipt.get("seq")])
        for receipt in receipts if receipt.get("seq") in sensor_by_seq
    ]

    cue_results = []
    for prompt in prompts:
        end_ns = prompt["host_monotonic_ns"]
        start_ns = end_ns - int(30.5 * 1_000_000_000)
        rows = [(host_ns, record) for host_ns, record in receipt_rows if start_ns <= host_ns <= end_ns]
        cue_results.append(analyze_cue(prompt, paired_by_index[prompt["index"]], rows))

    valid_rows = [row for row in cue_results if row["valid"]]
    respiration = [row["respiration_rpm"] for row in valid_rows]
    errors = [row["vendor_error_bpm"] for row in valid_rows]
    regression = linear_regression(respiration, errors)
    regression["criterion_slope_0_7_to_1_3"] = (
        regression["slope"] is not None and 0.7 <= regression["slope"] <= 1.3
    )
    regression["criterion_r_at_least_0_6"] = (
        regression["pearson_r"] is not None and regression["pearson_r"] >= 0.6
    )
    regression["stage1_preliminary_pass"] = (
        regression["criterion_slope_0_7_to_1_3"] and regression["criterion_r_at_least_0_6"]
    )

    error_matches = sum(row["vendor_error_sideband_match"] for row in valid_rows)
    direct_matches = sum(
        row["vendor_error_sideband_match"]
        and row["dominant_spectrum_sideband_match"]
        and row["vendor_error_nearest_order"] == row["dominant_spectrum_nearest_order"]
        for row in valid_rows
    )
    coupling = {
        "abs_error_vs_breath_phase_std_r": pearson(
            [abs(row["vendor_error_bpm"]) for row in valid_rows],
            [row["breath_phase_std"] for row in valid_rows],
        ),
        "sideband_ratio_vs_breath_phase_std_r": pearson(
            [row["max_predicted_sideband_to_base_ratio"] for row in valid_rows],
            [row["breath_phase_std"] for row in valid_rows],
        ),
        "sideband_ratio_vs_breath_peak_ratio_r": pearson(
            [row["max_predicted_sideband_to_base_ratio"] for row in valid_rows],
            [row["breath_spectral_peak_ratio"] for row in valid_rows],
        ),
        "sideband_ratio_vs_breath_filtered_valid_rate_r": pearson(
            [row["max_predicted_sideband_to_base_ratio"] for row in valid_rows],
            [row["breath_filtered_valid_rate"] for row in valid_rows],
        ),
    }

    plot_scatter(valid_rows, regression, args.output_dir / "s1_error_vs_respiration.png")
    representative_indices = (3, 5, 9)
    for index in representative_indices:
        row = next(item for item in valid_rows if item["index"] == index)
        plot_spectrum(row, args.output_dir / f"s1_spectrum_cue_{index:02d}.png")
    plot_coupling(valid_rows, args.output_dir / "s1_breath_sideband_coupling.png")
    write_csv(cue_results, args.output_dir / "s1_cue_sideband_metrics.csv")

    serializable_rows = []
    for row in cue_results:
        cleaned = dict(row)
        cleaned.pop("_plot", None)
        serializable_rows.append(cleaned)
    outliers = [row for row in serializable_rows if row["index"] in (5, 8, 9)]
    stage1_conclusion = (
        "PRELIMINARY_SUPPORT_PENDING_S2"
        if regression["stage1_preliminary_pass"] and direct_matches >= max(1, len(valid_rows) // 2)
        else "PRELIMINARY_NOT_SUPPORTED_FINAL_PENDING_S2"
    )
    result = {
        "analysis_id": "mr60_hr_sideband_stage1_s1_20260801",
        "hypothesis_final_status": "PENDING_S2",
        "stage1_conclusion": stage1_conclusion,
        "heart_verified": False,
        "contracts": {
            "raw_phase_source": "total_phase",
            "auxiliary_phase_source": "heart_phase",
            "respiration_source": "breath_phase_fft_30s_causal",
            "vendor_breath_rate_used": False,
            "fixed_offset_applied": False,
            "window_seconds": 30.0,
            "sample_rate_hz": FS_HZ,
            "respiration_band_rpm": [5.0, 40.0],
            "heart_band_hz": list(HEART_BAND_HZ),
            "sideband_match_tolerance_bpm": MATCH_TOLERANCE_BPM,
        },
        "valid_cues": len(valid_rows),
        "excluded_cues": len(cue_results) - len(valid_rows),
        "excluded_rate": (len(cue_results) - len(valid_rows)) / len(cue_results),
        "regression_error_vs_respiration": regression,
        "spectrum_evidence": {
            "vendor_error_sideband_match_count": error_matches,
            "vendor_error_and_dominant_spectrum_order_match_count": direct_matches,
            "valid_count": len(valid_rows),
        },
        "coupling": coupling,
        "outliers": outliers,
        "cue_results": serializable_rows,
        "limitations": [
            "S1 Watch range is narrow; final H1 criterion is reserved for preregistered S1+S2 regression.",
            "Apple Watch is a consumer wearable, not a medical reference.",
            "total_phase is the rawest phase field exposed by the fixed ESP schema; heart_phase is auxiliary only.",
        ],
    }
    result_path = args.output_dir / "stage1_results.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    artifact_paths = [
        args.sensor_log, args.receipts, args.prompts, args.reference, args.comparison,
        Path(__file__),
        result_path, args.output_dir / "s1_cue_sideband_metrics.csv",
        args.output_dir / "s1_error_vs_respiration.png",
        args.output_dir / "s1_spectrum_cue_03.png",
        args.output_dir / "s1_spectrum_cue_05.png",
        args.output_dir / "s1_spectrum_cue_09.png",
        args.output_dir / "s1_breath_sideband_coupling.png",
    ]
    manifest = {
        "manifest_version": "1.0",
        "analysis_id": result["analysis_id"],
        "existing_manifest_modified": False,
        "artifacts": [
            {"path": str(path), "sha256": sha256(path), "size_bytes": path.stat().st_size}
            for path in artifact_paths
        ],
    }
    (args.output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
