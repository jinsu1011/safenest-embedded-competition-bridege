#!/usr/bin/env python3
"""Analyze the shortened S2 recovery holdout without tuning Stage 1 parameters."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
import statistics as stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from hr_sideband_stage1 import (
    MATCH_TOLERANCE_BPM,
    analyze_cue,
    linear_regression,
    plot_spectrum,
    sha256,
)


PAIR_HALF_WINDOW_NS = int(2.5 * 1_000_000_000)
CAUSAL_WINDOW_NS = int(30.5 * 1_000_000_000)
MIN_STABLE_PRESENCE_RATE = 0.95


def load_jsonl_skip_invalid(path: Path) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    invalid: list[dict] = []
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                invalid.append({"line": line_number, "error": str(error)})
    return rows, invalid


def finite_positive(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and float(value) > 0.0
    )


def pearson(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) < 2 or np.std(xs) == 0.0 or np.std(ys) == 0.0:
        return None
    return float(np.corrcoef(xs, ys)[0, 1])


def plot_recovery(rows: list[dict], output: Path) -> None:
    elapsed = [row["elapsed_from_entry_s"] for row in rows]
    watch = [row["watch_bpm"] for row in rows]
    vendor = [row["vendor_mr60_bpm"] for row in rows]
    fig, ax = plt.subplots(figsize=(8.8, 4.9))
    ax.plot(elapsed, watch, marker="o", linewidth=1.8, label="Apple Watch")
    ax.plot(elapsed, vendor, marker="s", linewidth=1.5, label="Vendor MR60")
    for row in rows:
        ax.annotate(
            f"{row['watch_bpm']:.0f}/{row['vendor_mr60_bpm']:.0f}",
            (row["elapsed_from_entry_s"], max(row["watch_bpm"], row["vendor_mr60_bpm"])),
            xytext=(0, 7), textcoords="offset points", ha="center", fontsize=7,
        )
    ax.set_xlabel("Elapsed from entry (s)")
    ax.set_ylabel("Heart rate (bpm)")
    ax.set_title("Shortened S2 recovery: Watch / vendor MR60")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def plot_combined_scatter(s1: list[dict], s2: list[dict], regression: dict, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 5.3))
    ax.scatter(
        [row["respiration_rpm"] for row in s1],
        [row["vendor_error_bpm"] for row in s1],
        marker="o", s=46, label="S1 training",
    )
    ax.scatter(
        [row["respiration_rpm"] for row in s2],
        [row["vendor_error_bpm"] for row in s2],
        marker="^", s=58, label="S2 holdout",
    )
    all_rows = s1 + s2
    for prefix, rows in (("S1-", s1), ("S2-", s2)):
        for row in rows:
            ax.annotate(
                f"{prefix}{row['index']}",
                (row["respiration_rpm"], row["vendor_error_bpm"]),
                xytext=(4, 4), textcoords="offset points", fontsize=7,
            )
    xs = np.asarray([row["respiration_rpm"] for row in all_rows])
    grid = np.linspace(max(0.0, float(np.min(xs)) - 1.0), float(np.max(xs)) + 1.0, 120)
    if regression["slope"] is not None:
        ax.plot(
            grid,
            regression["slope"] * grid + regression["intercept_bpm"],
            linewidth=1.6,
            label=f"combined fit slope={regression['slope']:.2f}, r={regression['pearson_r']:.2f}",
        )
    ax.plot(grid, grid, linestyle="--", linewidth=1.0, label="+1 × respiration")
    ax.plot(grid, 2.0 * grid, linestyle=":", linewidth=1.0, label="+2 × respiration")
    ax.axhline(0.0, color="0.5", linewidth=0.8)
    ax.set_xlabel("Self phase respiration estimate (rpm)")
    ax.set_ylabel("Vendor MR60 − Apple Watch (bpm)")
    ax.set_title("S1 + shortened S2: heart error vs respiration")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output, dpi=180)
    plt.close(fig)


def write_csv(rows: list[dict], output: Path) -> None:
    fields = [
        "index", "elapsed_from_entry_s", "watch_bpm", "vendor_mr60_bpm",
        "vendor_error_bpm", "mr60_samples", "valid", "exclusion_reason",
        "stable_presence_rate", "respiration_rpm", "breath_phase_std",
        "breath_spectral_peak_ratio", "vendor_error_nearest_order",
        "vendor_error_order_residual_bpm", "vendor_error_sideband_match",
        "dominant_total_peak_bpm", "dominant_spectrum_nearest_order",
        "dominant_spectrum_order_residual_bpm", "dominant_spectrum_sideband_match",
        "vendor_to_watch_amplitude_ratio", "max_predicted_sideband_to_base_ratio",
    ]
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sensor-log", type=Path, required=True)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--stage1-results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    sensors, invalid_sensor_lines = load_jsonl_skip_invalid(args.sensor_log)
    receipts, invalid_receipt_lines = load_jsonl_skip_invalid(args.receipts)
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    stage1 = json.loads(args.stage1_results.read_text(encoding="utf-8"))
    sensor_by_seq = {row.get("seq"): row for row in sensors if isinstance(row.get("seq"), int)}
    receipt_rows = [
        (row["host_monotonic_ns"], sensor_by_seq[row["seq"]])
        for row in receipts
        if row.get("seq") in sensor_by_seq and isinstance(row.get("host_monotonic_ns"), int)
    ]

    analyzed: list[dict] = []
    for sample in reference["samples"]:
        prompt_ns = sample["host_monotonic_ns"]
        heart_values = [
            float(record["heart_rate_raw"])
            for host_ns, record in receipt_rows
            if abs(host_ns - prompt_ns) <= PAIR_HALF_WINDOW_NS
            and record.get("heart_raw_valid") is True
            and finite_positive(record.get("heart_rate_raw"))
        ]
        vendor = stats.median(heart_values) if heart_values else None
        paired = {
            "watch_bpm": float(sample["watch_bpm"]),
            "mr60_median_bpm": vendor,
            "error_bpm": vendor - float(sample["watch_bpm"]) if vendor is not None else None,
        }
        prompt = {
            "index": sample["sample"],
            "scheduled_elapsed_s": sample["elapsed_from_entry_s"],
        }
        causal_rows = [
            (host_ns, record)
            for host_ns, record in receipt_rows
            if prompt_ns - CAUSAL_WINDOW_NS <= host_ns <= prompt_ns
        ]
        stable_rate = (
            sum(record.get("human_detected_stable") is True for _, record in causal_rows)
            / len(causal_rows)
            if causal_rows else 0.0
        )
        if vendor is None:
            result = {
                "index": sample["sample"],
                "scheduled_elapsed_s": sample["elapsed_from_entry_s"],
                "watch_bpm": sample["watch_bpm"],
                "vendor_mr60_bpm": None,
                "vendor_error_bpm": None,
                "valid": False,
                "exclusion_reason": "NO_VALID_VENDOR_HEART_PAIR",
            }
        else:
            result = analyze_cue(prompt, paired, causal_rows)
        result["elapsed_from_entry_s"] = sample["elapsed_from_entry_s"]
        result["mr60_samples"] = len(heart_values)
        result["stable_presence_rate"] = stable_rate
        if result.get("valid") and stable_rate < MIN_STABLE_PRESENCE_RATE:
            result["valid"] = False
            result["exclusion_reason"] = "CAUSAL_WINDOW_STABLE_PRESENCE_BELOW_95_PERCENT"
        analyzed.append(result)

    paired_rows = [row for row in analyzed if row["vendor_error_bpm"] is not None]
    valid_s2 = [row for row in analyzed if row.get("valid")]
    s1_valid = [row for row in stage1["cue_results"] if row.get("valid")]
    combined = s1_valid + valid_s2
    regression = linear_regression(
        [row["respiration_rpm"] for row in combined],
        [row["vendor_error_bpm"] for row in combined],
    )
    slope_pass = regression["slope"] is not None and 0.7 <= regression["slope"] <= 1.3
    r_pass = regression["pearson_r"] is not None and regression["pearson_r"] >= 0.6

    direct_matches_s2 = sum(
        row["vendor_error_sideband_match"]
        and row["dominant_spectrum_sideband_match"]
        and row["vendor_error_nearest_order"] == row["dominant_spectrum_nearest_order"]
        for row in valid_s2
    )
    error_matches_s2 = sum(row["vendor_error_sideband_match"] for row in valid_s2)
    h1_supported = slope_pass and r_pass

    errors = [row["vendor_error_bpm"] for row in paired_rows]
    watch = [row["watch_bpm"] for row in paired_rows]
    vendor = [row["vendor_mr60_bpm"] for row in paired_rows]
    recovery = {
        "paired_points": len(paired_rows),
        "observed_span_s": reference["samples"][-1]["elapsed_from_entry_s"],
        "watch_start_bpm": watch[0],
        "watch_end_bpm": watch[-1],
        "watch_change_bpm": watch[-1] - watch[0],
        "vendor_start_bpm": vendor[0],
        "vendor_end_bpm": vendor[-1],
        "vendor_change_bpm": vendor[-1] - vendor[0],
        "mae_bpm": stats.mean(abs(value) for value in errors),
        "bias_bpm": stats.mean(errors),
        "max_abs_error_bpm": max(abs(value) for value in errors),
        "pearson_r_watch_vs_vendor": pearson(watch, vendor),
        "phase2b_recovery_gate_r_at_least_0_5": (
            pearson(watch, vendor) is not None and pearson(watch, vendor) >= 0.5
        ),
        "phase2b_recovery_gate_max_error_at_most_10": max(abs(value) for value in errors) <= 10.0,
    }
    recovery["phase2b_recovery_gate_pass"] = (
        recovery["phase2b_recovery_gate_r_at_least_0_5"]
        and recovery["phase2b_recovery_gate_max_error_at_most_10"]
    )

    plot_recovery(paired_rows, args.output_dir / "s2_recovery_trace.png")
    plot_combined_scatter(s1_valid, valid_s2, regression, args.output_dir / "s1_s2_error_vs_respiration.png")
    representative = [row for row in valid_s2 if row["index"] in (2, 4, 7)]
    for row in representative:
        plot_spectrum(row, args.output_dir / f"s2_spectrum_sample_{row['index']:02d}.png")
    write_csv(analyzed, args.output_dir / "s2_pair_sideband_metrics.csv")

    serializable: list[dict] = []
    for row in analyzed:
        cleaned = dict(row)
        cleaned.pop("_plot", None)
        serializable.append(cleaned)
    result = {
        "analysis_id": "mr60_hr_sideband_stage2_shortened_s2_20260801",
        "holdout_used_once": True,
        "parameters_retuned_from_s2": False,
        "heart_verified": False,
        "h1_final_status": "SUPPORTED" if h1_supported else "REJECTED",
        "stage3_notch_allowed": h1_supported,
        "contracts": {
            "inherited_from_stage1": True,
            "vendor_breath_rate_used": False,
            "fixed_offset_applied": False,
            "missing_value_fill_applied": False,
            "pair_half_window_seconds": PAIR_HALF_WINDOW_NS / 1e9,
            "causal_window_seconds": 30.5,
            "minimum_causal_stable_presence_rate": MIN_STABLE_PRESENCE_RATE,
        },
        "input_quality": {
            "sensor_records_valid": len(sensors),
            "sensor_records_invalid": len(invalid_sensor_lines),
            "invalid_sensor_lines": invalid_sensor_lines,
            "receipt_records_valid": len(receipts),
            "receipt_records_invalid": len(invalid_receipt_lines),
        },
        "s2_recovery": recovery,
        "s2_sideband_valid_points": len(valid_s2),
        "s2_sideband_excluded_points": len(analyzed) - len(valid_s2),
        "s2_sideband_excluded_rate": (len(analyzed) - len(valid_s2)) / len(analyzed),
        "combined_regression_error_vs_respiration": {
            **regression,
            "criterion_slope_0_7_to_1_3": slope_pass,
            "criterion_r_at_least_0_6": r_pass,
            "h1_preregistered_regression_pass": h1_supported,
        },
        "spectrum_evidence": {
            "s1_vendor_error_sideband_match_count": stage1["spectrum_evidence"]["vendor_error_sideband_match_count"],
            "s1_direct_order_match_count": stage1["spectrum_evidence"]["vendor_error_and_dominant_spectrum_order_match_count"],
            "s1_valid_count": stage1["spectrum_evidence"]["valid_count"],
            "s2_vendor_error_sideband_match_count": error_matches_s2,
            "s2_direct_order_match_count": direct_matches_s2,
            "s2_valid_count": len(valid_s2),
            "direct_spectrum_consistent": direct_matches_s2 > 0,
        },
        "notch_evaluation": {
            "performed": False,
            "reason": None if h1_supported else "H1 rejected by preregistered combined regression; Stage 3 prohibited.",
        },
        "samples": serializable,
        "limitations": [
            "S2 was shortened by the user to 185.598 seconds instead of the planned 8 minutes.",
            "The entry sample is retained for recovery tracking but excluded from sideband regression when its causal window lacks stable presence.",
            "Apple Watch is a consumer wearable, not a medical reference.",
        ],
    }
    result_path = args.output_dir / "stage2_results.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    artifacts = [
        args.sensor_log,
        args.receipts,
        args.reference,
        args.stage1_results,
        Path(__file__),
        result_path,
        args.output_dir / "s2_pair_sideband_metrics.csv",
        args.output_dir / "s2_recovery_trace.png",
        args.output_dir / "s1_s2_error_vs_respiration.png",
        *[args.output_dir / f"s2_spectrum_sample_{row['index']:02d}.png" for row in representative],
    ]
    manifest = {
        "manifest_version": "1.0",
        "analysis_id": result["analysis_id"],
        "existing_manifest_modified": False,
        "artifacts": [
            {"path": str(path), "sha256": sha256(path), "size_bytes": path.stat().st_size}
            for path in artifacts
        ],
    }
    (args.output_dir / "stage2_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
