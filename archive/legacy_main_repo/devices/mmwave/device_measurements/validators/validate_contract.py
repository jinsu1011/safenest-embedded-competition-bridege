#!/usr/bin/env python3
"""Small dependency-free QA checker for the M-C0 evidence contract."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path


REQUIRED_MANIFEST = {
    "schema_version",
    "status",
    "session_id",
    "subject_id",
    "operator_id",
    "start_time_utc",
    "end_time_utc",
    "sensor",
    "setup",
    "condition",
    "reference",
    "files",
    "privacy",
    "qa",
}

REQUIRED_RECORD = {
    "schema_version",
    "device_id",
    "seq",
    "ts_monotonic_ms",
    "uart_frame_ok",
    "checksum_ok",
    "human_detected_raw",
    "human_detected_stable",
    "distance_cm_raw",
    "breath_rate_raw",
    "breath_rate_filtered",
    "breath_filtered_valid",
    "breath_phase_std",
    "breath_window_ready",
    "heart_rate_raw",
    "heart_raw_valid",
    "heart_verified",
    "total_phase",
    "breath_phase",
    "heart_phase",
    "distance_std_cm",
    "firmware_version",
    "sensor_firmware_version",
    "config_hash",
    "sensor_state",
    "error_code",
}


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def validate_manifest(data: dict, errors: list[str]) -> None:
    missing = REQUIRED_MANIFEST - data.keys()
    for key in sorted(missing):
        errors.append(f"manifest missing: {key}")

    if data.get("schema_version") != "m-c0-session-1.0":
        errors.append("manifest schema_version must be m-c0-session-1.0")
    if not re.fullmatch(r"M-C0-[A-Z0-9][A-Z0-9_-]*", str(data.get("session_id", ""))):
        errors.append("manifest session_id format is invalid")
    if not re.fullmatch(r"SUBJ-[A-Z0-9][A-Z0-9_-]*", str(data.get("subject_id", ""))):
        errors.append("manifest subject_id must be pseudonymous")
    if not re.fullmatch(r"OP-[A-Z0-9][A-Z0-9_-]*", str(data.get("operator_id", ""))):
        errors.append("manifest operator_id format is invalid")

    try:
        if parse_time(data["end_time_utc"]) <= parse_time(data["start_time_utc"]):
            errors.append("manifest end_time_utc must be after start_time_utc")
    except (KeyError, TypeError, ValueError):
        errors.append("manifest timestamps must be ISO-8601 date-time values")

    files = data.get("files", {})
    if files.get("raw_immutable") is not True:
        errors.append("files.raw_immutable must be true")
    raw_files = files.get("raw_jsonl", [])
    if not isinstance(raw_files, list) or not raw_files:
        errors.append("files.raw_jsonl must contain at least one file")
    for index, item in enumerate(raw_files if isinstance(raw_files, list) else []):
        if not isinstance(item, dict):
            errors.append(f"files.raw_jsonl[{index}] must be an object")
            continue
        if not item.get("path"):
            errors.append(f"files.raw_jsonl[{index}].path is required")
        if not re.fullmatch(r"[a-fA-F0-9]{64}", str(item.get("sha256", ""))):
            errors.append(f"files.raw_jsonl[{index}].sha256 must be 64 hex characters")

    privacy = data.get("privacy", {})
    if privacy.get("identifiers_removed") is not True:
        errors.append("privacy.identifiers_removed must be true")
    if privacy.get("video_collected") is not False:
        errors.append("privacy.video_collected must be false")

    condition = data.get("condition", {})
    if condition.get("breathing_mode") not in {"normal_spontaneous", "safe_observation"}:
        errors.append("condition.breathing_mode must be a safe normal-observation value")


def validate_raw(path: Path, errors: list[str], warnings: list[str]) -> int:
    count = 0
    previous_seq = None
    previous_ts = None
    try:
        handle = path.open(encoding="utf-8")
    except OSError as exc:
        errors.append(f"raw file cannot be opened: {path}: {exc}")
        return count

    with handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            count += 1
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                errors.append(f"raw line {line_number} is not JSON: {exc.msg}")
                continue
            if not isinstance(record, dict):
                errors.append(f"raw line {line_number} is not an object")
                continue
            missing = REQUIRED_RECORD - record.keys()
            for key in sorted(missing):
                errors.append(f"raw line {line_number} missing: {key}")
            seq = record.get("seq")
            ts = record.get("ts_monotonic_ms")
            if not isinstance(seq, int) or seq < 0:
                errors.append(f"raw line {line_number} seq must be a non-negative integer")
            if not isinstance(ts, int) or ts < 0:
                errors.append(f"raw line {line_number} ts_monotonic_ms must be a non-negative integer")
            if isinstance(seq, int) and previous_seq is not None and seq < previous_seq:
                errors.append(f"raw line {line_number} seq moved backwards")
            if isinstance(ts, int) and previous_ts is not None:
                if ts < previous_ts:
                    errors.append(f"raw line {line_number} timestamp moved backwards")
                elif ts == previous_ts:
                    warnings.append(f"raw line {line_number} has duplicate timestamp")
            if isinstance(seq, int):
                previous_seq = seq
            if isinstance(ts, int):
                previous_ts = ts
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--raw-jsonl", type=Path)
    parser.add_argument("--check-files", action="store_true")
    parser.add_argument(
        "--strict-warnings",
        action="store_true",
        help="treat raw timestamp warnings as errors for formal QA",
    )
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    try:
        data = json.loads(args.manifest.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: manifest cannot be read: {exc}")
        return 1
    if not isinstance(data, dict):
        print("FAIL: manifest root must be an object")
        return 1
    validate_manifest(data, errors)

    if args.raw_jsonl:
        record_count = validate_raw(args.raw_jsonl, errors, warnings)
        print(f"raw_records={record_count}")
    elif args.check_files:
        for item in data.get("files", {}).get("raw_jsonl", []):
            candidate = args.manifest.parent.parent / item.get("path", "")
            if not candidate.is_file():
                errors.append(f"declared raw file does not exist: {candidate}")

    for warning in warnings:
        print(f"WARN: {warning}")
    if args.strict_warnings and warnings:
        errors.extend(f"strict warning: {warning}" for warning in warnings)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        print(f"FAIL: {len(errors)} error(s)")
        return 1
    print("PASS: M-C0 contract checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
