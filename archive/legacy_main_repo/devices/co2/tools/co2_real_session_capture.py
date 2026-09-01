#!/usr/bin/env python3
"""Capture a REAL SCD40 CO2 validation session through the V5 provider.

One process owns the serial port. Every raw line is tee'd to disk exactly as
received, and the same lines drive the production CO2 provider inside the V5
node, so the raw evidence and the AI evidence come from one physical stream.

Nothing here synthesizes, substitutes or back-fills a sensor value.

Example::

    python3 devices/co2/tools/co2_real_session_capture.py \
        --port /dev/cu.usbserial-110 \
        --stabilization-sec 70 --qualified-sec 300 \
        --output-dir devices/co2/validation_results/<timestamp>_real_co2
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import subprocess
import time
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
ONDEVICE_AI_ROOT = REPO_ROOT / "ondevice_ai"
for path in (REPO_ROOT, ONDEVICE_AI_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from devices.co2.src.co2_serial_adapter import CO2SerialProvider  # noqa: E402
from integrated_node.run_node import SafeNestIntegratedNode  # noqa: E402
from sensors.provider_contract import validate_provider_result  # noqa: E402


class TeeSerial:
    """Wraps a real serial object and mirrors every received line to disk."""

    def __init__(self, inner, sink, session_start: float):
        self._inner = inner
        self._sink = sink
        self._session_start = session_start
        self.raw_line_count = 0

    @property
    def is_open(self):
        return getattr(self._inner, "is_open", True)

    @property
    def in_waiting(self):
        return getattr(self._inner, "in_waiting", 0)

    def reset_input_buffer(self):
        return self._inner.reset_input_buffer()

    def readline(self):
        raw = self._inner.readline()
        if raw:
            self.raw_line_count += 1
            self._sink.write(
                json.dumps(
                    {
                        "host_recv_unix": time.time(),
                        "host_elapsed_sec": round(time.time() - self._session_start, 4),
                        "raw": raw.decode("utf-8", errors="replace").rstrip("\r\n"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            self._sink.flush()
        return raw

    def close(self):
        return self._inner.close()


def git_info() -> dict:
    def run(*args):
        try:
            return subprocess.run(
                ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=True
            ).stdout.strip()
        except Exception:
            return None

    return {
        "branch": run("branch", "--show-current"),
        "head": run("rev-parse", "HEAD"),
        "dirty": run("status", "--short"),
    }


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def summarize(values):
    if not values:
        return None
    return {
        "count": len(values),
        "mean": statistics.fmean(values),
        "p50": percentile(values, 0.50),
        "p95": percentile(values, 0.95),
        "max": max(values),
        "min": min(values),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--baudrate", type=int, default=115200)
    parser.add_argument(
        "--stabilization-sec",
        type=float,
        default=70.0,
        help="SCD40 physical stabilization window; results before this are NOT qualified",
    )
    parser.add_argument("--qualified-sec", type=float, default=300.0)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()

    output_dir = args.output_dir
    if output_dir.exists() and any(output_dir.iterdir()):
        print(f"refusing to overwrite existing evidence: {output_dir}", file=sys.stderr)
        return 2
    output_dir.mkdir(parents=True, exist_ok=True)

    import serial  # imported here so the failure mode is explicit

    session_start = time.time()
    raw_sink = (output_dir / "raw_serial.jsonl").open("w", encoding="utf-8")
    ai_sink = (output_dir / "ai_results.jsonl").open("w", encoding="utf-8")

    tee_holder = {}

    def serial_factory(**kwargs):
        inner = serial.Serial(**kwargs)
        tee = TeeSerial(inner, raw_sink, session_start)
        tee_holder["tee"] = tee
        return tee

    provider = CO2SerialProvider(
        port=args.port,
        baudrate=args.baudrate,
        serial_factory=serial_factory,
    )
    node = SafeNestIntegratedNode(mode="real", sensors={"co2": provider})
    node.start()

    reads: list[dict] = []
    total_sec = args.stabilization_sec + args.qualified_sec
    deadline = session_start + total_sec
    try:
        while time.time() < deadline:
            read_started = time.perf_counter()
            output = node.step()
            end_to_end_ms = (time.perf_counter() - read_started) * 1000.0
            result = provider.last_result
            elapsed = time.time() - session_start
            qualified = elapsed >= args.stabilization_sec
            contract_valid, contract_error = (
                validate_provider_result(result, "co2") if result is not None else (False, "NO_RESULT")
            )
            node_co2 = output.sensors.get("co2")
            record = {
                "host_elapsed_sec": round(elapsed, 4),
                "qualified": qualified,
                "phase": "QUALIFIED" if qualified else "SCD40_STABILIZATION",
                "node_end_to_end_ms": end_to_end_ms,
                # What the V5 node actually ADOPTED after its own contract and
                # timeout checks, as opposed to what the provider returned.
                "node_adopted_co2": node_co2,
                "v5_contract_valid": contract_valid,
                "v5_contract_error": contract_error,
                "node_system_health": output.system_health,
                "co2": result.to_dict() if result is not None else None,
            }
            reads.append(record)
            ai_sink.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
            ai_sink.flush()
            remaining = int(deadline - time.time())
            print(
                f"[{int(elapsed):4d}s {'QUAL' if qualified else 'WARM'}] "
                f"valid={result.valid if result else None} "
                f"state={result.state if result else None} "
                f"err={result.error if result else None} "
                f"ppm={result.metadata.get('co2_ppm') if result else None} "
                f"rh={result.metadata.get('humidity_pct') if result else None} "
                f"slope={result.metadata.get('co2_slope_ppm_min') if result else None} "
                f"(-{remaining}s)",
                file=sys.stderr,
                flush=True,
            )
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
    finally:
        node.shutdown()
        ai_sink.close()
        raw_sink.close()

    tee = tee_holder.get("tee")
    metadata = {
        "label": "REAL SCD40 CO2 session — REAL SENSOR EVIDENCE",
        "session_start_unix": session_start,
        "session_end_unix": time.time(),
        "session_duration_sec": time.time() - session_start,
        "stabilization_sec": args.stabilization_sec,
        "qualified_window_sec": args.qualified_sec,
        "port": args.port,
        "baudrate": args.baudrate,
        "host": {
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "git": git_info(),
        "raw_line_count": tee.raw_line_count if tee else 0,
        "model": {
            "path": str(provider.production.interpreter.model_path.relative_to(REPO_ROOT)),
            "model_id": provider.production.interpreter.model_meta["model_id"],
            "version": provider.production.interpreter.model_meta["version"],
            "status": provider.production.interpreter.model_meta["status"],
            "sha256_actual": provider.interpreter.sha256_hash,
            "sha256_expected": provider.production.interpreter.model_meta["sha256"],
            "sha256_matches": provider.interpreter.sha256_matches,
        },
        "provider_runtime_settings": provider.runtime_settings,
        "required_history_sec": provider.required_history_sec,
        "physical_sample_count": provider.physical_sample_count,
        "duplicate_line_count": provider.duplicate_line_count,
        "tflite_invocations": provider.tflite_invocations,
    }
    (output_dir / "session_metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    qualified = [r for r in reads if r["qualified"]]
    valid = [r for r in qualified if r["co2"] and r["co2"]["valid"]]
    invalid = [r for r in qualified if r["co2"] and not r["co2"]["valid"]]
    error_histogram: dict[str, int] = {}
    for record in invalid:
        code = record["co2"]["error"] or "UNKNOWN"
        error_histogram[code] = error_histogram.get(code, 0) + 1

    physical_ts = []
    for record in valid:
        ts = record["co2"]["metadata"].get("co2_sample_ts_ms")
        if ts is not None and (not physical_ts or ts != physical_ts[-1]):
            physical_ts.append(ts)
    intervals = [
        (b - a) / 1000.0 for a, b in zip(physical_ts, physical_ts[1:])
    ]

    analysis = {
        "note": "REAL SENSOR EVIDENCE — qualified window only (post-stabilization)",
        "reads_total": len(reads),
        "reads_qualified": len(qualified),
        "reads_valid": len(valid),
        "reads_invalid": len(invalid),
        "invalid_error_histogram": error_histogram,
        "distinct_physical_samples_inferred": len(physical_ts),
        "physical_sample_interval_sec": summarize(intervals),
        "physical_timestamp_monotonic": all(b > a for a, b in zip(physical_ts, physical_ts[1:])),
        "tflite_invocations_total": provider.tflite_invocations,
        "fallback_count": sum(
            1 for r in valid if r["co2"]["metadata"].get("fallback_used")
        ),
        "tflite_invoke_latency_ms": summarize(
            [r["co2"]["metadata"]["inference_latency_ms"] for r in valid]
        ),
        "provider_read_latency_ms": summarize([r["co2"]["latency_ms"] for r in valid]),
        "node_end_to_end_ms": summarize([r["node_end_to_end_ms"] for r in valid]),
        "co2_ppm": summarize([r["co2"]["metadata"]["co2_ppm"] for r in valid]),
        "humidity_pct": summarize([r["co2"]["metadata"]["humidity_pct"] for r in valid]),
        "temperature_c": summarize([r["co2"]["metadata"]["temperature_c"] for r in valid]),
        "co2_slope_ppm_min": summarize(
            [r["co2"]["metadata"]["co2_slope_ppm_min"] for r in valid]
        ),
        "v5_contract_failures": [
            r["v5_contract_error"] for r in qualified if not r["v5_contract_valid"]
        ],
        # Proof that the node adopted the provider result rather than replacing
        # it with a PROVIDER_* error (timeout, contract violation, exception).
        "node_adopted_valid_count": sum(
            1
            for r in qualified
            if r.get("node_adopted_co2") and r["node_adopted_co2"].get("valid")
        ),
        "node_adopted_error_histogram": {
            code: sum(
                1
                for r in qualified
                if r.get("node_adopted_co2")
                and not r["node_adopted_co2"].get("valid")
                and (r["node_adopted_co2"].get("error") or "UNKNOWN") == code
            )
            for code in {
                (r["node_adopted_co2"].get("error") or "UNKNOWN")
                for r in qualified
                if r.get("node_adopted_co2") and not r["node_adopted_co2"].get("valid")
            }
        },
        "node_replaced_provider_result_count": sum(
            1
            for r in qualified
            if r["co2"]
            and r["co2"]["valid"]
            and r.get("node_adopted_co2")
            and not r["node_adopted_co2"].get("valid")
        ),
        "non_telemetry_line_count": provider.non_telemetry_line_count,
        "sample_feature_vectors": [
            {
                "host_elapsed_sec": r["host_elapsed_sec"],
                "co2_sample_seq": r["co2"]["metadata"]["co2_sample_seq"],
                "co2_sample_ts_ms": r["co2"]["metadata"]["co2_sample_ts_ms"],
                "feature_order": r["co2"]["metadata"]["feature_order"],
                "feature_vector": r["co2"]["metadata"]["feature_vector"],
                "model_class": r["co2"]["metadata"]["class_name"],
                "model_confidence": r["co2"]["confidence"],
                "probabilities": r["co2"]["metadata"]["probabilities"],
                "provider_score": r["co2"]["score"],
                "provider_state": r["co2"]["state"],
            }
            for r in valid[:10]
        ],
    }
    (output_dir / "analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
