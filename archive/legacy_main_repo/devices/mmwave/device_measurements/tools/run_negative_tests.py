#!/usr/bin/env python3
"""Exercise the contract validator with intentionally bad fixtures."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "validators" / "validate_contract.py"
MANIFEST = ROOT / "fixtures" / "session_manifest.example.json"
RAW = ROOT / "fixtures" / "example.raw.jsonl"


def run_case(name: str, manifest: dict, raw_text: str, expected_exit: int,
             expected_text: str) -> dict:
    with tempfile.TemporaryDirectory(prefix="safenest-mc0-negative-") as temp:
        temp_path = Path(temp)
        manifest_path = temp_path / "manifest.json"
        raw_path = temp_path / "raw.jsonl"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        raw_path.write_text(raw_text, encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(VALIDATOR), "--manifest", str(manifest_path), "--raw-jsonl", str(raw_path), "--strict-warnings"],
            text=True, capture_output=True, check=False,
        )
    passed = completed.returncode == expected_exit and expected_text in completed.stdout
    return {"case": name, "passed": passed, "exit": completed.returncode, "matched": expected_text in completed.stdout}


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    raw_lines = RAW.read_text(encoding="utf-8").splitlines()
    backward = json.loads(raw_lines[1])
    backward["ts_monotonic_ms"] = 900
    duplicate = json.loads(raw_lines[1])
    duplicate["ts_monotonic_ms"] = 1000
    broken_manifest = json.loads(json.dumps(manifest))
    broken_manifest["privacy"]["video_collected"] = True

    results = [
        run_case("backward_timestamp", manifest, raw_lines[0] + "\n" + json.dumps(backward) + "\n", 1, "timestamp moved backwards"),
        run_case("malformed_json", manifest, raw_lines[0] + "\n{" + "\n", 1, "is not JSON"),
        run_case("strict_duplicate_timestamp", manifest, raw_lines[0] + "\n" + json.dumps(duplicate) + "\n", 1, "duplicate timestamp"),
        run_case("privacy_video_collected", broken_manifest, RAW.read_text(encoding="utf-8"), 1, "video_collected must be false"),
    ]
    print(json.dumps({"cases": results, "all_passed": all(item["passed"] for item in results)}, indent=2))
    return 0 if all(item["passed"] for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
