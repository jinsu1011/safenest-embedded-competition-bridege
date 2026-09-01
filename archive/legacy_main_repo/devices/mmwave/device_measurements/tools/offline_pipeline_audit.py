#!/usr/bin/env python3
"""Run the sensor-free CSV -> BPF -> z-score -> int8 audit.

This intentionally uses the same numerical sequence as the checked-in
experimental preprocessing source, but reads CSV with the standard library so
the audit only needs numpy and scipy.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable

import numpy as np
from scipy import __version__ as scipy_version
from scipy.signal import butter, filtfilt


REQUIRED_COLUMNS = {"timestamp_s", "resp_phase", "subject_id", "session_id", "label"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    missing = REQUIRED_COLUMNS - set(rows[0] if rows else ())
    if missing:
        raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
    return rows


def iter_windows(path: Path, window_samples: int = 300, stride_samples: int = 30,
                 sample_rate_hz: float = 10.0, max_gap_seconds: float = 0.5,
                 max_interpolated_fraction: float = 0.05) -> Iterable[dict]:
    rows = read_rows(path)
    groups: dict[tuple[str, str], list[dict[str, str]]] = {}
    for row in rows:
        groups.setdefault((row["subject_id"], row["session_id"]), []).append(row)

    expected_dt = 1.0 / sample_rate_hz
    for (subject_id, session_id), group in groups.items():
        phase = np.asarray([float(row["resp_phase"]) for row in group], dtype=np.float32)
        timestamps = np.asarray([float(row["timestamp_s"]) for row in group], dtype=np.float64)
        if len(phase) < window_samples or np.any(np.diff(timestamps) <= 0):
            continue
        for start in range(0, len(phase) - window_samples + 1, stride_samples):
            raw_phase = phase[start:start + window_samples]
            raw_ts = timestamps[start:start + window_samples]
            if not np.all(np.isfinite(raw_phase)) or not np.all(np.isfinite(raw_ts)):
                continue
            diffs = np.diff(raw_ts)
            if np.any(diffs > max_gap_seconds):
                continue
            target_ts = raw_ts[0] + np.arange(window_samples) * expected_dt
            if target_ts[-1] > raw_ts[-1] + 1e-5:
                continue
            values = np.interp(target_ts, raw_ts, raw_phase).astype(np.float32)
            interpolated_fraction = float(
                np.sum(np.maximum(0.0, diffs - expected_dt)) / (window_samples / sample_rate_hz)
            )
            if interpolated_fraction > max_interpolated_fraction:
                continue
            yield {
                "values": values,
                "subject_id": subject_id,
                "session_id": session_id,
                "label": group[start].get("label") or None,
                "quality": 1.0 - interpolated_fraction,
                "interpolated_fraction": interpolated_fraction,
            }


def preprocess_window(raw_signal: np.ndarray, mean: float, std: float,
                      b: np.ndarray, a: np.ndarray) -> tuple[np.ndarray, dict]:
    arr = np.asarray(raw_signal, dtype=np.float32).flatten()
    quality = {"valid": True, "reason": "OK", "original_length": len(arr),
               "nan_count": 0, "inf_count": 0}
    if len(arr) != 300:
        quality["valid"] = False
        quality["reason"] = f"Expected 300 samples, got {len(arr)}"
        if len(arr) < 300:
            arr = np.pad(arr, (0, 300 - len(arr)), mode="edge")
        else:
            arr = arr[:300]
    nan_mask = np.isnan(arr)
    inf_mask = np.isinf(arr)
    quality["nan_count"] = int(np.sum(nan_mask))
    quality["inf_count"] = int(np.sum(inf_mask))
    if quality["nan_count"] or quality["inf_count"]:
        quality["valid"] = False
        quality["reason"] = "Signal contains non-finite values"
        arr = np.nan_to_num(arr, nan=mean, posinf=5.0, neginf=-5.0)
    detrended = arr - np.mean(arr)
    filtered = filtfilt(b, a, detrended)
    normalized = (filtered - mean) / std
    clip_mask = (normalized < -5.0) | (normalized > 5.0)
    clipped = np.clip(normalized, -5.0, 5.0).astype(np.float32)
    return clipped.reshape(1, 300, 1), {**quality, "clip_count": int(np.sum(clip_mask))}


def quantize(values: np.ndarray, scale: float, zero_point: int) -> tuple[np.ndarray, np.ndarray]:
    unbounded = np.rint(values / scale) + zero_point
    saturated = (unbounded < -128) | (unbounded > 127)
    quantized = np.clip(unbounded, -128, 127).astype(np.int8)
    return quantized, saturated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv-dir", type=Path, required=True)
    parser.add_argument("--mean", type=float, default=0.0031162832173884064)
    parser.add_argument("--std", type=float, default=2.955399434649939)
    parser.add_argument("--scale", type=float, default=0.041720833629369736)
    parser.add_argument("--zero-point", type=int, default=-3)
    args = parser.parse_args()

    csv_paths = sorted(args.csv_dir.glob("*.csv"))
    if not csv_paths:
        raise SystemExit(f"no CSV files found in {args.csv_dir}")
    b, a = butter(4, [0.1 / 5.0, 0.5 / 5.0], btype="bandpass")
    windows: list[dict] = []
    file_summaries = []
    for path in csv_paths:
        rows = read_rows(path)
        file_windows = list(iter_windows(path))
        windows.extend(file_windows)
        file_summaries.append({"file": path.name, "rows": len(rows), "windows": len(file_windows)})

    raw = np.stack([item["values"] for item in windows]).astype(np.float32)
    processed = []
    quality = []
    for item in raw:
        output, info = preprocess_window(item, args.mean, args.std, b, a)
        processed.append(output)
        quality.append(info)
    processed_array = np.concatenate(processed, axis=0)
    flat = processed_array.reshape(-1)
    quantized, saturated = quantize(flat, args.scale, args.zero_point)
    dequantized = (quantized.astype(np.float32) - args.zero_point) * args.scale

    t = np.arange(300, dtype=np.float32) / 10.0
    synthetic_cases = {
        "clean_sine": 0.8 * np.sin(2 * np.pi * 0.25 * t) + 0.3,
        "constant": np.zeros(300, dtype=np.float32),
        "nan_inf": np.zeros(300, dtype=np.float32),
        "short_signal": np.zeros(100, dtype=np.float32),
    }
    synthetic_cases["nan_inf"][10] = np.nan
    synthetic_cases["nan_inf"][11] = np.inf
    synthetic_results = {}
    for name, signal in synthetic_cases.items():
        output, info = preprocess_window(signal, args.mean, args.std, b, a)
        synthetic_results[name] = {
            "shape": list(output.shape),
            "finite": bool(np.all(np.isfinite(output))),
            "quality_valid": info["valid"],
            "reason": info["reason"],
        }

    result = {
        "runtime": {"numpy": np.__version__, "scipy": scipy_version},
        "source_contract": {
            "sample_rate_hz": 10.0,
            "window_samples": 300,
            "filter": "Butterworth bandpass 0.1-0.5 Hz order 4 + filtfilt",
            "zscore_mean": args.mean,
            "zscore_std": args.std,
            "clip": [-5.0, 5.0],
            "int8_scale": args.scale,
            "int8_zero_point": args.zero_point,
        },
        "csv": {
            "files": len(csv_paths),
            "windows": len(windows),
            "shape": list(processed_array.shape),
            "all_finite": bool(np.all(np.isfinite(processed_array))),
            "quality_invalid": sum(not item["valid"] for item in quality),
            "preprocess_clip_ratio": float(np.sum([item["clip_count"] for item in quality]) / flat.size),
            "processed_mean": float(np.mean(flat)),
            "processed_std": float(np.std(flat)),
            "processed_min": float(np.min(flat)),
            "processed_max": float(np.max(flat)),
            "quantized_min": int(np.min(quantized)),
            "quantized_max": int(np.max(quantized)),
            "quantized_saturation_ratio": float(np.mean(saturated)),
            "dequantized_mae": float(np.mean(np.abs(dequantized - flat))),
            "dequantized_max_abs_error": float(np.max(np.abs(dequantized - flat))),
            "files": file_summaries,
        },
        "synthetic_cases": synthetic_results,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
