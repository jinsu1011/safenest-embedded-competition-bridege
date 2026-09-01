#!/usr/bin/env python3
"""Build the reproducible manifest for the MR60 logs accepted for integration."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "ondevice_ai" / "datasets" / "mmwave"
    / "mr60_20260728_manifest.json"
)

SOURCES = [
    {
        "path": "devices/mmwave/firmware/logs/baseline/2026-07-28_empty_v2_360s.jsonl",
        "condition": "empty_room",
        "duration_s": 360,
        "label": "ABSENT",
        "accepted": True,
    },
    {
        "path": "devices/mmwave/firmware/logs/baseline/2026-07-28_occupied_d09_v2_360s.jsonl",
        "condition": "one_stationary_person_front_0.8_to_1.0m",
        "duration_s": 360,
        "label": "PRESENT_STATIONARY",
        "accepted": True,
    },
    {
        "path": "devices/mmwave/firmware/logs/kpi/2026-07-28_entry_exit_20_v2.jsonl",
        "condition": "entry_still_exit_20_trials",
        "trials": 20,
        "label": "ENTRY_EXIT",
        "accepted": True,
    },
    {
        "path": "devices/mmwave/firmware/logs/breath/2026-07-28_breath_paced_12rpm_explicit_v2_attempt03.jsonl",
        "condition": "paced_breathing_front_12rpm_warmup60_measure180",
        "reference_breath_rpm": 12,
        "label": "PACED_BREATHING",
        "accepted": True,
    },
    {
        "path": "devices/mmwave/firmware/logs/breath/2026-07-28_breath_paced_15rpm_explicit_full_v3.jsonl",
        "condition": "paced_breathing_front_15rpm_warmup60_measure180",
        "reference_breath_rpm": 15,
        "label": "PACED_BREATHING",
        "accepted": True,
    },
    {
        "path": "devices/mmwave/firmware/logs/breath/2026-07-28_breath_paced_20rpm_explicit_full_v2.jsonl",
        "condition": "paced_breathing_front_20rpm_warmup60_measure180",
        "reference_breath_rpm": 20,
        "label": "PACED_BREATHING",
        "accepted": True,
    },
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest() -> dict:
    entries = []
    for source in SOURCES:
        absolute = PROJECT_ROOT / source["path"]
        if not absolute.is_file():
            raise FileNotFoundError(absolute)
        entry = dict(source)
        entry.update({"bytes": absolute.stat().st_size, "sha256": sha256(absolute)})
        entries.append(entry)
    return {
        "schema_version": "1.0",
        "dataset_id": "safenest_mr60_20260728_valid",
        "sensor": "Seeed MR60BHA2",
        "collector": "ESP-WROOM-32 UART2 GPIO16/17 at 115200 8N1",
        "privacy": "No image or audio is included; mmWave numeric telemetry only.",
        "reference_limits": {
            "breath": "Paced cue is a rate reference, not a medical reference device.",
            "heart": "No simultaneous reference device; heart output is UNVERIFIED.",
            "apnea": "Not collected and must not be inferred from 0/null/timeout.",
        },
        "excluded_data_policy": "Preflight, interrupted, and failed trials remain preserved locally but are not listed as accepted sources.",
        "sources": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_manifest(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
