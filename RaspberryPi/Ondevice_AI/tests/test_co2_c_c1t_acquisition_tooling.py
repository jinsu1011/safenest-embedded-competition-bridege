from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from scripts.capture_co2_c_c1t_session import (
    CaptureSession,
    _fixture_observations,
    load_context,
    validate_session_bundle,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = ROOT / "datasets/co2/manifests/c_c1t_acquisition_tooling/fixtures"


def run_fixture(name: str, temp_root: Path, session_id: str) -> tuple[Path, dict]:
    session = CaptureSession(
        output_root=temp_root,
        operator_id="codex",
        location_id="fixture-room",
        scenario_id="VACANT_STABLE",
        ground_truth_label="VACANT",
        ground_truth_source="CONTROLLED_EMPTY_ROOM",
        session_id=session_id,
        dry_run=True,
        start_time=datetime(2026, 8, 15, tzinfo=timezone.utc),
    )
    for payload, captured_at, monotonic, raw_text, source_error in _fixture_observations(
        FIXTURE_ROOT / name
    ):
        session.process_observation(
            payload,
            captured_at=captured_at,
            logger_monotonic_ns=monotonic,
            source_payload_text=raw_text,
            source_error=source_error,
        )
    session.finalize()
    return session.bundle_dir, validate_session_bundle(session.bundle_dir, load_context())


class Cc1tAcquisitionToolingTests(unittest.TestCase):
    def test_valid_fixture_distinguishes_fresh_and_cached_events(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle, result = run_fixture(
                "valid_session_input.jsonl",
                Path(directory),
                "CO2C1R-20260815-CODEX-S001",
            )
            self.assertEqual(result["status"], "PASS", result)
            self.assertEqual(result["counts"]["fresh_events"], 2)
            self.assertEqual(result["counts"]["cached_retransmissions"], 1)
            raw_rows = [
                json.loads(line)
                for line in (bundle / "raw_measurements.jsonl").read_text().splitlines()
            ]
            self.assertEqual(
                [row["sensor_measurement_freshness"] for row in raw_rows],
                ["FRESH_EVENT", "CACHED_RETRANSMISSION", "FRESH_EVENT"],
            )
            self.assertEqual(raw_rows[0]["ground_truth_label"], "VACANT")
            self.assertNotIn("CO2_slope", raw_rows[0])

    def test_missing_event_marker_is_preserved_and_blocks_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle, result = run_fixture(
                "missing_event_marker.jsonl",
                Path(directory),
                "CO2C1R-20260815-CODEX-S002",
            )
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("no verified fresh" in error for error in result["errors"]))
            failures = (bundle / "failure_events.jsonl").read_text().splitlines()
            self.assertEqual(len(failures), 1)

    def test_transport_failure_is_recorded_without_synthetic_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            bundle, result = run_fixture(
                "transport_failure.jsonl",
                Path(directory),
                "CO2C1R-20260815-CODEX-S003",
            )
            self.assertEqual(result["status"], "FAIL")
            row = json.loads((bundle / "raw_measurements.jsonl").read_text())
            self.assertIsNone(row["raw_co2_ppm"])
            self.assertEqual(row["sensor_measurement_freshness"], "TRANSPORT_UNAVAILABLE")
            self.assertEqual(row["transport_freshness"], "UNAVAILABLE")

    def test_decreasing_event_id_requires_new_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            session = CaptureSession(
                output_root=Path(directory),
                operator_id="codex",
                location_id="fixture-room",
                scenario_id="VACANT_STABLE",
                ground_truth_label="VACANT",
                ground_truth_source="CONTROLLED_EMPTY_ROOM",
                session_id="CO2C1R-20260815-CODEX-S004",
                dry_run=True,
                start_time=datetime(2026, 8, 15, tzinfo=timezone.utc),
            )
            base = {
                "sensors": {
                    "device_id": "esp32",
                    "co2_ppm": 600,
                    "co2_measurement_monotonic_ms": 100,
                    "co2_measurement_event_valid": True,
                    "valid": {"co2": True},
                    "connected": True,
                    "fresh": True,
                    "status": "live",
                }
            }
            first = json.loads(json.dumps(base))
            first["sensors"]["co2_measurement_event_id"] = 2
            second = json.loads(json.dumps(base))
            second["sensors"]["co2_measurement_event_id"] = 1
            session.process_observation(first, logger_monotonic_ns=1)
            session.process_observation(second, logger_monotonic_ns=2)
            session.finalize()
            result = validate_session_bundle(session.bundle_dir, load_context())
            self.assertEqual(result["status"], "FAIL")
            self.assertTrue(any("counter reset" in error for error in result["errors"]))
            self.assertEqual(len((session.bundle_dir / "deviation_events.jsonl").read_text().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
