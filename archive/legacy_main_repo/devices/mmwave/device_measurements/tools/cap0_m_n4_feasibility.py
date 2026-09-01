#!/usr/bin/env python3
"""CAP-0/CAP-2 feasibility probe: how many canonical M-N4 windows does an MR60 session yield?

Runs an MR60 raw JSONL capture through the FROZEN M-N4 canonical acceptance and
window-formation logic (RaspberryPi/Ondevice_AI/scripts/mmwave_m_n4_canonical.py,
contract MMWAVE_MR60_COMPAT_INPUT_DATASET_V1) and reports, per session:

  - telemetry cadence and seq integrity
  - derived phase_update_estimate_ms = ts_monotonic_ms - phase_age_ms
  - accepted phase-update events vs republications dropped by the 8 ms rule
  - non-overlapping 30 s window yield, with rejection reasons
  - per-window MAD alongside the producer-side sensor_state/error_code mix

Read-only. Does not modify the capture. Does not train, score, or label.

Usage:
    python3 tools/cap0_m_n4_feasibility.py <session.raw.jsonl> [...]
"""
from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

import numpy as np

# device_measurements/tools -> repo root
REPO = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(REPO / "RaspberryPi/Ondevice_AI/scripts"))
import mmwave_m_n4_canonical as C  # noqa: E402

REQUIRED = ("breath_phase", "ts_monotonic_ms", "phase_age_ms")  # contract required_live_fields


def load(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def probe(path: Path) -> dict:
    rows = load(path)
    n = len(rows)
    out: dict = {"file": path.name, "records": n}

    present = collections.Counter()
    for row in rows:
        present.update(row.keys())
    out["required_fields_complete"] = {k: present[k] == n for k in REQUIRED}
    out["fields_missing_in_some_rows"] = {k: n - v for k, v in present.items() if v != n}

    ts = np.array([r["ts_monotonic_ms"] for r in rows], dtype=np.float64)
    age = np.array([r["phase_age_ms"] for r in rows], dtype=np.float64)
    phase = np.array([r["breath_phase"] for r in rows], dtype=np.float64)
    seq = np.array([r["seq"] for r in rows], dtype=np.int64)

    d_ts = np.diff(ts)
    out["duration_s"] = round(float((ts[-1] - ts[0]) / 1000.0), 3)
    out["ts_monotonic_nondecreasing"] = bool(np.all(d_ts >= 0))
    out["telemetry_hz_median"] = round(1000.0 / float(np.median(d_ts)), 3)
    out["seq_strictly_increasing"] = bool(np.all(np.diff(seq) > 0))
    out["seq_gaps"] = int(np.sum(np.diff(seq) != 1))
    out["breath_phase_all_finite"] = bool(np.all(np.isfinite(phase)))
    out["phase_age_ms"] = {
        "median": float(np.median(age)),
        "p95": float(np.percentile(age, 95)),
        "max": float(age.max()),
        "at_or_above_kPhaseMaxAgeMs_500": int(np.sum(age >= 500)),
    }

    update_ms = ts - age
    out["phase_update_estimate_backsteps"] = int(np.sum(np.diff(update_ms) < 0))
    out["rows_per_distinct_update_estimate"] = round(n / len(np.unique(update_ms)), 4)

    t_s, x, info = C.accept_phase_events(
        ts, phase, age, production=True, timestamps_are_seconds=False
    )
    intervals = np.diff(t_s)
    out["m_n4"] = {
        "accepted_events": info["n_events"],
        "republications_dropped_8ms_rule": info["n_republications"],
        "accepted_rate_hz": round(info["n_events"] / out["duration_s"], 3),
        "accepted_interval_s": {
            "median": round(float(np.median(intervals)), 4),
            "p95": round(float(np.percentile(intervals, 95)), 4),
            "max": round(float(intervals.max()), 4),
        },
        "intervals_over_gap_floor_0.40s": int(np.sum(intervals > C.GAP_FLOOR_S)),
    }

    state = np.array([r.get("sensor_state") for r in rows])
    windows, rejected = [], collections.Counter()
    start = float(t_s[0])
    while start + C.WINDOW_SECONDS <= float(t_s[-1]):
        in_win = (update_ms / 1000.0 >= start) & (update_ms / 1000.0 < start + C.WINDOW_SECONDS)
        try:
            w = C.form_canonical_window(t_s, x, start)
            windows.append(
                {
                    "t_start_s": round(start, 3),
                    "mad": round(w.mad, 6),
                    "mad_collapsed": bool(w.collapsed),
                    "phase_events": w.n_phase_events,
                    "median_update_dt_s": round(w.median_update_dt_s, 4),
                    "producer_non_valid_fraction": round(
                        float(np.mean(state[in_win] != "VALID")), 3
                    )
                    if in_win.any()
                    else None,
                }
            )
        except C.CanonicalContractError as exc:
            rejected[str(exc)] += 1
        start += C.WINDOW_SECONDS

    out["m_n4"]["windows_accepted"] = len(windows)
    out["m_n4"]["windows_rejected"] = dict(rejected)
    out["m_n4"]["windows"] = windows
    out["producer_state_counts"] = dict(collections.Counter(state.tolist()))
    out["producer_error_code_counts"] = dict(
        collections.Counter(str(r.get("error_code")) for r in rows)
    )
    # The M-N4 contract has no amplitude gate: DEGRADED/LOW_AMPLITUDE rows are
    # accepted as long as freshness and gap rules hold. Report, do not filter.
    out["note"] = (
        "producer_non_valid_fraction is reported for the model team; "
        "M-N4 does not reject on sensor_state or breath amplitude."
    )
    return out


def main() -> int:
    paths = [Path(p) for p in sys.argv[1:]]
    if not paths:
        print(__doc__)
        return 2
    print(json.dumps([probe(p) for p in paths], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
