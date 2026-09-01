#!/usr/bin/env python3
"""One-command, dependency-free audit for CSV and JSONL evidence bundles."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_csv(directory: Path) -> dict:
    required = {"timestamp_s", "resp_phase"}
    summaries = []
    violations = {"missing_columns": 0, "nonfinite_phase": 0, "timestamp_backward": 0, "timestamp_duplicate": 0}
    max_gap = 0.0
    for path in sorted(directory.glob("*.csv")):
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            columns = set(reader.fieldnames or [])
            missing = required - columns
            if missing:
                violations["missing_columns"] += 1
            rows = 0
            previous = None
            local_max_gap = 0.0
            for row in reader:
                rows += 1
                try:
                    phase = float(row["resp_phase"])
                    timestamp = float(row["timestamp_s"])
                except (KeyError, TypeError, ValueError):
                    violations["nonfinite_phase"] += 1
                    continue
                if not math.isfinite(phase) or not math.isfinite(timestamp):
                    violations["nonfinite_phase"] += 1
                    continue
                if previous is not None:
                    gap = timestamp - previous
                    local_max_gap = max(local_max_gap, gap)
                    max_gap = max(max_gap, gap)
                    if gap < 0:
                        violations["timestamp_backward"] += 1
                    elif gap == 0:
                        violations["timestamp_duplicate"] += 1
                previous = timestamp
        summaries.append({"file": path.name, "records": rows, "sha256": sha256(path), "max_gap_s": local_max_gap})
    return {"files": len(summaries), "max_gap_s": max_gap, "violations": violations, "file_summaries": summaries}


def audit_jsonl(directory: Path) -> dict:
    files = sorted(directory.glob("*.jsonl"))
    schema_versions: dict[str, int] = {}
    physical_lines = 0
    valid_objects = 0
    invalid_lines = 0
    timestamp_backward = 0
    timestamp_duplicate = 0
    for path in files:
        previous = None
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                physical_lines += 1
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    invalid_lines += 1
                    continue
                if not isinstance(record, dict):
                    continue
                valid_objects += 1
                version = str(record.get("schema_version", "MISSING"))
                schema_versions[version] = schema_versions.get(version, 0) + 1
                timestamp = record.get("ts_monotonic_ms")
                if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool):
                    if previous is not None:
                        if timestamp < previous:
                            timestamp_backward += 1
                        elif timestamp == previous:
                            timestamp_duplicate += 1
                    previous = timestamp
    return {
        "files": len(files),
        "physical_lines": physical_lines,
        "valid_json_objects": valid_objects,
        "invalid_json_lines": invalid_lines,
        "schema_versions": schema_versions,
        "timestamp_backward": timestamp_backward,
        "timestamp_duplicate": timestamp_duplicate,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv-dir", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--strict", action="store_true", help="return nonzero for any structural exception")
    args = parser.parse_args()
    result = {"csv": audit_csv(args.csv_dir), "raw_jsonl": audit_jsonl(args.raw_dir)}
    result["status"] = "PASS" if not any(result["csv"]["violations"].values()) and not result["raw_jsonl"]["invalid_json_lines"] else "PASS_WITH_EXCEPTIONS"
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if args.strict and result["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
