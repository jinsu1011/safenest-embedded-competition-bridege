#!/usr/bin/env python3
"""Audit ±10 s S2 time alignment without changing the holdout evaluation."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import statistics as stats

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from hr_sideband_stage1 import sha256


HALF_WINDOW_NS = int(2.5 * 1_000_000_000)
SHIFTS_SECONDS = tuple(range(-10, 11))


def load_jsonl_skip_invalid(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sensor-log", type=Path, action="append", required=True)
    parser.add_argument("--receipts", type=Path, action="append", required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if len(args.sensor_log) != len(args.receipts):
        raise SystemExit("sensor-log/receipts count mismatch")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    receipt_rows = []
    for sensor_path, receipt_path in zip(args.sensor_log, args.receipts):
        sensors = load_jsonl_skip_invalid(sensor_path)
        by_seq = {row.get("seq"): row for row in sensors}
        receipt_rows.extend(
            (receipt["host_monotonic_ns"], by_seq[receipt["seq"]])
            for receipt in load_jsonl_skip_invalid(receipt_path)
            if receipt.get("seq") in by_seq
        )
    reference = json.loads(args.reference.read_text(encoding="utf-8"))
    watch = np.asarray([row["watch_bpm"] for row in reference["samples"]], dtype=float)

    scan = []
    for shift_s in SHIFTS_SECONDS:
        vendor = []
        for sample in reference["samples"]:
            target_ns = sample["host_monotonic_ns"] + int(shift_s * 1_000_000_000)
            values = [
                float(record["heart_rate_raw"])
                for host_ns, record in receipt_rows
                if abs(host_ns - target_ns) <= HALF_WINDOW_NS
                and record.get("heart_raw_valid") is True
                and isinstance(record.get("heart_rate_raw"), (int, float))
                and not isinstance(record.get("heart_rate_raw"), bool)
                and record["heart_rate_raw"] > 0
            ]
            if not values:
                raise SystemExit(f"no pair at shift {shift_s:+d}s")
            vendor.append(stats.median(values))
        correlation = float(np.corrcoef(watch, np.asarray(vendor, dtype=float))[0, 1])
        scan.append({
            "shift_seconds": shift_s,
            "pearson_r": correlation,
            "vendor_medians_bpm": vendor,
        })

    best = max(scan, key=lambda row: row["pearson_r"])
    maximum_at_boundary = best["shift_seconds"] in (SHIFTS_SECONDS[0], SHIFTS_SECONDS[-1])
    interior_local_peaks = []
    for left, center, right in zip(scan, scan[1:], scan[2:]):
        if center["pearson_r"] > left["pearson_r"] and center["pearson_r"] > right["pearson_r"]:
            interior_local_peaks.append(center["shift_seconds"])
    single_interior_peak = not maximum_at_boundary and len(interior_local_peaks) == 1

    fig, ax = plt.subplots(figsize=(8.4, 4.5))
    ax.plot(
        [row["shift_seconds"] for row in scan],
        [row["pearson_r"] for row in scan],
        marker="o",
    )
    ax.axvline(0, color="0.5", linewidth=0.9)
    ax.scatter([best["shift_seconds"]], [best["pearson_r"]], marker="s", s=65,
               label=f"max at boundary {best['shift_seconds']:+d}s, r={best['pearson_r']:.3f}")
    ax.set_xlabel("Applied MR60 time shift (s)")
    ax.set_ylabel("Watch–MR60 Pearson r")
    ax.set_title("S2 ±10 s time-alignment audit")
    ax.set_xticks(list(SHIFTS_SECONDS)[::2])
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    plot_path = args.output_dir / "s2_time_sync_scan.png"
    fig.savefig(plot_path, dpi=180)
    plt.close(fig)

    csv_path = args.output_dir / "s2_time_sync_scan.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=("shift_seconds", "pearson_r", "vendor_medians_bpm"),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(scan)

    result = {
        "audit_id": "mr60_hr_s2_time_sync_20260801",
        "search_range_seconds": [-10, 10],
        "step_seconds": 1,
        "pair_half_window_seconds": HALF_WINDOW_NS / 1e9,
        "best_shift_seconds": best["shift_seconds"],
        "best_pearson_r": best["pearson_r"],
        "maximum_at_boundary": maximum_at_boundary,
        "interior_local_peak_shifts_seconds": interior_local_peaks,
        "single_interior_peak": single_interior_peak,
        "correction_applied": False,
        "decision": (
            "NO_CORRECTION_MAXIMUM_AT_SEARCH_BOUNDARY"
            if maximum_at_boundary
            else "NO_CORRECTION_NO_SINGLE_INTERIOR_PEAK"
        ),
        "scan": scan,
    }
    result_path = args.output_dir / "s2_time_sync_audit.json"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    manifest_path = args.output_dir / "s2_time_sync_manifest.json"
    artifacts = [*args.sensor_log, *args.receipts, args.reference, Path(__file__), result_path, csv_path, plot_path]
    manifest_path.write_text(json.dumps({
        "manifest_version": "1.0",
        "audit_id": result["audit_id"],
        "artifacts": [
            {"path": str(path), "sha256": sha256(path), "size_bytes": path.stat().st_size}
            for path in artifacts
        ],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
