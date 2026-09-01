#!/usr/bin/env python3
"""Independently re-audit M-C0 phase freshness estimators without model use."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path
from typing import Any

try:
    from scripts.mmwave_m_c0_correspondence_audit import (
        assert_freshness_estimator_consistency,
    )
except ModuleNotFoundError:  # Direct execution puts scripts/ first on sys.path.
    from mmwave_m_c0_correspondence_audit import (
        assert_freshness_estimator_consistency,
    )


OUTPUT_PATH = Path(
    "datasets/mmwave/manifests/M-C0_correspondence_audit/freshness_estimator_reaudit.json"
)
LEGACY_RELATIVE_PATH = Path(
    "devices/mmwave/firmware/logs/final/"
    "2026-08-01_occupied_d09_v120_31min_attempt02.jsonl"
)
PILOT_PUBLIC_ROOT = Path("devices/mmwave/device_measurements/pilot")
PILOT_FILENAMES = {
    "M-C0-PILOT-DESKWORK-001": "M-C0-PILOT-DESKWORK-001.raw.jsonl",
    "M-C0-PILOT-STATIONARY-001": "M-C0-PILOT-STATIONARY-001.raw.jsonl",
}

OLD_ESTIMATOR_IMPLEMENTATION = """for previous, current in zip(age_pairs, age_pairs[1:]):
    if current[2] < previous[2]:
        reset_indices.append(current[0])
        reset_times.append(current[1])
span = age_pairs[-1][1] - age_pairs[0][1]
cadence = len(reset_times) / span if span > 0 else None"""


def round_value(value: float | None, digits: int = 9) -> float | None:
    return round(value, digits) if value is not None else None


def percentile(values: list[float], quantile: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def method_result(
    indices: list[int],
    span_s: float,
    definition: str,
    role: str,
    status: str = "CURRENT_DIAGNOSTIC",
) -> dict[str, Any]:
    return {
        "status": status,
        "transition_count": len(indices),
        "cadence_hz": round_value(len(indices) / span_s if span_s > 0 else None),
        "definition": definition,
        "role": role,
    }


def analyze_session(session_id: str, public_path: Path, local_path: Path) -> dict[str, Any]:
    rows = load_jsonl(local_path)
    timestamps_ms = [float(row["ts_monotonic_ms"]) for row in rows]
    ages_ms = [float(row["phase_age_ms"]) for row in rows]
    phases = [float(row["breath_phase"]) for row in rows]
    update_instants_ms = [
        timestamp_ms - age_ms for timestamp_ms, age_ms in zip(timestamps_ms, ages_ms)
    ]
    span_s = (timestamps_ms[-1] - timestamps_ms[0]) / 1000.0

    old_age_decrease = [
        index
        for index in range(1, len(rows))
        if ages_ms[index] < ages_ms[index - 1]
    ]
    phase_or_age_transition = [
        index
        for index in range(1, len(rows))
        if phases[index] != phases[index - 1]
        or ages_ms[index] < ages_ms[index - 1]
    ]
    age_newer_than_previous_emission = [
        index
        for index in range(1, len(rows))
        if ages_ms[index] < timestamps_ms[index] - timestamps_ms[index - 1]
    ]
    reconstructed_update_advance = [
        index
        for index in range(1, len(rows))
        if update_instants_ms[index] > update_instants_ms[index - 1]
    ]
    positive_intervals_ms = [
        timestamps_ms[index] - timestamps_ms[index - 1]
        for index in range(1, len(rows))
        if timestamps_ms[index] > timestamps_ms[index - 1]
    ]
    row_cadence_hz = (len(rows) - 1) / span_s
    reconstructed_cadence_hz = len(reconstructed_update_advance) / span_s
    regression_guards = assert_freshness_estimator_consistency(
        max_phase_age_ms=max(ages_ms),
        telemetry_interval_ms=statistics.median(positive_intervals_ms),
        fresh_cadence_hz=reconstructed_cadence_hz,
        row_cadence_hz=row_cadence_hz,
        timestamp_age_transition_count=len(reconstructed_update_advance),
        age_interval_transition_count=len(age_newer_than_previous_emission),
    )

    methods = {
        "old_phase_age_decrease_proxy": method_result(
            old_age_decrease,
            span_s,
            "count rows where phase_age_ms[i] < phase_age_ms[i-1]; divide by timestamp span",
            "systematically undercounts always-low age after genuinely new updates",
            "RETRACTED_FAULTY_ESTIMATOR",
        ),
        "phase_value_change_or_age_decrease": method_result(
            phase_or_age_transition,
            span_s,
            "count rows where breath_phase changes or phase_age_ms decreases; divide by timestamp span",
            "independent evidence lower bound; repeated quantized phase values can hide genuine updates",
        ),
        "phase_age_less_than_previous_row_interval": method_result(
            age_newer_than_previous_emission,
            span_s,
            "count rows where phase_age_ms[i] < ts[i]-ts[i-1]; divide by timestamp span",
            "independent confirmation that the stored phase update is newer than the previous telemetry emission",
        ),
        "reconstructed_update_instant_advances": method_result(
            reconstructed_update_advance,
            span_s,
            "reconstruct update_ms[i]=ts_monotonic_ms[i]-phase_age_ms[i]; count rows where update_ms[i] > update_ms[i-1]; divide by timestamp span",
            "selected estimator because it directly tests whether the stored source-update instant advances and does not depend on phase-value changes or age decreases",
        ),
    }
    return {
        "session_id": session_id,
        "source_path": public_path.as_posix(),
        "source_sha256": sha256_file(local_path),
        "record_count": len(rows),
        "timestamp_span_s": round_value(span_s),
        "telemetry_row_cadence_hz": round_value(row_cadence_hz),
        "phase_age_ms": {
            "min": round_value(min(ages_ms)),
            "median": round_value(statistics.median(ages_ms)),
            "p95": round_value(percentile(ages_ms, 0.95)),
            "max": round_value(max(ages_ms)),
        },
        "methods": methods,
        "selected_method": "reconstructed_update_instant_advances",
        "regression_guards": regression_guards,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pilot-evidence-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()
    root = args.root.resolve()
    pilot_root = args.pilot_evidence_root.resolve()
    output = (root / args.output).resolve() if not args.output.is_absolute() else args.output.resolve()
    if output.is_relative_to(pilot_root):
        raise ValueError("derived output must remain outside the read-only pilot evidence root")

    sessions = [
        analyze_session(
            "2026-08-01_occupied_d09_v120_31min_attempt02",
            LEGACY_RELATIVE_PATH,
            root / LEGACY_RELATIVE_PATH,
        )
    ]
    for session_id, filename in PILOT_FILENAMES.items():
        sessions.append(
            analyze_session(
                session_id,
                PILOT_PUBLIC_ROOT / filename,
                pilot_root / filename,
            )
        )

    payload = {
        "schema_version": "M-C0_FRESHNESS_ESTIMATOR_REAUDIT_V1",
        "old_estimator_source": "scripts/mmwave_m_c0_correspondence_audit.py::freshness_summary",
        "old_estimator_status": "RETRACTED_FAULTY_ESTIMATOR",
        "old_estimator_implementation": OLD_ESTIMATOR_IMPLEMENTATION,
        "sessions": sessions,
        "method_disagreement": {
            "status": "MATERIAL_DISAGREEMENT",
            "finding": "The old age-decrease proxy systematically undercounts always-fresh pilot rows. Phase-change-or-age-decrease is a lower bound because quantized phase values can repeat. Reconstructed update instants and the age-versus-row-interval test independently place both pilots near 10 Hz.",
            "selected_method": "reconstructed_update_instant_advances",
            "selection_reason": "It directly reconstructs the source-update instant from two recorded fields and detects an advancing update even when age does not decrease and the phase value repeats.",
            "no_methods_averaged": True,
        },
        "execution": {
            "model_invoked": False,
            "inference_executed": False,
            "raw_files_modified": False,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": args.output.as_posix(), "sessions": len(sessions)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
