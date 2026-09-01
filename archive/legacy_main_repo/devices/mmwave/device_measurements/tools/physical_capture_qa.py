#!/usr/bin/env python3
"""Compute machine-readable QA for one immutable MR60 physical JSONL capture."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path


NUMERIC_FIELDS = (
    "distance_cm_raw",
    "breath_rate_raw",
    "breath_rate_filtered",
    "breath_phase_std",
    "heart_rate_raw",
    "total_phase",
    "breath_phase",
    "heart_phase",
    "distance_std_cm",
)

COVERAGE_FIELDS = (
    "human_detected_raw",
    "human_detected_stable",
    *NUMERIC_FIELDS,
    "sensor_firmware_version",
)

PHASE_MAX_AGE_MS = 500
PHASE_MAX_AGE_SOURCE = "devices/mmwave/firmware/include/mmwave_config.h:kPhaseMaxAgeMs"

RAW_RECORD_SCHEMA = Path(__file__).resolve().parents[1] / "schemas" / "raw_record.schema.json"


def summarize_schema_conformance(records: list[dict]) -> dict:
    """Flag record keys that appear on only some records.

    The schema sets additionalProperties=true and the current firmware emits
    several fields it does not declare, so an undeclared key is not by itself a
    defect. A key carried by only a subset of records is: a serial byte dropout
    can fuse two adjacent JSON keys into one novel key (observed once as
    "breath_filtered_v_std" in M-C0-PILOT-STATIONARY-001). That line still parses,
    so malformed_line_count never sees it; only key frequency does.
    """
    schema = json.loads(RAW_RECORD_SCHEMA.read_text())
    declared = set(schema.get("properties", {}))
    required = set(schema.get("required", []))
    total = len(records)

    key_counts: Counter = Counter()
    for record in records:
        key_counts.update(record.keys())

    consistent = {key for key, count in key_counts.items() if count == total}
    inconsistent = {
        key: count for key, count in sorted(key_counts.items()) if count < total
    }
    missing_required = {
        key: total - key_counts.get(key, 0)
        for key in sorted(required)
        if key_counts.get(key, 0) < total
    }

    # The modal key signature is what a healthy record looks like in this capture.
    signatures: Counter = Counter(frozenset(record) for record in records)
    modal_signature = signatures.most_common(1)[0][0] if signatures else frozenset()
    anomalous = [
        index
        for index, record in enumerate(records, start=1)
        if frozenset(record) != modal_signature
    ]

    return {
        "schema": RAW_RECORD_SCHEMA.name,
        "record_count": total,
        "undeclared_keys_on_every_record": sorted(consistent - declared),
        "inconsistent_key_counts": inconsistent,
        "missing_required_key_counts": missing_required,
        "anomalous_record_indices": anomalous[:20],
        "anomalous_record_count": len(anomalous),
        "pass": not inconsistent and not missing_required,
        "note": (
            "Undeclared keys present on every record are current-firmware fields the "
            "schema has not declared; informational only. A key present on some records "
            "but not others indicates a truncated serial line that still parsed as JSON."
        ),
    }


def finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def summarize_phase_age(records: list[dict]) -> dict:
    values: list[float] = []
    missing_or_null = 0
    invalid = 0
    for record in records:
        value = record.get("phase_age_ms")
        if value is None:
            missing_or_null += 1
        elif finite(value) and float(value) >= 0:
            values.append(float(value))
        else:
            invalid += 1
    return {
        "count": len(values),
        "missing_or_null": missing_or_null,
        "invalid": invalid,
        "min_ms": rounded(min(values)) if values else None,
        "median_ms": rounded(statistics.median(values)) if values else None,
        "p95_ms": rounded(percentile(values, 0.95)),
        "max_ms": rounded(max(values)) if values else None,
        "threshold_classification": "PRODUCER_VALIDITY_THRESHOLD_DEFINED",
        "threshold_ms": PHASE_MAX_AGE_MS,
        "threshold_source": PHASE_MAX_AGE_SOURCE,
        "at_or_above_threshold": sum(value >= PHASE_MAX_AGE_MS for value in values),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-jsonl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    records: list[dict] = []
    malformed_lines: list[int] = []
    with args.raw_jsonl.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                malformed_lines.append(line_number)
                continue
            if not isinstance(record, dict):
                malformed_lines.append(line_number)
                continue
            records.append(record)

    intervals_ms: list[float] = []
    sequence_gap_events = 0
    missing_sequences = 0
    sequence_duplicates = 0
    sequence_backwards = 0
    timestamp_duplicates = 0
    timestamp_backwards = 0
    previous_seq = None
    previous_ts = None
    for record in records:
        seq = record.get("seq")
        ts = record.get("ts_monotonic_ms")
        if isinstance(seq, int) and not isinstance(seq, bool) and previous_seq is not None:
            delta = seq - previous_seq
            if delta > 1:
                sequence_gap_events += 1
                missing_sequences += delta - 1
            elif delta == 0:
                sequence_duplicates += 1
            elif delta < 0:
                sequence_backwards += 1
        if isinstance(ts, int) and not isinstance(ts, bool) and previous_ts is not None:
            delta_ms = float(ts - previous_ts)
            if delta_ms > 0:
                intervals_ms.append(delta_ms)
            elif delta_ms == 0:
                timestamp_duplicates += 1
            else:
                timestamp_backwards += 1
        if isinstance(seq, int) and not isinstance(seq, bool):
            previous_seq = seq
        if isinstance(ts, int) and not isinstance(ts, bool):
            previous_ts = ts

    mean_interval = statistics.fmean(intervals_ms) if intervals_ms else None
    duration_ms = (
        records[-1].get("ts_monotonic_ms") - records[0].get("ts_monotonic_ms")
        if len(records) >= 2
        and isinstance(records[0].get("ts_monotonic_ms"), int)
        and isinstance(records[-1].get("ts_monotonic_ms"), int)
        else None
    )

    coverage = {}
    for field in COVERAGE_FIELDS:
        populated = sum(record.get(field) is not None for record in records)
        coverage[field] = {
            "populated": populated,
            "ratio": rounded(populated / len(records)) if records else None,
        }

    numeric_ranges = {}
    for field in NUMERIC_FIELDS:
        values = [float(record[field]) for record in records if finite(record.get(field))]
        numeric_ranges[field] = {
            "count": len(values),
            "min": rounded(min(values)) if values else None,
            "max": rounded(max(values)) if values else None,
            "mean": rounded(statistics.fmean(values)) if values else None,
            "median": rounded(statistics.median(values)) if values else None,
        }

    state_counts = Counter(str(record.get("sensor_state")) for record in records)
    error_counts = Counter(str(record.get("error_code")) for record in records)
    uart_bad = sum(record.get("uart_frame_ok") is not True for record in records)
    checksum_bad = sum(record.get("checksum_ok") is not True for record in records)
    heart_verified_true = sum(record.get("heart_verified") is True for record in records)

    schema_conformance = summarize_schema_conformance(records)

    stream_integrity_pass = not any((
        malformed_lines,
        not schema_conformance["pass"],
        sequence_gap_events,
        sequence_duplicates,
        sequence_backwards,
        timestamp_duplicates,
        timestamp_backwards,
        uart_bad,
        checksum_bad,
    ))

    result = {
        "qa_schema_version": "m-c0-physical-qa-1.2",
        "raw": {
            "path": args.raw_jsonl.as_posix(),
            "sha256": hashlib.sha256(args.raw_jsonl.read_bytes()).hexdigest(),
            "byte_count": args.raw_jsonl.stat().st_size,
            "physical_lines": len(records) + len(malformed_lines),
            "valid_json_records": len(records),
            "malformed_line_count": len(malformed_lines),
            "malformed_lines": malformed_lines,
        },
        "identity": {
            "device_ids": sorted({str(record.get("device_id")) for record in records}),
            "firmware_versions": sorted({str(record.get("firmware_version")) for record in records}),
            "sensor_firmware_versions": sorted({str(record.get("sensor_firmware_version")) for record in records}),
            "config_hashes": sorted({str(record.get("config_hash")) for record in records}),
        },
        "sequence": {
            "first": records[0].get("seq") if records else None,
            "last": records[-1].get("seq") if records else None,
            "gap_events": sequence_gap_events,
            "missing_sequences": missing_sequences,
            "duplicates": sequence_duplicates,
            "backwards": sequence_backwards,
        },
        "timing": {
            "telemetry_row_count": len(records),
            "telemetry_interval_count": len(intervals_ms),
            "first_ts_monotonic_ms": records[0].get("ts_monotonic_ms") if records else None,
            "last_ts_monotonic_ms": records[-1].get("ts_monotonic_ms") if records else None,
            "duration_ms": duration_ms,
            "effective_cadence_hz": rounded(1000.0 / mean_interval) if mean_interval else None,
            "minimum_interval_ms": rounded(min(intervals_ms)) if intervals_ms else None,
            "mean_interval_ms": rounded(mean_interval),
            "median_interval_ms": rounded(statistics.median(intervals_ms)) if intervals_ms else None,
            "p95_interval_ms": rounded(percentile(intervals_ms, 0.95)),
            "jitter_pstdev_ms": rounded(statistics.pstdev(intervals_ms)) if intervals_ms else None,
            "maximum_gap_ms": rounded(max(intervals_ms)) if intervals_ms else None,
            "gap_over_500ms": sum(value > 500.0 for value in intervals_ms),
            "duplicate_timestamps": timestamp_duplicates,
            "backward_timestamps": timestamp_backwards,
            "nominal_30s_windows": math.floor(duration_ms / 30000) if duration_ms is not None else 0,
        },
        "freshness": {
            "phase_age_ms": summarize_phase_age(records),
            "telemetry_row_cadence_is_fresh_phase_cadence": False,
            "exact_phase_frame_arrival_identity_available": False,
            "fresh_phase_cadence_status": "FRESH_PHASE_CADENCE_NOT_YET_FULLY_VERIFIED",
            "repeated_identical_breath_phase_is_sufficient_stale_proof": False,
            "limitation": "phase_age_ms is staleness evidence, not an exact log of every 0x0A13 frame arrival.",
        },
        "communication": {
            "uart_bad": uart_bad,
            "checksum_bad": checksum_bad,
        },
        "coverage": coverage,
        "schema_conformance": schema_conformance,
        "numeric_ranges": numeric_ranges,
        "sensor_state_counts": dict(sorted(state_counts.items())),
        "error_code_counts": dict(sorted(error_counts.items())),
        "heart_verified_true": heart_verified_true,
        "stream_integrity_pass": stream_integrity_pass,
        "claim_boundaries": {
            "physical_signal_captured": bool(records),
            "respiration_accuracy_verified": False,
            "heart_accuracy_verified": False,
            "clinical_apnea_validated": False,
            "deployment_ready": False,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if stream_integrity_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
