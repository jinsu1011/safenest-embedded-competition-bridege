#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = PROJECT_ROOT
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from devices.mmwave.src.mr60_esp_adapter import MR60ESPAdapter


LOG_ROOT = REPO_ROOT / "devices" / "mmwave" / "firmware" / "logs" / "breath"


class TestMR60ESPAdapter(unittest.TestCase):
    @staticmethod
    def current_record(overrides: dict | None = None, **keyword_overrides) -> dict:
        record = {
            "schema_version": "1.2",
            "firmware_version": "safenest-mr60-esp/1.2.0",
            "config_hash": "b817e8bfd5e52b18275626f7b6a9bd60098ea4b108428a5aaf63600dbc987834",
        }
        record.update(overrides or {})
        record.update(keyword_overrides)
        return record

    def test_zero_is_unknown_not_apnea(self) -> None:
        adapter = MR60ESPAdapter()
        packet = adapter.process(self.current_record({
            "seq": 1, "ts_monotonic_ms": 1000,
            "uart_frame_ok": True, "checksum_ok": True,
            "checksum_errors": 0, "parse_errors": 0,
            "human_detected_raw": True, "distance_cm_raw": 90.0,
            "breath_rate_raw": 0.0, "heart_rate_raw": 0.0,
            "breath_phase": None, "phase_age_ms": 10, "heart_age_ms": 10,
            "sensor_state": "RAW",
        }))
        mmwave = packet["mmwave_mr60"]
        self.assertFalse(mmwave["valid"])
        self.assertIsNone(mmwave["breath_rpm"])
        self.assertIsNone(mmwave["apnea"])
        self.assertFalse(mmwave["apnea_verified"])

    def test_absence_clears_window_and_vitals(self) -> None:
        adapter = MR60ESPAdapter()
        adapter.estimator.timestamps.extend([0.0, 0.1])
        adapter.estimator.values.extend([0.1, 0.2])
        packet = adapter.process(self.current_record({
            "seq": 1, "ts_monotonic_ms": 1000,
            "uart_frame_ok": True, "checksum_ok": True,
            "checksum_errors": 0, "parse_errors": 0,
            "human_detected_raw": False, "distance_cm_raw": None,
            "breath_rate_raw": 18.0, "heart_rate_raw": 80.0,
            "breath_phase": 0.2, "phase_age_ms": 10, "heart_age_ms": 10,
            "sensor_state": "RAW",
        }))
        mmwave = packet["mmwave_mr60"]
        self.assertEqual(mmwave["state"], "UNKNOWN")
        self.assertIsNone(mmwave["breath_rpm"])
        self.assertIsNone(mmwave["heart_bpm"])
        self.assertEqual(mmwave["window_samples"], 0)

    def test_synthetic_15rpm_is_valid_after_60_second_warmup(self) -> None:
        adapter = MR60ESPAdapter()
        packet = None
        for index in range(620):
            timestamp_s = index / 10.0
            packet = adapter.process(self.current_record({
                "seq": index, "ts_monotonic_ms": int(timestamp_s * 1000),
                "uart_frame_ok": True, "checksum_ok": True,
                "checksum_errors": 0, "parse_errors": 0,
                "human_detected_raw": True, "distance_cm_raw": 90.0,
                "breath_rate_raw": 19.0, "heart_rate_raw": 78.0,
                "breath_phase": float(np.sin(2.0 * np.pi * 0.25 * timestamp_s)),
                "heart_phase": 0.1, "phase_age_ms": 10, "heart_age_ms": 10,
                "sensor_state": "RAW",
            }))
        self.assertIsNotNone(packet)
        mmwave = packet["mmwave_mr60"]
        self.assertEqual(mmwave["state"], "VALID")
        self.assertAlmostEqual(mmwave["breath_rpm"], 15.0, delta=0.3)
        self.assertFalse(mmwave["heart_verified"])
        self.assertLessEqual(mmwave["heart_confidence"], 0.25)

    def test_replays_paced_logs_within_one_rpm(self) -> None:
        cases = [
            (12.0, "2026-07-28_breath_paced_12rpm_explicit_v2_attempt03.jsonl"),
            (15.0, "2026-07-28_breath_paced_15rpm_explicit_full_v3.jsonl"),
            (20.0, "2026-07-28_breath_paced_20rpm_explicit_full_v2.jsonl"),
        ]
        for target, filename in cases:
            with self.subTest(target=target):
                adapter = MR60ESPAdapter(strict_provenance=False)
                estimates = []
                with (LOG_ROOT / filename).open(encoding="utf-8") as stream:
                    for line in stream:
                        record = json.loads(line)
                        if record.get("kind") != "sensor":
                            continue
                        packet = adapter.process(record)
                        value = packet["mmwave_mr60"].get("breath_rpm")
                        if value is not None:
                            estimates.append(float(value))
                self.assertTrue(estimates)
                self.assertAlmostEqual(float(np.median(estimates)), target, delta=1.0)

    def test_provenance_mismatch_is_fault_and_clears_window(self) -> None:
        cases = (
            ("schema_version", "9.9", "MMWAVE_SCHEMA_MISMATCH"),
            ("firmware_version", "safenest-mr60-esp/9.9.9", "MMWAVE_FIRMWARE_MISMATCH"),
            ("config_hash", "bad-hash", "MMWAVE_CONFIG_HASH_MISMATCH"),
        )
        for field, bad_value, expected_reason in cases:
            with self.subTest(field=field):
                adapter = MR60ESPAdapter()
                adapter.estimator.timestamps.extend([0.0, 0.1])
                adapter.estimator.values.extend([0.1, 0.2])
                record = self.current_record(
                    seq=1, ts_monotonic_ms=1000, human_detected_stable=True,
                )
                record[field] = bad_value
                packet = adapter.process(record)
                mmwave = packet["mmwave_mr60"]
                self.assertEqual(mmwave["state"], "FAULT")
                self.assertEqual(mmwave["fault_reason"], expected_reason)
                self.assertEqual(mmwave["window_samples"], 0)
                self.assertFalse(mmwave["heart_verified"])
                self.assertFalse(mmwave["apnea_verified"])

    def test_timeout_is_explicit_stale_unknown(self) -> None:
        adapter = MR60ESPAdapter()
        adapter.estimator.timestamps.extend([0.0, 0.1])
        adapter.estimator.values.extend([0.1, 0.2])
        mmwave = adapter.timeout_packet()["mmwave_mr60"]
        self.assertEqual(mmwave["state"], "UNKNOWN")
        self.assertTrue(mmwave["stale"])
        self.assertEqual(mmwave["fault_reason"], "MMWAVE_SERIAL_TIMEOUT")
        self.assertEqual(mmwave["window_samples"], 0)

if __name__ == "__main__":
    unittest.main()
