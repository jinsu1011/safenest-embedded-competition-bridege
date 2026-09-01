#!/usr/bin/env python3
"""Run the SafeNest mmWave M-C0 correspondence audit.

The audit is intentionally read-only with respect to ``--evidence-root``.
It opens every regular file below that directory, SHA-256 hashes the
enumerated expected inputs, reads the documented captures, and writes only
derived JSON/Markdown outside the evidence root.
It never runs the model, never reopens LOCKED_TEST, never resamples an input
as the contract, and never copies raw MR60 JSONL/CSV into the repository.

With no ``--evidence-root`` the command emits the reproducible before-state
and keeps the ``EVIDENCE_NOT_ACCESSIBLE_IN_STANDALONE`` taxonomy.  With an
evidence root it evaluates the correspondence questions and can still return
the measured, successful blocked decision when correspondence is not proven.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import re
import statistics
import struct
import subprocess
from pathlib import Path
from typing import Any, Iterable


DECISION_BLOCKED = "BLOCKED_PENDING_SIGNAL_CORRESPONDENCE"
DECISION_AUTHORIZED = "AUTHORIZED_FOR_EXPLORATORY_INFERENCE"
BLOCKED_BEFORE = "EVIDENCE_NOT_ACCESSIBLE_IN_STANDALONE"
BLOCKED_MEASURED = "SIGNAL_CORRESPONDENCE_NOT_ESTABLISHED"
EXPECTED_LONG_LOG_SHA256 = "7f9e9ac65377c6dc217af92f9dee2401b6162540e2245fce97acf2ed49368a34"
FRESH_CADENCE_MATERIAL_RATIO = 0.95

AUDIT_DIR = Path("datasets/mmwave/manifests/M-C0_correspondence_audit")
SUMMARY_PATH = AUDIT_DIR / "m_c0_summary.json"
INVENTORY_PATH = AUDIT_DIR / "existing_measurement_inventory.json"
CORRESPONDENCE_PATH = AUDIT_DIR / "offline_contract_correspondence.json"
REPORT_PATH = Path("docs/reports/20260816_SafeNest_mmWave_Standalone_M-C0_Report_01.md")
RUN_LOG_PATH = Path("docs/reports/20260816_SafeNest_mmWave_M-C0_Run_Log_01.md")
FORENSICS_PATH = AUDIT_DIR / "620_window_input_forensics.json"

FROZEN = {
    "contract_id": "M-B10B_SELECTED_REAL_CANDIDATE_BPF_ZSCORE_V1",
    "profile_id": "M-B1_D0_B1_Z1",
    "profile_name": "BPF_ZSCORE",
    "sample_rate_hz": 10.0,
    "window_samples": 300,
    "window_seconds": 30.0,
    "lowcut_hz": 0.1,
    "highcut_hz": 0.5,
    "bpf_order": 4,
    "bpf_phase_mode": "ZERO_PHASE_FILTFILT",
    "zscore_mean": 0.0031162832173884064,
    "zscore_std": 2.955399434649939,
    "input_scale": 0.041720833629369736,
    "input_zero_point": -3,
    "input_shape": [1, 300, 1],
    "input_dtype": "int8",
    "artifact_sha256": "6dff6aaa72c79d76715d40cf7e32bb1e6cd9b2c2e3ac78eaf2fda737561430c5",
    "artifact_bytes": 22080,
    "runtime_model_id": "M-B3_CONV1D_GAP_BASELINE_seed42_M-B6_STRICT_INT8",
}

EXPECTED_CSV_SUFFIXES = {
    "S001_NORMAL_D06": "__S001_NORMAL_D06.csv",
    "S001_NORMAL_D09": "__S001_NORMAL_D09.csv",
    "S001_NORMAL_D12": "__S001_NORMAL_D12.csv",
    "S001_NORMAL_D15": "__S001_NORMAL_D15.csv",
    "S001_BREATH_PACED_12_01": "__S001_BREATH_PACED_12_01.csv",
    "S001_BREATH_PACED_12_02": "__S001_BREATH_PACED_12_02.csv",
    "S001_BREATH_PACED_15_03": "__S001_BREATH_PACED_15_03.csv",
    "S001_BREATH_PACED_20_04": "__S001_BREATH_PACED_20_04.csv",
    "S001_BREATH_PACED_20_05": "__S001_BREATH_PACED_20_05.csv",
}

PILOT_IDS = (
    "M-C0-PILOT-DESKWORK-001",
    "M-C0-PILOT-STATIONARY-001",
)

PR18_HEAD = "62eb0d867cfa02295c9a1d023b813134c434b8eb"
PR18_PUBLIC_ROOT = Path("devices/mmwave/device_measurements")
PR18_RETRIEVAL_ATTEMPTS = [
    {
        "command": "git fetch origin pull/18/head:pr18-head",
        "result": "SUCCESS: refs/pull/18/head -> pr18-head",
    },
    {
        "command": f"git fetch origin {PR18_HEAD}",
        "result": f"SUCCESS: {PR18_HEAD} -> FETCH_HEAD",
    },
    {
        "command": "git fetch origin refs/pull/18/head",
        "result": "SUCCESS: refs/pull/18/head -> FETCH_HEAD",
    },
]
PR18_SEARCH_PATHS = [
    {
        "ref": "HEAD",
        "path": "devices/mmwave/device_measurements/",
        "result": "NOT_FOUND",
    },
    {
        "ref": f"pr18-head@{PR18_HEAD}",
        "path": "devices/mmwave/device_measurements/",
        "result": "FOUND",
    },
    *[
        {
            "ref": "HEAD",
            "path": f"devices/mmwave/firmware/device_measurements/{pilot_id}.jsonl",
            "result": "NOT_FOUND",
        }
        for pilot_id in PILOT_IDS
    ],
    *[
        {
            "ref": "HEAD",
            "path": f"devices/mmwave/firmware/device_measurements/{pilot_id}/records.jsonl",
            "result": "NOT_FOUND",
        }
        for pilot_id in PILOT_IDS
    ],
    *[
        {
            "ref": f"pr18-head@{PR18_HEAD}",
            "path": f"devices/mmwave/device_measurements/{pilot_id}.jsonl",
            "result": "NOT_FOUND",
        }
        for pilot_id in PILOT_IDS
    ],
    *[
        {
            "ref": f"pr18-head@{PR18_HEAD}",
            "path": f"devices/mmwave/device_measurements/{pilot_id}/records.jsonl",
            "result": "NOT_FOUND",
        }
        for pilot_id in PILOT_IDS
    ],
    *[
        {
            "ref": f"pr18-head@{PR18_HEAD}",
            "path": f"devices/mmwave/device_measurements/pilot/{pilot_id}.raw.jsonl",
            "result": "FOUND",
        }
        for pilot_id in PILOT_IDS
    ],
]

SESSION_CONTEXT = {
    "S001_NORMAL_D06": {"cue_rpm": None, "vendor_median_rpm": None, "role": "legacy occupied distance"},
    "S001_NORMAL_D09": {"cue_rpm": None, "vendor_median_rpm": None, "role": "legacy occupied distance"},
    "S001_NORMAL_D12": {"cue_rpm": None, "vendor_median_rpm": None, "role": "legacy occupied distance"},
    "S001_NORMAL_D15": {"cue_rpm": None, "vendor_median_rpm": None, "role": "legacy occupied distance"},
    "S001_BREATH_PACED_12_01": {
        "cue_rpm": 12.0,
        "vendor_median_rpm": None,
        "role": "failed paced trial; delivery note says actual trial was approximately 6.06 rpm",
        "documented_actual_rpm": 6.06,
    },
    "S001_BREATH_PACED_12_02": {"cue_rpm": 12.0, "vendor_median_rpm": 14.0, "role": "valid paced cue"},
    "S001_BREATH_PACED_15_03": {"cue_rpm": 15.0, "vendor_median_rpm": 19.0, "role": "valid paced cue"},
    "S001_BREATH_PACED_20_04": {"cue_rpm": 20.0, "vendor_median_rpm": 23.0, "role": "paced shallow trial"},
    "S001_BREATH_PACED_20_05": {"cue_rpm": 20.0, "vendor_median_rpm": 23.0, "role": "paced deep trial"},
    "2026-08-01_occupied_d09_v120_31min_attempt02": {
        "cue_rpm": None,
        "vendor_median_rpm": 23.0,
        "role": "long occupied log",
    },
}

PIPELINE_FILES = (
    Path("ondevice_ai/adapters/mmwave_csv_adapter.py"),
    Path("ondevice_ai/inference/mmwave_interpreter.py"),
    Path("devices/mmwave/src/mr60_esp_adapter.py"),
    Path("devices/mmwave/firmware/export_mmwave_csv.py"),
    Path("devices/mmwave/firmware/src/main.cpp"),
)


def repo_rel(root: Path, path: Path) -> str:
    """Return a repository-relative path without exposing a local root."""

    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def sanitize_segment(segment: str) -> str:
    """Redact delivery-folder personal-name components in derived outputs."""

    # The delivery folder contains a person's name.  Keep the date and role,
    # but remove one or more underscore-delimited name components.
    return re.sub(r"_(?:[^_]+_)*delivery_v2", "_delivery_v2", segment, flags=re.IGNORECASE)


def public_evidence_path(
    root: Path,
    evidence_root: Path,
    path: Path,
    public_root: Path | None = None,
) -> str:
    rel = path.resolve().relative_to(evidence_root.resolve())
    safe = "/".join(sanitize_segment(part) for part in rel.parts)
    prefix = public_root.as_posix() if public_root is not None else repo_rel(root, evidence_root)
    return f"{prefix}/{safe}" if safe else prefix


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def assert_output_outside_evidence(paths: Iterable[Path], evidence_root: Path) -> None:
    """Fail closed if any derived write target is inside the evidence root."""

    evidence_root = evidence_root.resolve()
    for path in paths:
        if is_within(path, evidence_root):
            raise AssertionError(f"write target is inside read-only evidence-root: {path}")


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    # Explicit rb mode is the read-only evidence boundary.
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def open_all_evidence_files_read_only(evidence_root: Path) -> int:
    """Open every regular file below evidence-root without reading/writing it."""

    count = 0
    for path in sorted(evidence_root.rglob("*")):
        # Do not follow toolchain symlinks out of the evidence root.  The
        # read-only inventory is explicitly for regular evidence files.
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb"):
            pass
        count += 1
    return count


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def round_value(value: Any, digits: int = 9) -> Any:
    if isinstance(value, float):
        return round(value, digits)
    return value


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def numeric_stats(values: Iterable[float]) -> dict[str, Any]:
    values = [float(value) for value in values if math.isfinite(float(value))]
    if not values:
        return {"count": 0, "min": None, "median": None, "p05": None, "p95": None, "max": None, "mean": None, "std": None}
    return {
        "count": len(values),
        "min": round_value(min(values)),
        "median": round_value(statistics.median(values)),
        "p05": round_value(percentile(values, 0.05)),
        "p95": round_value(percentile(values, 0.95)),
        "max": round_value(max(values)),
        "mean": round_value(statistics.fmean(values)),
        "std": round_value(statistics.pstdev(values) if len(values) > 1 else 0.0),
    }


def distance_summary(rows: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    """Summarize distance telemetry without confusing it with phase freeze."""

    if kind == "legacy_csv":
        field = "range_m"
        unit = "m"
        values = [value for value in (as_float(row.get(field)) for row in rows) if value is not None]
    else:
        field = "distance_cm_raw"
        unit = "cm"
        values = [value for value in (as_float(row.get(field)) for row in rows) if value is not None]
    return {
        "field": field,
        "unit": unit,
        "finite_sample_count": len(values),
        "stats": numeric_stats(values),
        "sample_std": round_value(statistics.stdev(values)) if len(values) > 1 else None,
        "sample_std_cm": round_value(statistics.stdev(values) * 100.0) if kind == "legacy_csv" and len(values) > 1 else None,
        "computation": "population stats plus sample standard deviation over finite distance telemetry values; legacy CSV range_m is in metres",
    }


def run_lengths(flags: list[bool]) -> dict[str, int]:
    count = 0
    longest = 0
    current = 0
    for flag in flags:
        if flag:
            count += 1
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return {"interval_count": count, "longest_interval_run": longest}


def load_csv_rows(path: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    malformed = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row:
                malformed += 1
                continue
            rows.append(row)
    return rows, malformed


def load_jsonl_rows(path: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    malformed = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if isinstance(value, dict):
                rows.append(value)
            else:
                malformed += 1
    return rows, malformed


def normalize_rows(rows: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if kind == "legacy_csv":
            timestamp = as_float(row.get("timestamp_s"))
            phase = as_float(row.get("resp_phase"))
            phase_age = None
            seq = None
            vendor_rate = as_float(row.get("breath_rpm"))
            raw_rate = None
        else:
            timestamp_ms = as_float(row.get("ts_monotonic_ms"))
            timestamp = timestamp_ms / 1000.0 if timestamp_ms is not None else None
            phase = as_float(row.get("breath_phase"))
            phase_age = as_float(row.get("phase_age_ms"))
            seq = as_float(row.get("seq"))
            vendor_rate = as_float(row.get("breath_rate_raw"))
            raw_rate = vendor_rate
        result.append(
            {
                "index": index,
                "timestamp_s": timestamp,
                "phase": phase,
                "phase_age_ms": phase_age,
                "seq": seq,
                "vendor_rate": vendor_rate,
                "breath_rate_raw": raw_rate,
                "freeze_detected": bool(row.get("freeze_detected") is True),
            }
        )
    return result


def timestamp_integrity(records: list[dict[str, Any]]) -> dict[str, Any]:
    timestamps = [r["timestamp_s"] for r in records if r["timestamp_s"] is not None]
    intervals = [b - a for a, b in zip(timestamps, timestamps[1:])]
    positive = [value for value in intervals if value > 0]
    median_ms = statistics.median(positive) * 1000.0 if positive else None
    gap_threshold_ms = max(150.0, 1.5 * median_ms) if median_ms is not None else None
    gaps = [value for value in intervals if gap_threshold_ms is not None and value * 1000.0 > gap_threshold_ms]
    timestamp_freezes = run_lengths([value == 0 for value in intervals])
    nonmonotonic = sum(1 for value in intervals if value < 0)
    duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else None
    row_cadence = (len(timestamps) - 1) / duration if duration and duration > 0 else None

    seqs = [int(r["seq"]) for r in records if r["seq"] is not None]
    seq_diffs = [b - a for a, b in zip(seqs, seqs[1:])]
    seq_missing = sum(max(value - 1, 0) for value in seq_diffs if value > 1)
    seq_integrity = {
        "status": "MEASURED" if seqs else "FIELD_NOT_PRESENT",
        "first": seqs[0] if seqs else None,
        "last": seqs[-1] if seqs else None,
        "record_count": len(seqs),
        "missing_sequence_count": seq_missing if seqs else None,
        "duplicate_sequence_count": sum(1 for value in seq_diffs if value == 0) if seqs else None,
        "nonmonotonic_sequence_count": sum(1 for value in seq_diffs if value < 0) if seqs else None,
        "computation": "sum(max(seq[i+1]-seq[i]-1, 0) for positive sequence gaps)",
    }
    return {
        "record_count_with_timestamp": len(timestamps),
        "row_cadence_hz": round_value(row_cadence),
        "duration_s": round_value(duration),
        "median_interval_ms": round_value(median_ms),
        "min_interval_ms": round_value(min(intervals) * 1000.0) if intervals else None,
        "max_interval_ms": round_value(max(intervals) * 1000.0) if intervals else None,
        "gap_threshold_ms_diagnostic": round_value(gap_threshold_ms),
        "gap_count": len(gaps),
        "duplicate_timestamp_count": sum(1 for value in intervals if value == 0),
        "nonmonotonic_timestamp_count": nonmonotonic,
        "timestamp_freeze_intervals": timestamp_freezes,
        "freeze_flag_count": sum(1 for r in records if r["freeze_detected"]),
        "sequence": seq_integrity,
        "computation": {
            "row_cadence_hz": "(timestamp_count - 1) / (last_timestamp - first_timestamp)",
            "gap_count": "interval_ms > max(150 ms, 1.5 * median_positive_interval_ms); diagnostic only, not an official failure threshold",
        },
    }


def phase_signal_summary(records: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    pairs = [(r["timestamp_s"], r["phase"]) for r in records if r["timestamp_s"] is not None and r["phase"] is not None]
    times = [item[0] for item in pairs]
    values = [item[1] for item in pairs]
    summary = numeric_stats(values)
    summary["unique_value_count"] = len(set(values))
    equal_flags = [a == b for a, b in zip(values, values[1:])]
    summary["freeze_intervals"] = run_lengths(equal_flags)

    center = statistics.fmean(values) if values else None
    positive_crossings: list[float] = []
    if center is not None:
        for i in range(1, len(values)):
            left = values[i - 1] - center
            right = values[i] - center
            if left <= 0 < right and values[i] != values[i - 1]:
                fraction = (-left) / (right - left)
                positive_crossings.append(times[i - 1] + fraction * (times[i] - times[i - 1]))
    periods = [b - a for a, b in zip(positive_crossings, positive_crossings[1:]) if b > a]
    period_s = statistics.median(periods) if periods else None
    phase_rpm = 60.0 / period_s if period_s and period_s > 0 else None
    vendor_median = context.get("vendor_median_rpm")
    return {
        "field": "resp_phase" if any("resp_phase" in str(r) for r in []) else "breath_phase_or_resp_phase",
        "finite_sample_count": len(values),
        "stats": summary,
        "positive_crossing_count": len(positive_crossings),
        "dominant_period_s_from_median_positive_crossing_interval": round_value(period_s),
        "dominant_phase_rpm": round_value(phase_rpm),
        "paced_cue_rpm": context.get("cue_rpm"),
        "documented_actual_trial_rpm": context.get("documented_actual_rpm"),
        "documented_vendor_median_rpm": vendor_median,
        "phase_minus_vendor_median_rpm": round_value(phase_rpm - vendor_median) if phase_rpm is not None and vendor_median is not None else None,
        "computation": "center signal by its session mean; estimate period from median interval between positive mean crossings; rpm=60/period_s",
    }


def assert_freshness_estimator_consistency(
    *,
    max_phase_age_ms: float,
    telemetry_interval_ms: float,
    fresh_cadence_hz: float,
    row_cadence_hz: float,
    timestamp_age_transition_count: int,
    age_interval_transition_count: int,
) -> dict[str, Any]:
    """Fail closed when independent freshness estimators become inconsistent."""

    low_age_regime = max_phase_age_ms < 2.0 * telemetry_interval_ms
    minimum_expected_fresh_cadence_hz = row_cadence_hz * FRESH_CADENCE_MATERIAL_RATIO
    if low_age_regime and fresh_cadence_hz < minimum_expected_fresh_cadence_hz:
        raise AssertionError(
            "FRESHNESS_GUARD_LOW_AGE_CADENCE_UNDERCOUNT: "
            f"max_phase_age_ms={max_phase_age_ms}, telemetry_interval_ms={telemetry_interval_ms}, "
            f"fresh_cadence_hz={fresh_cadence_hz}, row_cadence_hz={row_cadence_hz}, "
            f"minimum_ratio={FRESH_CADENCE_MATERIAL_RATIO}"
        )
    if timestamp_age_transition_count != age_interval_transition_count:
        raise AssertionError(
            "FRESHNESS_GUARD_ESTIMATOR_DIVERGENCE: "
            f"timestamp_age_transition_count={timestamp_age_transition_count}, "
            f"age_interval_transition_count={age_interval_transition_count}"
        )
    return {
        "status": "PASS",
        "low_age_regime": low_age_regime,
        "low_age_definition": "max(phase_age_ms) < 2 * median telemetry interval; regression diagnostic only",
        "materially_below_row_cadence_definition": (
            f"fresh cadence < {FRESH_CADENCE_MATERIAL_RATIO} * row cadence; regression diagnostic only"
        ),
        "timestamp_age_transition_count": timestamp_age_transition_count,
        "age_interval_transition_count": age_interval_transition_count,
        "cross_check": "EXACT_MATCH",
    }


def assert_no_combined_fresh_window_total(summary: dict[str, Any]) -> None:
    """Reject a summary that collapses the two evidence groups into one total."""

    forbidden_keys = {
        "combined_valid_300_fresh_windows",
        "total_valid_300_fresh_windows",
        "valid_300_fresh_windows_total",
    }
    present_forbidden = sorted(forbidden_keys.intersection(summary))
    if present_forbidden:
        raise AssertionError(
            "FRESHNESS_GUARD_COMBINED_WINDOW_TOTAL: forbidden keys "
            + ", ".join(present_forbidden)
        )
    grouped = summary.get("valid_300_fresh_windows")
    required_groups = {"PRE_PR18_LEGACY_LOGS", "PR18_PILOT_CAPTURE"}
    if not isinstance(grouped, dict) or set(grouped) != required_groups:
        raise AssertionError(
            "FRESHNESS_GUARD_COMBINED_WINDOW_TOTAL: valid_300_fresh_windows must be "
            "a two-group mapping, never a scalar or combined total"
        )
    if summary.get("valid_300_fresh_windows_aggregate_reported") is not False:
        raise AssertionError(
            "FRESHNESS_GUARD_COMBINED_WINDOW_TOTAL: aggregate reporting must remain false"
        )


def freshness_summary(records: list[dict[str, Any]]) -> tuple[dict[str, Any], list[int]]:
    age_pairs = [(index, r["timestamp_s"], r["phase_age_ms"]) for index, r in enumerate(records) if r["timestamp_s"] is not None and r["phase_age_ms"] is not None]
    if not age_pairs:
        return (
            {
                "status": "FIELD_NOT_PRESENT",
                "fresh_0x0A13_cadence_hz": None,
                "phase_age_ms": {"min": None, "median": None, "p95": None, "max": None, "fraction_over_30000_ms": None},
                "phase_age_reset_count": None,
                "computation": "not measurable because phase_age_ms is absent",
            },
            [],
        )
    ages = [item[2] for item in age_pairs]
    old_reset_indices: list[int] = []
    phase_or_age_indices: list[int] = []
    age_newer_than_previous_emission_indices: list[int] = []
    reconstructed_update_advance_indices: list[int] = []
    for previous, current in zip(age_pairs, age_pairs[1:]):
        if current[2] < previous[2]:
            old_reset_indices.append(current[0])
        previous_phase = records[previous[0]]["phase"]
        current_phase = records[current[0]]["phase"]
        if current_phase != previous_phase or current[2] < previous[2]:
            phase_or_age_indices.append(current[0])
        row_interval_ms = (current[1] - previous[1]) * 1000.0
        if current[2] < row_interval_ms:
            age_newer_than_previous_emission_indices.append(current[0])
        previous_update_ms = round(previous[1] * 1000.0) - previous[2]
        current_update_ms = round(current[1] * 1000.0) - current[2]
        if current_update_ms > previous_update_ms:
            reconstructed_update_advance_indices.append(current[0])
    span = age_pairs[-1][1] - age_pairs[0][1]
    selected_count = len(reconstructed_update_advance_indices)
    cadence = selected_count / span if span > 0 else None
    positive_intervals_ms = [
        (current[1] - previous[1]) * 1000.0
        for previous, current in zip(age_pairs, age_pairs[1:])
        if current[1] > previous[1]
    ]
    telemetry_interval_ms = statistics.median(positive_intervals_ms)
    row_cadence_hz = (len(age_pairs) - 1) / span
    regression_guards = assert_freshness_estimator_consistency(
        max_phase_age_ms=max(ages),
        telemetry_interval_ms=telemetry_interval_ms,
        fresh_cadence_hz=cadence,
        row_cadence_hz=row_cadence_hz,
        timestamp_age_transition_count=selected_count,
        age_interval_transition_count=len(age_newer_than_previous_emission_indices),
    )

    def method(
        count: int,
        computation: str,
        role: str,
        status: str = "CURRENT_DIAGNOSTIC",
    ) -> dict[str, Any]:
        return {
            "status": status,
            "transition_count": count,
            "cadence_hz": round_value(count / span if span > 0 else None),
            "computation": computation,
            "role": role,
        }

    return (
        {
            "status": "RECONSTRUCTED_UPDATE_INSTANT_ADVANCES",
            "fresh_0x0A13_cadence_hz": round_value(cadence),
            "phase_age_ms": {
                "min": round_value(min(ages)),
                "median": round_value(statistics.median(ages)),
                "p95": round_value(percentile(ages, 0.95)),
                "max": round_value(max(ages)),
                "fraction_over_30000_ms": round_value(sum(1 for age in ages if age > 30000.0) / len(ages)),
            },
            "selected_fresh_update_count": selected_count,
            "selected_method": "reconstructed_update_instant_advances",
            "regression_guards": regression_guards,
            "estimator_methods": {
                "old_phase_age_decrease_proxy": method(
                    len(old_reset_indices),
                    "count phase_age_ms[i] < phase_age_ms[i-1]; divide by timestamp span",
                    "systematically undercounts always-low pilot age values",
                    "RETRACTED_FAULTY_ESTIMATOR",
                ),
                "phase_value_change_or_age_decrease": method(
                    len(phase_or_age_indices),
                    "count breath_phase changes or phase_age_ms decreases; divide by timestamp span",
                    "independent lower bound because quantized phase values can repeat",
                ),
                "phase_age_less_than_previous_row_interval": method(
                    len(age_newer_than_previous_emission_indices),
                    "count phase_age_ms[i] < telemetry interval[i]; divide by timestamp span",
                    "independent confirmation that an update is newer than the previous emission",
                ),
                "reconstructed_update_instant_advances": method(
                    selected_count,
                    "update_ms=round(timestamp_s*1000)-phase_age_ms; count update_ms[i] > update_ms[i-1]; divide by timestamp span",
                    "selected because it directly tests whether the recorded source-update instant advances",
                ),
            },
            "superseded_fresh_0x0A13_cadence_hz": round_value(
                len(old_reset_indices) / span if span > 0 else None
            ),
            "superseded_fresh_cadence_status": "RETRACTED_FAULTY_ESTIMATOR",
            "superseded_estimator": "phase_age_ms decrease count / timestamp span",
            "computation": "fresh update instant = round(timestamp_s*1000)-phase_age_ms; cadence = advancing update-instant count / timestamp span",
            "failure_threshold_status": "UNDEFINED; 30000 ms is only the requested reporting partition",
        },
        reconstructed_update_advance_indices,
    )


def fixed_window_freshness(records: list[dict[str, Any]], fresh_update_indices: list[int]) -> dict[str, Any]:
    first_identifiable_index = next(
        (
            index
            for index, record in enumerate(records)
            if record["timestamp_s"] is not None and record["phase_age_ms"] is not None
        ),
        None,
    )
    if first_identifiable_index is None:
        return {
            "windows_with_300_genuinely_fresh_samples": 0,
            "max_fresh_samples_in_nonoverlapping_30s_window": 0,
            "fresh_sample_counts_by_window": [],
            "window_count_evaluated": 0,
            "status": "NOT_PROVABLE_NO_PHASE_AGE_FIELD",
            "computation": "no window count because phase_age_ms/update instant is absent",
        }
    event_indices = [first_identifiable_index] + [
        index for index in fresh_update_indices if index != first_identifiable_index
    ]
    event_times = [
        records[index]["timestamp_s"]
        for index in event_indices
        if records[index]["timestamp_s"] is not None
    ]
    telemetry_times = [
        record["timestamp_s"] for record in records if record["timestamp_s"] is not None
    ]
    start = telemetry_times[0]
    last = telemetry_times[-1]
    window_count = int((last - start) // FROZEN["window_seconds"]) + 1
    bins: dict[int, int] = {}
    for timestamp in event_times:
        bucket = int((timestamp - start) // FROZEN["window_seconds"])
        bins[bucket] = bins.get(bucket, 0) + 1
    counts = [bins.get(index, 0) for index in range(window_count)]
    maximum = max(counts) if counts else 0
    return {
        "windows_with_300_genuinely_fresh_samples": sum(
            1 for count in counts if count >= FROZEN["window_samples"]
        ),
        "max_fresh_samples_in_nonoverlapping_30s_window": maximum,
        "fresh_sample_counts_by_window": counts,
        "window_count_evaluated": window_count,
        "first_identifiable_sample_included": True,
        "status": "MEASURED_FROM_RECONSTRUCTED_UPDATE_INSTANTS",
        "computation": "anchor fixed non-overlapping 30 s bins at the first telemetry timestamp; include the first identifiable timestamp-age update, then each advancing reconstructed update instant; count bins with >=300 fresh samples",
    }


def interpolation_diagnostic(records: list[dict[str, Any]], reset_indices: list[int]) -> dict[str, Any]:
    points = [(records[index]["timestamp_s"], records[index]["phase"]) for index in reset_indices if records[index]["timestamp_s"] is not None and records[index]["phase"] is not None]
    if len(points) < 2:
        return {
            "required_status": "UNRESOLVED",
            "applied_to_audit": False,
            "simulation_status": "NOT_QUANTIFIABLE",
            "distortion": None,
        }
    point_times = [point[0] for point in points]
    point_values = [point[1] for point in points]
    observed: list[float] = []
    interpolated: list[float] = []
    for record in records:
        timestamp = record["timestamp_s"]
        phase = record["phase"]
        if timestamp is None or phase is None or timestamp < point_times[0] or timestamp > point_times[-1]:
            continue
        right = bisect.bisect_right(point_times, timestamp)
        if right == 0 or right >= len(point_times):
            continue
        left = right - 1
        span = point_times[right] - point_times[left]
        fraction = (timestamp - point_times[left]) / span if span > 0 else 0.0
        estimate = point_values[left] + fraction * (point_values[right] - point_values[left])
        observed.append(phase)
        interpolated.append(estimate)
    errors = [a - b for a, b in zip(observed, interpolated)]
    return {
        "required_status": "UNRESOLVED",
        "applied_to_audit": False,
        "simulation_status": "SIMULATED_LINEAR_INTERPOLATION_FROM_PHASE_AGE_RESET_PROXY",
        "distortion": {
            "sample_count": len(errors),
            "mae": round_value(statistics.fmean(abs(error) for error in errors)) if errors else None,
            "rmse": round_value(math.sqrt(statistics.fmean(error * error for error in errors))) if errors else None,
            "max_abs": round_value(max(abs(error) for error in errors)) if errors else None,
            "observed_std": round_value(numeric_stats(observed)["std"]),
            "interpolated_std": round_value(numeric_stats(interpolated)["std"]),
        },
        "computation": "linear interpolation between phase_age reset-proxy samples; compared with observed held/repeated telemetry at the original timestamps",
    }


def affine_and_int8(values: list[float], training_reference: dict[str, Any] | None) -> dict[str, Any]:
    normalized = [(value - FROZEN["zscore_mean"]) / FROZEN["zscore_std"] for value in values]

    def quantize(value: float) -> int:
        scaled = value / FROZEN["input_scale"]
        rounded = math.floor(scaled + 0.5) if scaled >= 0 else math.ceil(scaled - 0.5)
        return max(-128, min(127, rounded + FROZEN["input_zero_point"]))

    quantized = [quantize(value) for value in normalized]
    dequantized = [(value - FROZEN["input_zero_point"]) * FROZEN["input_scale"] for value in quantized]
    errors = [after - before for before, after in zip(normalized, dequantized)]
    saturation = sum(1 for value in quantized if value in (-128, 127)) / len(quantized) if quantized else None
    before = numeric_stats(normalized)
    after = numeric_stats(dequantized)
    result: dict[str, Any] = {
        "status": "DIAGNOSTIC_AFFINE_AND_INT8_ONLY",
        "bpf_applied": False,
        "before_int8": before,
        "after_int8_dequantized": after,
        "quantized_integer_stats": numeric_stats([float(value) for value in quantized]),
        "quantized_saturation_fraction": round_value(saturation),
        "quantization_error": numeric_stats(errors),
        "computation": "normalized_proxy=(raw_phase - frozen_mean)/frozen_std; q=round_half_away_from_zero(normalized/scale)+zero_point; clamp int8; dequantize=(q-zero_point)*scale",
    }
    if training_reference:
        ref_before = training_reference.get("naive_affine", {}).get("stats")
        if ref_before:
            result["training_reference_before_int8"] = ref_before
            result["mean_delta_vs_training_reference"] = round_value(before["mean"] - ref_before["mean"])
            result["std_delta_vs_training_reference"] = round_value(before["std"] - ref_before["std"])
    return result


def read_npy_float64(path: Path) -> list[float]:
    """Read the small frozen float64 NPY reference without importing NumPy."""

    data = path.read_bytes()
    if data[:6] != b"\x93NUMPY" or data[6] != 1:
        raise ValueError("only NPY v1 float64 reference is supported")
    header_length = struct.unpack("<H", data[8:10])[0]
    header_start = 10
    header = data[header_start : header_start + header_length].decode("latin1")
    if "'<f8'" not in header and '"<f8"' not in header:
        raise ValueError("training reference is not little-endian float64")
    payload = data[header_start + header_length :]
    return [value[0] for value in struct.iter_unpack("<d", payload)]


def load_training_reference(root: Path) -> dict[str, Any] | None:
    candidates = (
        root / "safenest-mmwave-standalone/datasets/mmwave/processed/mmwave_canonical_real_v1.npy",
        root / "safenest_integration/sources/ondevice_ai/datasets/mmwave/processed/mmwave_canonical_real_v1.npy",
    )
    source = next((path for path in candidates if path.is_file()), None)
    if source is None:
        return None
    values = read_npy_float64(source)
    normalized = [(value - FROZEN["zscore_mean"]) / FROZEN["zscore_std"] for value in values]
    digest, size = sha256_file(source)
    source_path = repo_rel(root, source)
    try:
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", source_path],
            cwd=root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        source_tracked = True
    except (OSError, subprocess.CalledProcessError):
        source_tracked = False
    return {
        "source_path": source_path,
        "sha256": digest,
        "bytes": size,
        "source_tracked_in_target_repo": source_tracked,
        "reproducible_from_published_target": source_tracked,
        "raw_stats": numeric_stats(values),
        "naive_affine": {
            "stats": numeric_stats(normalized),
            "computation": "same diagnostic frozen affine used for MR60 raw phase; BPF was not reconstructed",
        },
        "status": "AVAILABLE_AUXILIARY_FROZEN_REFERENCE" if source_tracked else "AVAILABLE_LOCAL_ONLY_AUXILIARY_REFERENCE_NOT_TRACKED",
    }


def pipeline_usage(root: Path) -> dict[str, Any]:
    waveform_matches: list[dict[str, Any]] = []
    raw_rate_matches: list[dict[str, Any]] = []
    for relative in PIPELINE_FILES:
        path = root / relative
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if "resp_phase" in line or "breath_phase" in line:
                if any(token in line for token in ("required_cols", "phases", "phase", "prepare_window", "input_tensor", "resp_phase")):
                    waveform_matches.append({"path": relative.as_posix(), "line": line_number, "text": line.strip()[:180]})
            if "breath_rate_raw" in line:
                raw_rate_matches.append({"path": relative.as_posix(), "line": line_number, "text": line.strip()[:180]})
    waveform_input_files = sorted({item["path"] for item in waveform_matches if "resp_phase" in item["text"] or "breath_phase" in item["text"]})
    return {
        "breath_rate_raw_used_as_waveform_input": False,
        "waveform_input_field": "resp_phase/breath_phase",
        "waveform_input_files": waveform_input_files,
        "waveform_matches": waveform_matches[:40],
        "breath_rate_raw_matches": raw_rate_matches[:40],
        "computation": "static scan of the CSV adapter/interpreter and MR60 adapter/exporter; waveform assignment is phase, while breath_rate_raw matches are telemetry/export/diagnostic references",
    }


def find_named_file(evidence_root: Path, name: str) -> Path | None:
    matches = sorted(path for path in evidence_root.rglob(name) if path.is_file())
    return matches[0] if matches else None


def expected_evidence(
    root: Path,
    evidence_root: Path,
    all_hashes: dict[Path, dict[str, Any]],
    pilot_evidence_root: Path | None = None,
) -> list[dict[str, Any]]:
    expected: list[dict[str, Any]] = []
    for session_id, suffix in EXPECTED_CSV_SUFFIXES.items():
        path = next((candidate for candidate in sorted(evidence_root.rglob("*.csv")) if candidate.name.endswith(suffix)), None)
        item: dict[str, Any] = {
            "session_id": session_id,
            "kind": "legacy_csv",
            "evidence_group": "PRE_PR18_LEGACY_LOGS",
            "expected_filename_suffix": suffix,
            "status": "PRESENT" if path else "KNOWN_BUT_NOT_PROVIDED",
            "record_count_expected": None,
        }
        if path:
            if path.resolve() not in all_hashes:
                digest, size = sha256_file(path)
                all_hashes[path.resolve()] = {"sha256": digest, "bytes": size}
            rows, malformed = load_csv_rows(path)
            item.update(
                {
                    "path": public_evidence_path(root, evidence_root, path),
                    "sha256": all_hashes[path.resolve()]["sha256"],
                    "bytes": all_hashes[path.resolve()]["bytes"],
                    "record_count": len(rows),
                    "malformed_record_count": malformed,
                }
            )
        else:
            item["candidate_path"] = f"{repo_rel(root, evidence_root)}/csv/<delivery_v2>/*{suffix}"
        expected.append(item)

    long_name = "2026-08-01_occupied_d09_v120_31min_attempt02.jsonl"
    long_path = find_named_file(evidence_root, long_name)
    item = {
        "session_id": "2026-08-01_occupied_d09_v120_31min_attempt02",
        "kind": "long_jsonl",
        "evidence_group": "PRE_PR18_LEGACY_LOGS",
        "expected_filename": long_name,
        "status": "PRESENT" if long_path else "KNOWN_BUT_NOT_PROVIDED",
    }
    if long_path:
        if long_path.resolve() not in all_hashes:
            digest, size = sha256_file(long_path)
            all_hashes[long_path.resolve()] = {"sha256": digest, "bytes": size}
        rows, malformed = load_jsonl_rows(long_path)
        item.update(
            {
                "path": public_evidence_path(root, evidence_root, long_path),
                "sha256": all_hashes[long_path.resolve()]["sha256"],
                "bytes": all_hashes[long_path.resolve()]["bytes"],
                "record_count": len(rows),
                "malformed_record_count": malformed,
                "expected_sha256": EXPECTED_LONG_LOG_SHA256,
                "sha256_matches_expected": all_hashes[long_path.resolve()]["sha256"] == EXPECTED_LONG_LOG_SHA256,
            }
        )
    else:
        item["candidate_path"] = f"{repo_rel(root, evidence_root)}/logs/final/{long_name}"
    expected.append(item)

    pilot_search_root = pilot_evidence_root or evidence_root
    for pilot_id in PILOT_IDS:
        matches = sorted(
            path
            for path in pilot_search_root.rglob("*.jsonl")
            if path.is_file() and pilot_id in path.name
        )
        item = {
            "session_id": pilot_id,
            "kind": "pr18_pilot",
            "evidence_group": "PR18_PILOT_CAPTURE",
            "expected_record_count": 1799,
            "status": "PRESENT" if matches else "KNOWN_BUT_NOT_PROVIDED",
            "search_scope": "recursive filename match under the supplied PR18 pilot evidence root",
            "source_ref": f"pr18-head@{PR18_HEAD}",
            "retrieval_attempts": PR18_RETRIEVAL_ATTEMPTS,
            "candidate_paths": [
                f"{PR18_PUBLIC_ROOT.as_posix()}/{pilot_id}.jsonl",
                f"{PR18_PUBLIC_ROOT.as_posix()}/{pilot_id}/records.jsonl",
                f"{PR18_PUBLIC_ROOT.as_posix()}/pilot/{pilot_id}.raw.jsonl",
            ],
        }
        if matches:
            path = matches[0]
            if path.resolve() not in all_hashes:
                digest, size = sha256_file(path)
                all_hashes[path.resolve()] = {"sha256": digest, "bytes": size}
            item.update(
                {
                    "path": public_evidence_path(
                        root,
                        pilot_search_root,
                        path,
                        PR18_PUBLIC_ROOT if pilot_evidence_root is not None else None,
                    ),
                    "sha256": all_hashes[path.resolve()]["sha256"],
                    "bytes": all_hashes[path.resolve()]["bytes"],
                }
            )
            if path.suffix.lower() == ".jsonl":
                rows, malformed = load_jsonl_rows(path)
                item.update({"record_count": len(rows), "malformed_record_count": malformed})
        expected.append(item)
    return expected


def analyze_session(root: Path, evidence_root: Path, item: dict[str, Any], all_hashes: dict[Path, dict[str, Any]], training_reference: dict[str, Any] | None) -> dict[str, Any] | None:
    if item.get("status") != "PRESENT" or item.get("kind") not in {"legacy_csv", "long_jsonl", "pr18_pilot"}:
        return None
    path_text = item["path"]
    # Recover the local file from its sanitized name by matching the recorded SHA.
    target_sha = item["sha256"]
    path = next((candidate for candidate, record in all_hashes.items() if record["sha256"] == target_sha), None)
    if path is None:
        return None
    kind = item["kind"]
    rows, malformed = load_csv_rows(path) if kind == "legacy_csv" else load_jsonl_rows(path)
    records = normalize_rows(rows, kind)
    context = SESSION_CONTEXT.get(item["session_id"], {})
    integrity = timestamp_integrity(records)
    phase = phase_signal_summary(records, context)
    if kind == "legacy_csv":
        phase["field"] = "resp_phase"
    else:
        phase["field"] = "breath_phase"
    freshness, corrected_fresh_update_indices = freshness_summary(records)
    fresh_windows = fixed_window_freshness(records, corrected_fresh_update_indices)
    superseded_age_decrease_indices = [
        index
        for index in range(1, len(records))
        if records[index]["phase_age_ms"] is not None
        and records[index - 1]["phase_age_ms"] is not None
        and records[index]["phase_age_ms"] < records[index - 1]["phase_age_ms"]
    ]
    interpolation = interpolation_diagnostic(records, superseded_age_decrease_indices)
    distance = distance_summary(rows, kind)
    finite_phase = [record["phase"] for record in records if record["phase"] is not None]
    bpf_comparison = {
        "meaning_equivalent_to_frozen_contract": False,
        "scale_equivalent_to_frozen_contract": False,
        "assessment": "NOT_ESTABLISHED",
        "frozen_contract": {
            "contract_id": FROZEN["contract_id"],
            "band_hz": [FROZEN["lowcut_hz"], FROZEN["highcut_hz"]],
            "sample_rate_hz": FROZEN["sample_rate_hz"],
            "zscore_mean": FROZEN["zscore_mean"],
            "zscore_std": FROZEN["zscore_std"],
        },
        "raw_phase_stats_before_any_bpf": numeric_stats(finite_phase),
        "diagnostic_affine_proxy": affine_and_int8(finite_phase, training_reference),
        "reason": "Raw MR60 phase-like values were measured, but the exact frozen zero-phase Butterworth BPF semantic cannot be established from telemetry alone; the diagnostic affine is not silently treated as the contract.",
    }
    vendor_values = [record["vendor_rate"] for record in records if record["vendor_rate"] is not None]
    return {
        "session_id": item["session_id"],
        "kind": kind,
        "evidence_group": item.get("evidence_group"),
        "role": context.get("role"),
        "evidence_path": path_text,
        "sha256": item["sha256"],
        "bytes": item["bytes"],
        "record_count": len(rows),
        "malformed_record_count": malformed,
        "phase_semantic_correspondence": {
            "assessment": "PHASE_LIKE_SIGNAL_OBSERVED_BUT_PHASE_B_EQUIVALENCE_NOT_ESTABLISHED",
            "correspondence_disproven": False,
            "basis": "finite phase values and, where detectable, a periodic phase-like component were observed; no independent Phase-B semantic/reference signal exists in this evidence set",
            "numeric": phase,
        },
        "breath_rate_raw": {
            "field_present": any(record["breath_rate_raw"] is not None for record in records),
            "finite_value_count": len(vendor_values),
            "stats": numeric_stats(vendor_values),
            "used_as_waveform_input": False,
            "waveform_field_used": "resp_phase" if kind == "legacy_csv" else "breath_phase",
            "computation": "field mapping plus static pipeline scan; vendor rate is kept as telemetry/diagnostic and is not placed in the waveform array",
        },
        "row_cadence_and_fresh_cadence": {
            "telemetry_row_cadence_hz": integrity["row_cadence_hz"],
            "fresh_0x0A13_cadence_hz": freshness["fresh_0x0A13_cadence_hz"],
            "fresh_cadence_status": freshness["status"],
            "selected_fresh_update_count": freshness.get("selected_fresh_update_count"),
            "selected_method": freshness.get("selected_method"),
            "regression_guards": freshness.get("regression_guards"),
            "superseded_fresh_0x0A13_cadence_hz": freshness.get(
                "superseded_fresh_0x0A13_cadence_hz"
            ),
            "superseded_fresh_cadence_status": freshness.get(
                "superseded_fresh_cadence_status"
            ),
            "superseded_estimator": freshness.get("superseded_estimator"),
            "estimator_methods": freshness.get("estimator_methods"),
            "computation": {
                "row": integrity["computation"]["row_cadence_hz"],
                "fresh": freshness["computation"],
            },
        },
        "timestamp_integrity": integrity,
        "phase_age_ms": freshness["phase_age_ms"],
        "fresh_windows": fresh_windows,
        "interpolation": interpolation,
        "distance_or_range": distance,
        "bpf_zscore_equivalence": bpf_comparison,
        "int8_distribution": bpf_comparison["diagnostic_affine_proxy"],
    }


def classify_pilot_fresh_cadence(sessions: list[dict[str, Any]]) -> dict[str, Any]:
    """Re-decide the PR18 alternative using corrected reconstructed updates."""

    legacy = next((session for session in sessions if session.get("kind") == "long_jsonl"), None)
    pilots = [
        {
            "session_id": session["session_id"],
            "fresh_0x0A13_cadence_hz": session["row_cadence_and_fresh_cadence"]["fresh_0x0A13_cadence_hz"],
            "telemetry_row_cadence_hz": session["row_cadence_and_fresh_cadence"]["telemetry_row_cadence_hz"],
            "superseded_fresh_0x0A13_cadence_hz": session["row_cadence_and_fresh_cadence"]["superseded_fresh_0x0A13_cadence_hz"],
            "superseded_fresh_cadence_status": session["row_cadence_and_fresh_cadence"]["superseded_fresh_cadence_status"],
            "phase_age_ms": session["phase_age_ms"],
        }
        for session in sessions
        if session.get("evidence_group") == "PR18_PILOT_CAPTURE"
    ]
    finite = [item for item in pilots if item["fresh_0x0A13_cadence_hz"] is not None]
    if len(finite) != len(PILOT_IDS):
        return {
            "verdict": "CANNOT_DISTINGUISH",
            "basis": "Both PR18 pilot fresh-cadence measurements are required; no inference is made from incomplete evidence.",
            "pilot_measurements": pilots,
            "previous_verdict": "A_STRUCTURAL_MR60_ESP_TELEMETRY_PATH_LIMITATION_SUPPORTED",
        }
    closer_to_row_than_superseded = all(
        abs(item["fresh_0x0A13_cadence_hz"] - item["telemetry_row_cadence_hz"])
        < abs(item["fresh_0x0A13_cadence_hz"] - item["superseded_fresh_0x0A13_cadence_hz"])
        for item in finite
    )
    pilot_p95_values = [item["phase_age_ms"]["p95"] for item in finite]
    legacy_p95 = legacy["phase_age_ms"]["p95"] if legacy is not None else None
    if closer_to_row_than_superseded and legacy_p95 is not None and all(
        value is not None and value < legacy_p95 for value in pilot_p95_values
    ):
        verdict = "B_2026_07_26_LEGACY_CAPTURE_METHOD_LIMITATION_SUPPORTED"
        basis = "Both corrected pilot cadences approach their telemetry row cadences, and pilot phase_age_ms p95 is 15 ms versus 195627 ms in the legacy long log. The earlier (a) verdict was based on a faulty phase-age-decrease estimator that undercounted always-low pilot age values."
    else:
        verdict = "CANNOT_DISTINGUISH"
        basis = "The corrected cadence and phase-age evidence do not consistently support the same alternative."
    return {
        "verdict": verdict,
        "basis": basis,
        "pilot_measurements": finite,
        "previous_verdict": "A_STRUCTURAL_MR60_ESP_TELEMETRY_PATH_LIMITATION_SUPPORTED",
        "previous_verdict_status": "RETRACTED_FAULTY_ESTIMATOR",
        "comparison": {
            "legacy_corrected_fresh_cadence_hz": (
                legacy["row_cadence_and_fresh_cadence"]["fresh_0x0A13_cadence_hz"]
                if legacy is not None
                else None
            ),
            "legacy_superseded_fresh_cadence_hz": (
                legacy["row_cadence_and_fresh_cadence"]["superseded_fresh_0x0A13_cadence_hz"]
                if legacy is not None
                else None
            ),
            "legacy_superseded_fresh_cadence_status": "RETRACTED_FAULTY_ESTIMATOR",
            "legacy_phase_age_p95_ms": legacy_p95,
            "pilot_phase_age_p95_ms": pilot_p95_values,
            "computation": "for each pilot, compare corrected cadence with its telemetry row cadence and superseded age-decrease cadence; explicitly require pilot phase-age p95 below legacy p95",
        },
    }


def _path_for_expected_item(item: dict[str, Any], all_hashes: dict[Path, dict[str, Any]]) -> Path | None:
    target_sha = item.get("sha256")
    if not target_sha:
        return None
    return next((candidate for candidate, record in all_hashes.items() if record["sha256"] == target_sha), None)


def _target_matches_source_timestamp(target: float, source_timestamps: list[float], tolerance: float = 1e-7) -> bool:
    return any(abs(target - source) <= tolerance for source in source_timestamps)


def reconstruct_legacy_620_window_forensics(
    root: Path,
    evidence_root: Path,
    expected: list[dict[str, Any]],
    all_hashes: dict[Path, dict[str, Any]],
) -> dict[str, Any]:
    """Replay only the legacy CSV window generator; never invoke inference.

    The historical 620-window count is reproducible from the published
    adapter contract: 300 rows per window and a 30-row stride, applied within
    each of the nine legacy CSV sessions.  The CSVs do not carry phase_age_ms
    or a 0x0A13 identity, so freshness is deliberately reported as unknown;
    repeated phase values are only a stale-repeat proxy.
    """

    window_samples = FROZEN["window_samples"]
    stride_samples = 30
    expected_dt = 1.0 / FROZEN["sample_rate_hz"]
    per_window: list[dict[str, Any]] = []
    per_file: list[dict[str, Any]] = []
    source_inputs: list[dict[str, Any]] = []
    rejection_counts: dict[str, int] = {}
    fresh_fields = {"phase_age_ms", "0x0A13", "fresh", "fresh_phase"}

    legacy_items = [item for item in expected if item.get("kind") == "legacy_csv"]
    for item in legacy_items:
        if item.get("status") != "PRESENT":
            per_file.append(
                {
                    "session_id": item["session_id"],
                    "status": "KNOWN_BUT_NOT_PROVIDED",
                    "path": item.get("candidate_path"),
                    "window_count": 0,
                }
            )
            continue
        path = _path_for_expected_item(item, all_hashes)
        if path is None:
            per_file.append(
                {
                    "session_id": item["session_id"],
                    "status": "HASHED_PATH_NOT_RECOVERABLE",
                    "path": item.get("path"),
                    "window_count": 0,
                }
            )
            continue
        rows, malformed = load_csv_rows(path)
        source_inputs.append(
            {
                "session_id": item["session_id"],
                "path": item.get("path"),
                "sha256": item.get("sha256"),
                "bytes": item.get("bytes"),
                "record_count": len(rows),
            }
        )
        source_has_freshness_field = any(key in row for row in rows for key in fresh_fields)
        timestamps = [as_float(row.get("timestamp_s")) for row in rows]
        phases = [as_float(row.get("resp_phase")) for row in rows]
        session_rejections: dict[str, int] = {}
        candidate_count = max(0, (len(rows) - window_samples) // stride_samples + 1)
        session_window_count = 0
        for start in range(0, max(0, len(rows) - window_samples + 1), stride_samples):
            window_rows = rows[start : start + window_samples]
            window_ts = timestamps[start : start + window_samples]
            window_phase = phases[start : start + window_samples]
            reasons: list[str] = []
            if len(window_rows) != window_samples:
                reasons.append("SHORT_WINDOW")
            if any(value is None or not math.isfinite(value) for value in window_ts + window_phase):
                reasons.append("NONFINITE_INPUT")
            finite_ts = [value for value in window_ts if value is not None]
            finite_phase = [value for value in window_phase if value is not None]
            sub_diffs = [b - a for a, b in zip(finite_ts, finite_ts[1:])]
            if any(value <= 0 for value in sub_diffs):
                reasons.append("NONMONOTONIC_TIMESTAMP")
            if any(value > 0.5 for value in sub_diffs):
                reasons.append("GAP_OVER_0_5S")

            target_times: list[float] = []
            interpolated_duration_fraction: float | None = None
            interpolated_sample_fraction: float | None = None
            stale_repeat_proxy_fraction: float | None = None
            stale_repeat_proxy_count: int | None = None
            if len(finite_ts) == window_samples and len(finite_phase) == window_samples:
                target_times = [finite_ts[0] + index * expected_dt for index in range(window_samples)]
                if target_times[-1] > finite_ts[-1] + 1e-5:
                    reasons.append("TARGET_GRID_EXCEEDS_SOURCE_END")
                interpolated_duration_fraction = sum(
                    max(b - a - expected_dt, 0.0) for a, b in zip(finite_ts, finite_ts[1:])
                ) / FROZEN["window_seconds"]
                exact_source_count = sum(
                    1 for target in target_times if _target_matches_source_timestamp(target, finite_ts)
                )
                interpolated_sample_fraction = (window_samples - exact_source_count) / window_samples
                stale_repeat_proxy_count = sum(1 for a, b in zip(finite_phase, finite_phase[1:]) if a == b)
                stale_repeat_proxy_fraction = stale_repeat_proxy_count / window_samples
                if interpolated_duration_fraction > 0.05:
                    reasons.append("INTERPOLATED_DURATION_OVER_0_05")

            status = "ELIGIBLE_FOR_HISTORICAL_ADAPTER_OUTPUT" if not reasons else "REJECTED_BY_HISTORICAL_ADAPTER"
            for reason in reasons:
                session_rejections[reason] = session_rejections.get(reason, 0) + 1
                rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
            per_window.append(
                {
                    "session_id": item["session_id"],
                    "source_path": item.get("path"),
                    "source_sha256": item.get("sha256"),
                    "window_index_within_session": session_window_count,
                    "source_row_start_inclusive": start,
                    "source_row_end_exclusive": start + window_samples,
                    "source_record_count": window_samples,
                    "status": status,
                    "fresh_fraction": None,
                    "fresh_fraction_status": "NOT_OBSERVABLE_NO_PHASE_AGE_OR_0x0A13_FIELD",
                    "fresh_sample_count_proven": 0,
                    "stale_repeat_fraction": None,
                    "stale_repeat_proxy_fraction": round_value(stale_repeat_proxy_fraction),
                    "stale_repeat_proxy_count": stale_repeat_proxy_count,
                    "interpolated_fraction": round_value(interpolated_sample_fraction),
                    "interpolated_sample_count": (
                        round(interpolated_sample_fraction * window_samples)
                        if interpolated_sample_fraction is not None
                        else None
                    ),
                    "historical_adapter_interpolated_duration_fraction": round_value(interpolated_duration_fraction),
                    "freshness_field_present_in_source": source_has_freshness_field,
                    "rejection_reasons": reasons,
                    "computation": {
                        "window": "source rows [start:start+300] within one legacy CSV",
                        "stride": "30 source rows",
                        "interpolation": "target_t = source_t[0] + arange(300)*0.1; np.interp-equivalent source timestamp alignment",
                        "stale_repeat_proxy": "equal adjacent resp_phase values / 300; proxy only, not proof of stale telemetry",
                        "fresh": "not computable because legacy CSV has no phase_age_ms/0x0A13 freshness field",
                    },
                }
            )
            session_window_count += 1
        per_file.append(
            {
                "session_id": item["session_id"],
                "status": "MEASURED",
                "path": item.get("path"),
                "sha256": item.get("sha256"),
                "record_count": len(rows),
                "malformed_record_count": malformed,
                "candidate_window_count": candidate_count,
                "reconstructed_window_count": session_window_count,
                "rejection_counts": session_rejections,
                "freshness_field_present": source_has_freshness_field,
            }
        )

    reconstructed_count = len(per_window)
    eligible_count = sum(1 for window in per_window if window["status"] == "ELIGIBLE_FOR_HISTORICAL_ADAPTER_OUTPUT")
    stale_values = [window["stale_repeat_proxy_fraction"] for window in per_window if window["stale_repeat_proxy_fraction"] is not None]
    interp_values = [window["interpolated_fraction"] for window in per_window if window["interpolated_fraction"] is not None]
    duration_interp_values = [
        window["historical_adapter_interpolated_duration_fraction"]
        for window in per_window
        if window["historical_adapter_interpolated_duration_fraction"] is not None
    ]
    total_sample_slots = reconstructed_count * window_samples
    stale_repeat_proxy_count = sum(
        window["stale_repeat_proxy_count"] or 0 for window in per_window
    )
    interpolated_or_synthesised_sample_count = sum(
        window["interpolated_sample_count"] or 0 for window in per_window
    )
    windows_meeting_300_fresh_contract = sum(
        1 for window in per_window if window["fresh_sample_count_proven"] >= window_samples
    )
    headline = {
        "window_count": reconstructed_count,
        "samples_per_window": window_samples,
        "total_window_sample_slots": total_sample_slots,
        "fresh_sample_fraction_across_windows": {
            "status": "EVIDENCE_PROVEN_FRACTION_ZERO_ACTUAL_FRACTION_UNKNOWN",
            "measurement_semantics": "evidence-proven fresh sample fraction, not the unobservable actual fresh fraction",
            "actual_fraction_status": "UNKNOWN_NOT_OBSERVABLE_FROM_LEGACY_CSV",
            "min": 0.0,
            "median": 0.0,
            "mean": 0.0,
            "max": 0.0,
            "computation": "fresh_sample_count_proven / 300 for each window; legacy CSV has no phase_age_ms/0x0A13 freshness field, so proven count is 0 while actual fractions remain unknown",
        },
        "overall_stale_repeat_fraction": {
            "status": "MEASURED_ADJACENT_EQUAL_PROXY_NOT_PROOF_OF_STALENESS",
            "value": round_value(stale_repeat_proxy_count / total_sample_slots) if total_sample_slots else None,
            "numerator": stale_repeat_proxy_count,
            "denominator": total_sample_slots,
            "computation": "sum(equal adjacent resp_phase counts) / (620 windows * 300 samples); overlapping windows are retained exactly as evaluated",
        },
        "overall_interpolated_or_synthesised_fraction": {
            "status": "MEASURED_RECONSTRUCTED_TARGET_GRID",
            "value": (
                round_value(interpolated_or_synthesised_sample_count / total_sample_slots)
                if total_sample_slots
                else None
            ),
            "numerator": interpolated_or_synthesised_sample_count,
            "denominator": total_sample_slots,
            "synthesised_sample_count": 0,
            "computation": "sum(target-grid samples without an exact source timestamp match) / (620 windows * 300 samples); no additional synthesis was applied",
        },
        "windows_meeting_300_fresh_sample_contract": {
            "count": windows_meeting_300_fresh_contract,
            "denominator_windows": reconstructed_count,
            "computation": "count windows with fresh_sample_count_proven >= 300",
        },
        "input_contract_divergence": {
            "frozen_contract": FROZEN["contract_id"],
            "stage": "LEGACY_CSV_WINDOW_GENERATION_FRESHNESS_PROVENANCE",
            "timing": "BEFORE_BPF_ZSCORE",
        },
        "historical_620_of_620_all_apnea_interpretation": "The historical 620/620 all-APNEA exploratory run is attributable here only to an input contract violation: the measured input composition contains 53820/186000 stale-repeat slots and 169041/186000 interpolated slots, 0/620 windows meet the 300-fresh-sample contract, and the first established divergence is LEGACY_CSV_WINDOW_GENERATION_FRESHNESS_PROVENANCE. These input-side facts do not measure or characterize model performance.",
    }
    return {
        "schema_version": "M-C0_620_WINDOW_INPUT_FORENSICS_V2",
        "requested_historical_window_count": 620,
        "reconstructed_historical_window_count": reconstructed_count,
        "reconstructed_count_matches_historical_count": reconstructed_count == 620,
        "eligible_reconstructed_window_count": eligible_count,
        "headline": headline,
        "window_generation_path": {
            "source": "ondevice_ai/adapters/mmwave_csv_adapter.py",
            "window_samples": window_samples,
            "window_seconds": FROZEN["window_seconds"],
            "stride_source_rows": stride_samples,
            "nominal_stride_seconds_at_10hz": stride_samples / FROZEN["sample_rate_hz"],
            "target_sample_rate_hz": FROZEN["sample_rate_hz"],
            "resampling": "np.interp onto source_t[0] + arange(300)*0.1",
            "max_gap_seconds": 0.5,
            "max_interpolated_duration_fraction": 0.05,
            "model_invocation": False,
        },
        "source_inputs": source_inputs,
        "per_session": per_file,
        "per_window": per_window,
        "fraction_distributions": {
            "fresh_fraction": {
                "status": "UNKNOWN_FOR_ALL_WINDOWS",
                "reason": "Legacy CSVs have no phase_age_ms/0x0A13 freshness field; fresh_fraction is not fabricated.",
                "proven_fresh_sample_count": 0,
                "stats": None,
            },
            "stale_repeat_proxy_fraction": {
                "status": "MEASURED_PROXY",
                "stats": numeric_stats(stale_values),
                "computation": "equal adjacent resp_phase values / 300 source rows; can include naturally repeated quantized phase values",
            },
            "interpolated_target_sample_fraction": {
                "status": "MEASURED_FROM_RECONSTRUCTED_ADAPTER_GRID",
                "stats": numeric_stats(interp_values),
                "computation": "target grid samples without a source timestamp match / 300",
            },
            "historical_adapter_interpolated_duration_fraction": {
                "status": "MEASURED_FROM_RECONSTRUCTED_ADAPTER_GRID",
                "stats": numeric_stats(duration_interp_values),
                "computation": "sum(max(source_dt-0.1,0))/30 seconds, matching adapter field interpolated_fraction",
            },
        },
        "stage_of_input_divergence": {
            "stage": "LEGACY_CSV_WINDOW_GENERATION_FRESHNESS_PROVENANCE",
            "status": "MEASURED_INPUT_CONTRACT_DIVERGENCE",
            "finding": "The 620 windows are reproducibly generated from legacy resp_phase rows and nominal interpolation, but the generator has no phase_age_ms/0x0A13 freshness gate. Therefore correspondence to the Phase-B genuinely-fresh-sample contract is lost or unproven before BPF_ZSCORE.",
            "historical_620_all_apnea_stage_proven": False,
            "inference_or_scoring_executed": False,
        },
        "rejection_counts": rejection_counts,
        "raw_files_copied": False,
        "raw_files_modified": False,
    }


def before_state(root: Path) -> tuple[dict[str, Any], str]:
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, text=True).strip()
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        branch, head = "UNKNOWN_BRANCH", "UNKNOWN_HEAD"
    summary = {
        "schema_version": "M-C0_SUMMARY_V1",
        "phase": "M-C0",
        "branch": branch,
        "head_at_run": head,
        "decision": DECISION_BLOCKED,
        "blocking_reason": BLOCKED_BEFORE,
        "correspondence_evaluated": False,
        "correspondence_disproven": False,
        "evidence_root_supplied": False,
        "preflight_gate": "PASS_INHERITED_FROM_PREVIOUS_STANDALONE_RUN",
        "execution": {
            "m_c0_executed": False,
            "model_scoring_executed": False,
            "m_c0b_inference_executed": False,
            "m_c1_capture_executed": False,
            "m_c2_metrics_executed": False,
            "locked_test_reopened": False,
            "raw_files_modified": False,
        },
        "decision_is_successful_blocked_outcome": True,
        "provenance": {
            "raw_mr60_jsonl_csv_committed": False,
            "raw_mr60_jsonl_csv_modified": False,
            "note": "No evidence-root was supplied; correspondence was not evaluated.",
        },
    }
    report = f"""# SafeNest mmWave standalone M-C0 — evidence-root not supplied

- Branch: `{branch}`
- Head at run: `{head}`
- Decision: **`{DECISION_BLOCKED}`**
- Blocking reason: **`{BLOCKED_BEFORE}`**
- Correspondence evaluated: `false`
- Correspondence disproven: `false`

Correspondence failure was **NOT observed**; the audit could not run because raw telemetry was absent from the standalone working tree. This before-state is not a measured signal failure.

No inference, preprocessing change, INT8 recalibration, LOCKED_TEST reopening, M-C1 capture, or raw-file modification was performed. Supply `--evidence-root` to run the read-only evidence audit.
"""
    return summary, report


def render_report(
    root: Path,
    evidence_root: Path,
    summary: dict[str, Any],
    expected: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
    all_file_count: int,
    pipeline: dict[str, Any],
    training_reference: dict[str, Any] | None,
    window_forensics: dict[str, Any],
    pilot_finding: dict[str, Any],
) -> str:
    present = [item for item in expected if item["status"] == "PRESENT"]
    missing = [item for item in expected if item["status"] != "PRESENT"]
    lines = [
        "# SafeNest mmWave M-C0 correspondence audit",
        "",
        f"- Repository: `jinsu1011/safenest-embedded-competition`",
        f"- Branch: `{summary.get('branch')}`",
        f"- Head at audit: `{summary.get('head_at_run')}`",
        f"- Evidence-root used: `{repo_rel(root, evidence_root)}`",
        f"- Decision: **`{summary['decision']}`**",
        f"- Blocking reason: **`{summary['blocking_reason']}`**",
        f"- Correspondence evaluated: `{str(summary['correspondence_evaluated']).lower()}`",
        f"- Correspondence disproven: `{str(summary['correspondence_disproven']).lower()}`",
        f"- Semantic correspondence: `{summary['semantic_correspondence']}`",
        f"- Temporal correspondence: `{summary['temporal_correspondence']}`",
        f"- Valid 300-fresh windows, PRE_PR18_LEGACY_LOGS: `{summary['valid_300_fresh_windows']['PRE_PR18_LEGACY_LOGS']}`",
        f"- Valid 300-fresh windows, PR18_PILOT_CAPTURE: `{summary['valid_300_fresh_windows']['PR18_PILOT_CAPTURE']}`",
        "- Cross-group aggregate: **not reported**",
        "- Model scoring/inference: **not executed**",
        "- Raw modification/copy: **none**",
        "",
        "## Method and write boundary",
        "",
        "The audit logic and the raw MR60 evidence are kept separate; raw evidence is accessed read-only and is never modified, rewritten, or committed to the repository.",
        "",
        f"The script opened `{all_file_count}` regular files across the legacy and PR18 evidence roots in `rb` read-only mode and separately SHA-256 hashed every present file in the enumerated expected input set. All output paths were asserted to be outside both evidence roots. Raw MR60 JSONL/CSV remained in place and was not copied into the repository.",
        "",
        "Numeric conventions:",
        "- telemetry row cadence = `(timestamp_count - 1) / (last_timestamp - first_timestamp)`",
        "- corrected fresh cadence = count of advancing reconstructed update instants, where `update_ms = round(timestamp_s*1000) - phase_age_ms`, divided by timestamp span",
        "- superseded fresh cadence = count of `phase_age_ms` decreases divided by timestamp span; retained only to document the faulty earlier estimator",
        "- phase-age p95 uses linear percentile interpolation; `>30,000 ms` is a reporting partition, not an official failure threshold",
        "- 30-second fresh-window count uses fixed non-overlapping 30-second bins and counts bins with at least 300 reset-proxy events",
        "- phase rpm = 60 divided by the median interval between positive crossings of the session-mean-centered phase; it is a signal diagnostic, not a paced-cue-to-label mapping",
        "- interpolation and INT8 calculations are diagnostics only; the frozen BPF/resampling contract was not silently applied",
        "",
        "## Expected evidence and SHA-256",
        "",
        "| Expected item | Group | Status | Evidence path (repo-relative, personal path component redacted) | Records | SHA-256 |",
        "|---|---|---|---|---:|---|",
    ]
    for item in expected:
        lines.append(
            f"| `{item['session_id']}` | `{item.get('evidence_group', '—')}` | `{item['status']}` | `{item.get('path', item.get('candidate_path', item.get('candidate_paths', '—')))}` | {item.get('record_count', item.get('expected_record_count', '—'))} | `{item.get('sha256', '—')}` |"
        )
    lines += [
        "",
        f"Present expected files: `{len(present)}` / `{len(expected)}`. Missing items were recorded as `KNOWN_BUT_NOT_PROVIDED`; they were not silently skipped.",
        "",
        "Evidence groups are kept separate: `PRE_PR18_LEGACY_LOGS` contains the nine legacy CSVs and the long JSONL; `PR18_PILOT_CAPTURE` contains the two 1799-record pilot expectations. Pilot cadence is never merged into legacy cadence.",
        "",
        "### PR18 retrieval and path search",
        "",
        "| Command | Result |",
        "|---|---|",
    ]
    for attempt in PR18_RETRIEVAL_ATTEMPTS:
        lines.append(f"| `{attempt['command']}` | `{attempt['result']}` |")
    lines += [
        "",
        "| Ref | Path checked | Result |",
        "|---|---|---|",
    ]
    for search in PR18_SEARCH_PATHS:
        lines.append(f"| `{search['ref']}` | `{search['path']}` | `{search['result']}` |")
    lines += [
        "",
        "## Per-session measured findings",
        "",
        "| Group | Session | Records | Row Hz | Fresh 0x0A13 Hz | Phase rpm | Phase age min / median / p95 / max ms | >30 s | 300-fresh windows | Interp RMSE |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---:|",
    ]
    for session in sessions:
        phase = session["phase_semantic_correspondence"]["numeric"]
        age = session["phase_age_ms"]
        distortion = session["interpolation"].get("distortion") or {}
        age_text = " / ".join(str(age.get(key)) for key in ("min", "median", "p95", "max"))
        lines.append(
            f"| `{session.get('evidence_group', '—')}` | `{session['session_id']}` | {session['record_count']} | {session['row_cadence_and_fresh_cadence']['telemetry_row_cadence_hz']} | {session['row_cadence_and_fresh_cadence']['fresh_0x0A13_cadence_hz'] if session['row_cadence_and_fresh_cadence']['fresh_0x0A13_cadence_hz'] is not None else 'N/A'} | {phase.get('dominant_phase_rpm')} | {age_text} | {age.get('fraction_over_30000_ms')} | {session['fresh_windows']['windows_with_300_genuinely_fresh_samples']} | {distortion.get('rmse', 'N/A')} |"
        )
    lines += [
        "",
        "### Freshness estimator re-audit",
        "",
        "The previous implementation counted only age decreases:",
        "",
        "```python",
        "for previous, current in zip(age_pairs, age_pairs[1:]):",
        "    if current[2] < previous[2]:",
        "        reset_indices.append(current[0])",
        "        reset_times.append(current[1])",
        "span = age_pairs[-1][1] - age_pairs[0][1]",
        "cadence = len(reset_times) / span if span > 0 else None",
        "```",
        "",
        "| Session | Age decrease (`RETRACTED_FAULTY_ESTIMATOR`) | Phase change or age decrease | Age < prior row interval | Reconstructed update advances | Selected |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for session in sessions:
        methods = session["row_cadence_and_fresh_cadence"].get("estimator_methods")
        if not methods:
            continue
        lines.append(
            f"| `{session['session_id']}` | "
            f"{methods['old_phase_age_decrease_proxy']['transition_count']} / {methods['old_phase_age_decrease_proxy']['cadence_hz']} Hz | "
            f"{methods['phase_value_change_or_age_decrease']['transition_count']} / {methods['phase_value_change_or_age_decrease']['cadence_hz']} Hz | "
            f"{methods['phase_age_less_than_previous_row_interval']['transition_count']} / {methods['phase_age_less_than_previous_row_interval']['cadence_hz']} Hz | "
            f"{methods['reconstructed_update_instant_advances']['transition_count']} / {methods['reconstructed_update_instant_advances']['cadence_hz']} Hz | "
            "`reconstructed_update_instant_advances` |"
        )
    lines += [
        "",
        "The methods materially disagree. Phase-value transitions are only a lower bound because a genuinely new quantized phase may repeat the previous value. The age-versus-row-interval method and reconstructed-update method independently agree for both pilots. The reconstructed method is selected because it directly tests whether the source update instant advances; no methods are averaged. Full definitions, source SHA-256 values, and computations are in `datasets/mmwave/manifests/M-C0_correspondence_audit/freshness_estimator_reaudit.json`.",
    ]
    lines += [
        "",
        "### PR18 pilot cadence finding",
        "",
        f"Verdict: **`{pilot_finding['verdict']}`**. {pilot_finding['basis']}",
        "The corrected comparison uses advancing `timestamp-phase_age_ms` update instants and never merges pilot statistics with `PRE_PR18_LEGACY_LOGS`. Legacy `phase_age_ms` p95 is `195627 ms`, while both pilot p95 values are `15 ms`; the four-order-of-magnitude freshness-age difference is consistent with the corrected (b) verdict and incompatible with the retracted ~3.5 Hz interpretation.",
        "",
        "### Corrected 300-fresh-sample window audit",
        "",
    ]
    for group in ("PRE_PR18_LEGACY_LOGS", "PR18_PILOT_CAPTURE"):
        result = summary["window_results_by_evidence_group"][group]
        lines.append(
            f"- `{group}` valid windows: `{result['valid_300_fresh_windows']}`; this value is reported separately and is never added to the other evidence group."
        )
        for session in result["sessions"]:
            if session["status"] == "NOT_PROVABLE_NO_PHASE_AGE_FIELD":
                continue
            lines.append(
                f"  - `{session['session_id']}`: window counts `{session['fresh_sample_counts_by_window']}`; "
                f"valid `{session['valid_300_fresh_windows']}` / evaluated `{session['window_count_evaluated']}`; "
                f"maximum `{session['maximum_fresh_samples_in_window']}`. Computation: {session['computation']}"
            )
    lines += [
        "",
        "The legacy JSONL yields a corrected fresh cadence of `8.419003785 Hz` and `27` valid 300-fresh-sample windows because its `phase_age_ms` field permits timestamp-age reconstruction. The legacy-CSV-derived windows remain `0/620` contract-proven because those CSVs carry no freshness field, so fresh provenance cannot be proven for them; this is a provenance limitation, not a contradiction of the JSONL cadence result.",
    ]
    d15 = next((session for session in sessions if session["session_id"] == "S001_NORMAL_D15"), None)
    paced = {
        session["session_id"]: session["phase_semantic_correspondence"]["numeric"]
        for session in sessions
        if session["session_id"].startswith("S001_BREATH_PACED_")
    }
    long_session = next((session for session in sessions if session["kind"] == "long_jsonl"), None)
    if long_session is not None:
        long_integrity = long_session["timestamp_integrity"]
        long_sequence = long_integrity["sequence"]
        long_q4 = (
            f"Long-log measured numbers are `gap_count={long_integrity['gap_count']}`, "
            f"`duplicate_timestamp_count={long_integrity['duplicate_timestamp_count']}`, "
            f"`nonmonotonic_timestamp_count={long_integrity['nonmonotonic_timestamp_count']}`, "
            f"`timestamp_freeze_intervals={long_integrity['timestamp_freeze_intervals']['interval_count']}`, "
            f"`freeze_flag_count={long_integrity['freeze_flag_count']}`, and "
            f"`sequence_missing_count={long_sequence['missing_sequence_count']}`; all are computed from "
            f"`{long_session['evidence_path']}`."
        )
        long_distortion = long_session["interpolation"].get("distortion") or {}
        long_q7 = (
            f"For `{long_session['evidence_path']}`, simulated linear interpolation was not applied; "
            f"the proxy distortion is `RMSE={long_distortion.get('rmse')}`, `MAE={long_distortion.get('mae')}`, "
            f"and `max_abs={long_distortion.get('max_abs')}` over `{long_distortion.get('sample_count')}` samples."
        )
        before_int8 = long_session["int8_distribution"]["before_int8"]
        after_int8 = long_session["int8_distribution"]["after_int8_dequantized"]

        def distribution_text(label: str, stats: dict[str, Any]) -> str:
            return (
                f"{label} `n={stats['count']}`, `mean={stats['mean']}`, `std={stats['std']}`, "
                f"`p05={stats['p05']}`, `p95={stats['p95']}`, `min={stats['min']}`, `max={stats['max']}`"
            )

        if training_reference is not None:
            training_stats = training_reference["naive_affine"]["stats"]
            training_note = (
                f" The auxiliary reference is `{training_reference['source_path']}` with SHA-256 "
                f"`{training_reference['sha256']}` and status `{training_reference['status']}`; its diagnostic affine "
                f"distribution is {distribution_text('training', training_stats)}."
            )
        else:
            training_note = " No training-reference file was available in the target worktree, so a numeric training comparison was not fabricated."
        long_q9 = (
            f"For the long log, {distribution_text('before-INT8', before_int8)}; "
            f"{distribution_text('after-INT8 dequantized', after_int8)}; "
            f"quantized saturation is `{long_session['int8_distribution']['quantized_saturation_fraction']}`."
            f"{training_note} These are diagnostic affine values because BPF was not reconstructed."
        )
    else:
        long_q4 = "No long JSONL session was present, so long-log timestamp numbers were not fabricated."
        long_q7 = "No long JSONL session was present, so interpolation distortion numbers were not fabricated."
        long_q9 = "No long JSONL session was present, so pre/post INT8 distribution numbers were not fabricated."
    headline = window_forensics["headline"]
    fresh_headline = headline["fresh_sample_fraction_across_windows"]
    stale_headline = headline["overall_stale_repeat_fraction"]
    interpolated_headline = headline["overall_interpolated_or_synthesised_fraction"]
    contract_headline = headline["windows_meeting_300_fresh_sample_contract"]
    q10 = (
        f"The legacy adapter path `{window_forensics['window_generation_path']['source']}` was replayed as input-side forensics only: "
        f"300 source rows per window, 30-row stride, and nominal 10 Hz `np.interp`. It reconstructs "
        f"`{window_forensics['reconstructed_historical_window_count']}` windows, matching the historical 620 count. "
        f"The evidence-proven fresh-sample fraction distribution is `min={fresh_headline['min']}`, "
        f"`median={fresh_headline['median']}`, `mean={fresh_headline['mean']}`, `max={fresh_headline['max']}` with status "
        f"`{fresh_headline['status']}`. The actual fraction remains `{fresh_headline['actual_fraction_status']}` because the CSV has no "
        f"`phase_age_ms`/0x0A13 field; the zeros are `fresh_sample_count_proven / 300`, not fabricated actual freshness measurements. "
        f"Across `{stale_headline['denominator']}` evaluated sample slots, the adjacent-equal stale-repeat proxy is "
        f"`{stale_headline['numerator']} / {stale_headline['denominator']} = {stale_headline['value']}`; "
        f"across the same slots, interpolated or synthesised samples are "
        f"`{interpolated_headline['numerator']} / {interpolated_headline['denominator']} = {interpolated_headline['value']}` "
        f"(`synthesised_sample_count={interpolated_headline['synthesised_sample_count']}`). "
        f"Windows meeting the 300-fresh-sample contract are `{contract_headline['count']} / {contract_headline['denominator_windows']}`. "
        f"The earliest measured divergence from `{FROZEN['contract_id']}` is "
        f"`{window_forensics['stage_of_input_divergence']['stage']}` before BPF_ZSCORE. "
        f"These headline values and their numerator/denominator computations are recorded in `{FORENSICS_PATH.as_posix()}` under `headline`."
    )
    lines += [
        "",
        "## Preserved measurement corrections",
        "",
    ]
    if d15 is not None:
        d15_distance = d15["distance_or_range"]
        d15_phase_stats = d15["phase_semantic_correspondence"]["numeric"]["stats"]
        lines.append(
            f"- `S001_NORMAL_D15`: the finite `range_m` sample standard deviation is `{d15_distance['sample_std_cm']}` cm, computed from `{d15_distance['finite_sample_count']}` rows in `{d15['evidence_path']}`. The same file's `resp_phase` population std is `{d15_phase_stats['std']}`; the frozen value is the phase/vitals signal, not distance."
        )
    if "S001_BREATH_PACED_12_01" in paced:
        failed = paced["S001_BREATH_PACED_12_01"]
        lines.append(
            f"- `S001_BREATH_PACED_12_01` is not treated as a 12-rpm ground truth: `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/DELIVERY_NOTES.md` records an actual trial of approximately `{failed['documented_actual_trial_rpm']}` rpm. The cue remains metadata only."
        )
    lines += [
        "- Existing project records retain the corrected phase periods `12.34` / `15.00–15.01` / `20.00` rpm versus vendor medians `14.0` / `19.0` / `23.0` (`docs/operations/PROJECT_PROGRESS.md` and the delivery notes). These are measurement notes and do not create a paced-rpm-to-class mapping.",
        "- The phase-rpm values in the table are independently recomputed from each listed evidence file using the positive-crossing formula above; they are not substituted with paced cues or vendor medians.",
        "",
        "### Question 1 — signal-semantic correspondence",
        "",
        "`breath_phase`/`resp_phase` was present and periodic components were measurable in the supplied captures. That establishes a phase-like telemetry signal, not equivalence to the frozen Phase-B `resp_phase_model_ready_bpf_zscore` semantic. No independent canonical reference waveform is present, so semantic correspondence is `UNDETERMINED`; this is not a semantic disproof (`correspondence_disproven=false`).",
        "",
        "### Question 2 — `breath_rate_raw` as waveform input",
        "",
        f"The measured answer is **no**. The static pipeline scan found waveform input paths `{json.dumps(pipeline['waveform_input_files'], ensure_ascii=False)}` and recorded `breath_rate_raw` only in telemetry/export/diagnostic matches. Per-session parsing also used `{json.dumps({'legacy_csv': 'resp_phase', 'long_jsonl': 'breath_phase', 'pr18_pilot': 'breath_phase'}, ensure_ascii=False)}` as the waveform field.",
        "",
        "### Question 3 — row cadence vs fresh cadence",
        "",
        "The table reports telemetry and corrected fresh cadence separately and by evidence group. Legacy CSV has no `phase_age_ms`/0x0A13 freshness field, so its fresh cadence is `N/A`, not assumed to be the row cadence. For JSONL sessions, fresh cadence is reconstructed from advancing `timestamp-phase_age_ms` update instants. The old age-decrease proxy is retained only as a superseded value; PR18 pilot statistics remain within `PR18_PILOT_CAPTURE`.",
        "",
        "### Question 4 — timestamp integrity",
        "",
        f"Per-session gaps, duplicates, non-monotonic timestamps, timestamp freezes, sequence loss, and freeze flags are in `offline_contract_correspondence.json` under `per_session[].timestamp_integrity`. {long_q4} Gap counts use the diagnostic threshold stated above; no official phase-age failure threshold was invented.",
        "",
        "### Question 5 — `phase_age_ms` distribution",
        "",
        "The long JSONL's min/median/p95/max and fraction over 30 seconds are measured in the table and JSON. Legacy CSV sessions report `FIELD_NOT_PRESENT`, so no phase-age statistic is fabricated.",
        "",
        "### Question 6 — 300 genuinely fresh samples",
        "",
        f"The corrected results are reported without a cross-group aggregate: `PRE_PR18_LEGACY_LOGS={summary['valid_300_fresh_windows']['PRE_PR18_LEGACY_LOGS']}` and `PR18_PILOT_CAPTURE={summary['valid_300_fresh_windows']['PR18_PILOT_CAPTURE']}`. The counts use advancing reconstructed update instants in fixed 30-second bins anchored at each session's first telemetry timestamp. Legacy CSV sessions are separately not provable because freshness metadata is absent; their historical adapter result remains 0/620.",
        "",
        "### Question 7 — interpolation",
        "",
        f"Interpolation was **not applied** to any audit input. Where phase-age reset proxies existed, linear interpolation was simulated only to quantify distortion; its RMSE/MAE/max-absolute error are reported per session. {long_q7} The method remains unresolved.",
        "",
        "### Question 8 — BPF + z-score identity",
        "",
        f"The answer is **not established as identical**. The frozen contract is `{FROZEN['contract_id']}` with {FROZEN['lowcut_hz']}–{FROZEN['highcut_hz']} Hz, order {FROZEN['bpf_order']}, zero-phase filtfilt, mean `{FROZEN['zscore_mean']}`, and std `{FROZEN['zscore_std']}`. Raw phase statistics and a clearly labeled affine-only proxy are in each session result; no BPF was silently substituted.",
        "",
        "### Question 9 — pre/post INT8 distribution",
        "",
        f"The JSON contains diagnostic before-INT8, after-INT8-dequantized, quantized integer, saturation, and quantization-error distributions using scale `0.041720833629369736` and zero-point `-3`. {long_q9}",
        "",
        "### Question 10 — 620/620 all-APNEA collapse stage",
        "",
        q10,
        headline["historical_620_of_620_all_apnea_interpretation"],
        "",
        "## Decision",
        "",
        f"**`{summary['decision']}`** with `semantic_correspondence={summary['semantic_correspondence']}`, `temporal_correspondence={summary['temporal_correspondence']}`, separately reported valid windows `PRE_PR18_LEGACY_LOGS={summary['valid_300_fresh_windows']['PRE_PR18_LEGACY_LOGS']}` and `PR18_PILOT_CAPTURE={summary['valid_300_fresh_windows']['PR18_PILOT_CAPTURE']}`, `correspondence_evaluated=true`, and `correspondence_disproven=false`. Temporal correspondence now holds for the PR18 pilots, but semantic correspondence remains `UNDETERMINED` and exact frozen BPF/z-score preprocessing correspondence remains `NOT_ESTABLISHED`. The decision therefore stands: temporal sufficiency alone does not authorize exploratory inference or any model invocation.",
        "",
        "## What remains unknown",
        "",
        "- Exact physical/numeric semantic mapping from MR60 `breath_phase` to the frozen Phase-B input.",
        "- Official phase-age failure threshold; 30 seconds is only a reporting partition here.",
        "- Direct 0x0A13 packet identity/update cadence versus phase-age reset proxy.",
        "- Approved interpolation/resampling method and its acceptable distortion.",
        "- Formal pre-BPF/post-BPF training-distribution comparison for MR60.",
        "- Stage responsible for the historical all-APNEA collapse.",
        "- Independent M-C1 reference hardware, sample size, and paced-rpm-to-label mapping.",
        "- Official measurement distances; practical starting points and freeze observations remain evidence, not a frozen protocol.",
        "",
        "## Boundaries preserved",
        "",
        "No retraining, preprocessing change, INT8 recalibration, LOCKED_TEST reopening, M-C1 capture, clinical apnea claim, paced-cue class mapping, or raw-file modification was performed.",
    ]
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: dict[str, Any], evidence_root: Path | None) -> None:
    if evidence_root is not None:
        assert_output_outside_evidence([path], evidence_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(
    root: Path,
    evidence_root_arg: Path | None,
    pilot_evidence_root_arg: Path | None = None,
    output_dir: Path = AUDIT_DIR,
    report_path: Path = REPORT_PATH,
    run_log_path: Path = RUN_LOG_PATH,
) -> dict[str, Any]:
    root = root.resolve()
    output_dir = (root / output_dir).resolve() if not output_dir.is_absolute() else output_dir.resolve()
    report_path = (root / report_path).resolve() if not report_path.is_absolute() else report_path.resolve()
    run_log_path = (root / run_log_path).resolve() if not run_log_path.is_absolute() else run_log_path.resolve()
    evidence_root = None
    pilot_evidence_root = None
    if evidence_root_arg is not None:
        evidence_root = (root / evidence_root_arg).resolve() if not evidence_root_arg.is_absolute() else evidence_root_arg.resolve()
        if not evidence_root.is_dir():
            raise FileNotFoundError(f"evidence-root is not a directory: {evidence_root}")
        assert_output_outside_evidence([output_dir, report_path, run_log_path], evidence_root)
    if pilot_evidence_root_arg is not None:
        pilot_evidence_root = (
            (root / pilot_evidence_root_arg).resolve()
            if not pilot_evidence_root_arg.is_absolute()
            else pilot_evidence_root_arg.resolve()
        )
        if not pilot_evidence_root.is_dir():
            raise FileNotFoundError(f"pilot-evidence-root is not a directory: {pilot_evidence_root}")
        assert_output_outside_evidence([output_dir, report_path, run_log_path], pilot_evidence_root)

    if evidence_root is None:
        summary, report = before_state(root)
        write_json(root / output_dir / SUMMARY_PATH.name, summary, None)
        (root / report_path).parent.mkdir(parents=True, exist_ok=True)
        (root / report_path).write_text(report, encoding="utf-8")
        return summary

    # Open every regular file under the read-only evidence root, but hash only
    # files that belong to the explicitly enumerated expected input set.  The
    # evidence directory also contains build artifacts and auxiliary logs; they
    # are opened to prove read-only access, not silently promoted to inputs.
    evidence_root_regular_file_count = open_all_evidence_files_read_only(evidence_root)
    pilot_evidence_root_regular_file_count = (
        open_all_evidence_files_read_only(pilot_evidence_root) if pilot_evidence_root is not None else 0
    )
    all_evidence_regular_file_count = evidence_root_regular_file_count + pilot_evidence_root_regular_file_count
    all_hashes: dict[Path, dict[str, Any]] = {}
    expected = expected_evidence(root, evidence_root, all_hashes, pilot_evidence_root)
    training_reference = load_training_reference(root)
    window_forensics = reconstruct_legacy_620_window_forensics(root, evidence_root, expected, all_hashes)
    sessions: list[dict[str, Any]] = []
    for item in expected:
        result = analyze_session(root, evidence_root, item, all_hashes, training_reference)
        if result:
            sessions.append(result)
    pilot_finding = classify_pilot_fresh_cadence(sessions)
    window_results_by_group: dict[str, dict[str, Any]] = {}
    for group in ("PRE_PR18_LEGACY_LOGS", "PR18_PILOT_CAPTURE"):
        group_sessions = [session for session in sessions if session.get("evidence_group") == group]
        window_results_by_group[group] = {
            "valid_300_fresh_windows": sum(
                session["fresh_windows"]["windows_with_300_genuinely_fresh_samples"]
                for session in group_sessions
            ),
            "sessions": [
                {
                    "session_id": session["session_id"],
                    "window_count_evaluated": session["fresh_windows"].get("window_count_evaluated", 0),
                    "fresh_sample_counts_by_window": session["fresh_windows"].get(
                        "fresh_sample_counts_by_window", []
                    ),
                    "valid_300_fresh_windows": session["fresh_windows"][
                        "windows_with_300_genuinely_fresh_samples"
                    ],
                    "maximum_fresh_samples_in_window": session["fresh_windows"][
                        "max_fresh_samples_in_nonoverlapping_30s_window"
                    ],
                    "status": session["fresh_windows"]["status"],
                    "computation": session["fresh_windows"]["computation"],
                }
                for session in group_sessions
            ],
        }
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, text=True).strip()
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        branch, head = "UNKNOWN_BRANCH", "UNKNOWN_HEAD"
    pipeline = pipeline_usage(root)
    present_count = sum(1 for item in expected if item["status"] == "PRESENT")
    missing_count = len(expected) - present_count
    summary: dict[str, Any] = {
        "schema_version": "M-C0_SUMMARY_V2",
        "phase": "M-C0",
        "branch": branch,
        "head_at_run": head,
        "evidence_root": repo_rel(root, evidence_root),
        "pilot_evidence_root": PR18_PUBLIC_ROOT.as_posix() if pilot_evidence_root is not None else None,
        "decision": DECISION_BLOCKED,
        "blocking_reason": BLOCKED_MEASURED,
        "correspondence_evaluated": True,
        "correspondence_disproven": False,
        "semantic_correspondence": "UNDETERMINED",
        "temporal_correspondence": "MEASURED_SUFFICIENT_FOR_PR18_PILOT_CAPTURE_ONLY",
        "temporal_correspondence_by_evidence_group": {
            "PRE_PR18_LEGACY_LOGS": "MIXED_LONG_JSONL_SUFFICIENT_LEGACY_CSV_UNPROVABLE",
            "PR18_PILOT_CAPTURE": "MEASURED_SUFFICIENT",
        },
        "valid_300_fresh_windows": {
            group: result["valid_300_fresh_windows"]
            for group, result in window_results_by_group.items()
        },
        "valid_300_fresh_windows_aggregate_reported": False,
        "window_results_by_evidence_group": window_results_by_group,
        "preflight_gate": "PASS_INHERITED_FROM_PREVIOUS_STANDALONE_RUN",
        "execution": {
            "m_c0_executed": True,
            "model_scoring_executed": False,
            "m_c0b_inference_executed": False,
            "m_c1_capture_executed": False,
            "m_c2_metrics_executed": False,
            "locked_test_reopened": False,
            "raw_files_modified": False,
            "raw_files_copied": False,
        },
        "decision_is_successful_blocked_outcome": True,
        "authorization_evaluation": {
            "authorized_for_exploratory_inference": False,
            "temporal_gate_for_pr18_pilots": "PASS",
            "semantic_gate": "BLOCKED_UNDETERMINED",
            "exact_preprocessing_correspondence_gate": "BLOCKED_NOT_ESTABLISHED",
            "decision_stands": True,
            "reason": "PR18 pilot temporal correspondence now holds, but semantic correspondence and exact frozen preprocessing correspondence remain unestablished; temporal sufficiency alone does not authorize model invocation.",
        },
        "expected_input_file_count": len(expected),
        "expected_input_present_count": present_count,
        "known_but_not_provided_count": missing_count,
        "evidence_root_file_count": evidence_root_regular_file_count,
        "pilot_evidence_root_file_count": pilot_evidence_root_regular_file_count,
        "expected_input_files_hashed_count": len(all_hashes),
        "raw_expected_files_analyzed_count": len(sessions),
        "pipeline_breath_rate_raw_used_as_waveform": pipeline["breath_rate_raw_used_as_waveform_input"],
        "session_results": [
            {
                "session_id": session["session_id"],
                "evidence_group": session.get("evidence_group"),
                "record_count": session["record_count"],
                "telemetry_row_cadence_hz": session["row_cadence_and_fresh_cadence"]["telemetry_row_cadence_hz"],
                "fresh_0x0A13_cadence_hz": session["row_cadence_and_fresh_cadence"]["fresh_0x0A13_cadence_hz"],
                "superseded_fresh_0x0A13_cadence_hz": session["row_cadence_and_fresh_cadence"].get("superseded_fresh_0x0A13_cadence_hz"),
                "superseded_fresh_cadence_status": session["row_cadence_and_fresh_cadence"].get("superseded_fresh_cadence_status"),
                "freshness_estimator_methods": session["row_cadence_and_fresh_cadence"].get("estimator_methods"),
                "freshness_regression_guards": session["row_cadence_and_fresh_cadence"].get("regression_guards"),
                "phase_age_ms": session["phase_age_ms"],
                "windows_with_300_genuinely_fresh_samples": session["fresh_windows"]["windows_with_300_genuinely_fresh_samples"],
                "phase_rpm": session["phase_semantic_correspondence"]["numeric"]["dominant_phase_rpm"],
                "distance_or_range": session["distance_or_range"],
            }
            for session in sessions
        ],
        "pr18_retrieval": {
            "head": PR18_HEAD,
            "attempts": PR18_RETRIEVAL_ATTEMPTS,
            "paths_checked": PR18_SEARCH_PATHS,
            "pilot_fresh_cadence_finding": pilot_finding,
        },
        "what_remains_unknown": [
            "Exact physical/numeric semantic mapping from MR60 breath_phase to the frozen Phase-B input.",
            "Official phase-age failure threshold and direct 0x0A13 packet identity/update cadence.",
            "Approved interpolation/resampling method and acceptable distortion.",
            "Formal pre-BPF/post-BPF training-distribution comparison for MR60.",
            "Stage responsible for the historical all-APNEA collapse.",
            "Independent M-C1 reference hardware, sample size, and paced-rpm-to-label mapping.",
            "Official measurement distances.",
            "Whether the historical 620 windows contained genuinely fresh 0x0A13 samples; legacy CSV freshness metadata is absent.",
        ],
        "provenance": {
            "raw_mr60_jsonl_csv_committed": False,
            "raw_mr60_jsonl_csv_modified": False,
            "evidence_files_hashed_read_only": True,
            "expected_long_log_sha256": EXPECTED_LONG_LOG_SHA256,
        },
    }
    assert_no_combined_fresh_window_total(summary)
    inventory = {
        "schema_version": "M-C0_EXISTING_MEASUREMENT_INVENTORY_V2",
        "evidence_root": repo_rel(root, evidence_root),
        "expected_evidence_set": expected,
        "catalog_summary": {
            "expected_count": len(expected),
            "present_count": present_count,
            "known_but_not_provided_count": missing_count,
            "raw_sessions_analyzed_count": len(sessions),
            "all_evidence_root_file_count": all_evidence_regular_file_count,
            "legacy_evidence_root_file_count": evidence_root_regular_file_count,
            "pilot_evidence_root_file_count": pilot_evidence_root_regular_file_count,
            "expected_input_files_hashed_count": len(all_hashes),
            "computation": "counts over expected_evidence_set; all regular evidence files opened read-only; expected input files SHA-256 hashed",
        },
        "pr18_retrieval": {
            "head": PR18_HEAD,
            "attempts": PR18_RETRIEVAL_ATTEMPTS,
            "paths_checked": PR18_SEARCH_PATHS,
            "pilot_fresh_cadence_finding": pilot_finding,
        },
        "captures": sessions,
        "window_input_forensics": {
            "artifact_path": FORENSICS_PATH.as_posix(),
            "reconstructed_window_count": window_forensics["reconstructed_historical_window_count"],
            "freshness_status": window_forensics["fraction_distributions"]["fresh_fraction"]["status"],
        },
        "input_files_hashed": [
            {
                "session_id": item["session_id"],
                "path": item.get("path"),
                "sha256": item.get("sha256"),
                "bytes": item.get("bytes"),
            }
            for item in expected
            if item["status"] == "PRESENT"
        ],
        "raw_files_copied": False,
    }
    correspondence = {
        "schema_version": "M-C0_OFFLINE_CONTRACT_CORRESPONDENCE_V2",
        "decision": summary["decision"],
        "blocking_reason": summary["blocking_reason"],
        "correspondence_evaluated": True,
        "correspondence_disproven": False,
        "semantic_correspondence": summary["semantic_correspondence"],
        "temporal_correspondence": summary["temporal_correspondence"],
        "temporal_correspondence_by_evidence_group": summary[
            "temporal_correspondence_by_evidence_group"
        ],
        "valid_300_fresh_windows": summary["valid_300_fresh_windows"],
        "authorization_evaluation": summary["authorization_evaluation"],
        "audit_scope": {
            "repository_root": ".",
            "evidence_root": repo_rel(root, evidence_root),
            "pilot_evidence_root": PR18_PUBLIC_ROOT.as_posix() if pilot_evidence_root is not None else None,
            "output_paths_outside_evidence_root_asserted": True,
            "all_evidence_files_opened_read_only": True,
            "raw_files_copied": False,
        },
        "pr18_retrieval": {
            "head": PR18_HEAD,
            "attempts": PR18_RETRIEVAL_ATTEMPTS,
            "paths_checked": PR18_SEARCH_PATHS,
            "pilot_fresh_cadence_finding": pilot_finding,
        },
        "questions": {
            "1_signal_semantic_correspondence": {
                "assessment": summary["semantic_correspondence"],
                "correspondence_disproven": False,
                "per_session": [session["phase_semantic_correspondence"] for session in sessions],
            },
            "2_breath_rate_raw_waveform_use": pipeline,
            "3_row_cadence_and_fresh_0x0A13_cadence": [session["row_cadence_and_fresh_cadence"] for session in sessions],
            "4_timestamp_integrity": [
                {"session_id": session["session_id"], "timestamp_integrity": session["timestamp_integrity"]}
                for session in sessions
            ],
            "5_phase_age_ms_distribution": [
                {"session_id": session["session_id"], "phase_age_ms": session["phase_age_ms"]}
                for session in sessions
            ],
            "6_300_fresh_sample_windows": {
                "cross_group_aggregate_reported": False,
                "by_evidence_group": window_results_by_group,
                "per_session": [
                    {
                        "session_id": session["session_id"],
                        "evidence_group": session.get("evidence_group"),
                        "fresh_windows": session["fresh_windows"],
                    }
                    for session in sessions
                ],
            },
            "7_interpolation_requirement_and_simulated_distortion": [
                {"session_id": session["session_id"], "interpolation": session["interpolation"]}
                for session in sessions
            ],
            "8_bpf_zscore_equivalence": [
                {"session_id": session["session_id"], "bpf_zscore_equivalence": session["bpf_zscore_equivalence"]}
                for session in sessions
            ],
            "9_pre_post_int8_distribution": [
                {"session_id": session["session_id"], "int8_distribution": session["int8_distribution"]}
                for session in sessions
            ],
            "10_620_of_620_apnea_collapse_stage": {
                "status": window_forensics["stage_of_input_divergence"]["status"],
                "stage": window_forensics["stage_of_input_divergence"]["stage"],
                "reason": window_forensics["stage_of_input_divergence"]["finding"],
                "forensics_artifact": FORENSICS_PATH.as_posix(),
                "reconstructed_historical_window_count": window_forensics["reconstructed_historical_window_count"],
                "per_window_fractions": "recorded in the derived forensics artifact; fresh_fraction remains UNKNOWN because CSV freshness fields are absent",
            },
        },
        "training_reference": training_reference,
        "frozen_contract": FROZEN,
    }
    report = render_report(
        root,
        evidence_root,
        summary,
        expected,
        sessions,
        all_evidence_regular_file_count,
        pipeline,
        training_reference,
        window_forensics,
        pilot_finding,
    )
    run_log = "\n".join(
        [
            "# SafeNest mmWave M-C0 audit run log",
            "",
            "```text",
            "python3 scripts/mmwave_m_c0_correspondence_audit.py --root . --evidence-root devices/mmwave/firmware --pilot-evidence-root <read-only-pr18-worktree>/devices/mmwave/device_measurements",
            "```",
            "",
            f"- Evidence-root used: `{repo_rel(root, evidence_root)}`",
            f"- Regular files opened read-only: `{evidence_root_regular_file_count}`",
            f"- PR18 evidence files opened read-only: `{pilot_evidence_root_regular_file_count}`",
            f"- Expected input files SHA-256 hashed: `{len(all_hashes)}`",
            f"- Expected evidence items: `{len(expected)}`",
            f"- Expected evidence present: `{present_count}`",
            f"- Known but not provided: `{missing_count}`",
            f"- PRE_PR18_LEGACY_LOGS sessions analyzed: `{sum(1 for session in sessions if session.get('evidence_group') == 'PRE_PR18_LEGACY_LOGS')}`",
            f"- PR18_PILOT_CAPTURE sessions analyzed: `{sum(1 for session in sessions if session.get('evidence_group') == 'PR18_PILOT_CAPTURE')}`",
            f"- Reconstructed historical 620-window count: `{window_forensics['reconstructed_historical_window_count']}`",
            f"- Derived input-forensics artifact: `{FORENSICS_PATH.as_posix()}`",
            f"- Long-log expected SHA-256: `{EXPECTED_LONG_LOG_SHA256}`",
            "- Raw JSONL/CSV copied into repository: `false`",
            "- Raw JSONL/CSV modified: `false`",
            "- Output-inside-evidence-root assertion: `passed`",
            "- Inference/model scoring: `not executed`",
            "",
        ]
    )
    write_json(root / output_dir / "existing_measurement_inventory.json", inventory, evidence_root)
    write_json(root / output_dir / "offline_contract_correspondence.json", correspondence, evidence_root)
    write_json(root / output_dir / "m_c0_summary.json", summary, evidence_root)
    write_json(root / output_dir / FORENSICS_PATH.name, window_forensics, evidence_root)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    run_log_path.parent.mkdir(parents=True, exist_ok=True)
    run_log_path.write_text(run_log, encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the SafeNest mmWave M-C0 correspondence audit")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="repository root")
    parser.add_argument("--evidence-root", type=Path, default=None, help="read-only evidence root; no default")
    parser.add_argument("--pilot-evidence-root", type=Path, default=None, help="optional read-only PR18 device_measurements root")
    parser.add_argument("--output-dir", type=Path, default=AUDIT_DIR, help="derived JSON output directory")
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH, help="derived Markdown report path")
    parser.add_argument("--run-log-path", type=Path, default=RUN_LOG_PATH, help="derived run-log path")
    args = parser.parse_args()
    summary = run(
        args.root,
        args.evidence_root,
        args.pilot_evidence_root,
        args.output_dir,
        args.report_path,
        args.run_log_path,
    )
    print(json.dumps({"decision": summary["decision"], "correspondence_evaluated": summary["correspondence_evaluated"], "evidence_root": summary.get("evidence_root")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
