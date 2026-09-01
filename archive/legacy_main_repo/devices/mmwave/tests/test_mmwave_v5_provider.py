#!/usr/bin/env python3

from __future__ import annotations

from collections import deque
import json
from pathlib import Path
import sys
import unittest

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[3]
ONDEVICE_AI_ROOT = REPO_ROOT / "ondevice_ai"
for path in (REPO_ROOT, ONDEVICE_AI_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from devices.mmwave.src.mmwave_adapter import MMWaveSensorAdapter
from inference.mmwave_interpreter import MMWavePrediction
from integrated_node.runtime_config import load_runtime_settings, validate_provider_settings
from sensors.provider_contract import validate_provider_interface, validate_provider_result


class FakeSerial:
    def __init__(self, lines=None, error: Exception | None = None, **kwargs):
        self.lines = deque(lines or [])
        self.error = error
        self.is_open = True
        self.closed = False

    def reset_input_buffer(self):
        return None

    def readline(self):
        if self.error is not None:
            raise self.error
        return self.lines.popleft() if self.lines else b""

    def close(self):
        self.closed = True
        self.is_open = False


class FakeInterpreter:
    def __init__(self, *, fallback_used=False):
        self.fallback_used = fallback_used
        self.sha256_hash = "a" * 64
        self.sha256_matches = not fallback_used
        self.calls = 0
        self.input_info = {
            "shape": np.asarray([1, 300, 1], dtype=np.int32),
            "dtype": np.dtype(np.int8),
        }

    def predict(self, window):
        self.calls += 1
        if np.asarray(window).shape != (300,):
            raise AssertionError("provider must pass exactly 300 samples")
        return MMWavePrediction(
            class_index=0,
            class_name="NORMAL",
            confidence=0.875,
            probabilities=[0.875, 0.1, 0.025],
            latency_ms=1.25,
            model_id="mmwave_heuristic_fallback" if self.fallback_used else "mmwave_resp_int8",
            model_version="0.1.0",
            fallback_used=self.fallback_used,
            fallback_reason="TFLITE_MODEL_LOAD_ERROR" if self.fallback_used else None,
        )


def current_record(index: int, **overrides) -> dict:
    timestamp_s = index / 10.0
    record = {
        "schema_version": "1.2",
        "firmware_version": "safenest-mr60-esp/1.2.0",
        "config_hash": "b817e8bfd5e52b18275626f7b6a9bd60098ea4b108428a5aaf63600dbc987834",
        "seq": index,
        "ts_monotonic_ms": int(timestamp_s * 1000),
        "uart_frame_ok": True,
        "checksum_ok": True,
        "checksum_errors": 0,
        "parse_errors": 0,
        "human_detected_raw": True,
        "human_detected_stable": True,
        "distance_cm_raw": 90.0,
        "breath_rate_raw": 15.0,
        "heart_rate_raw": 78.0,
        "breath_phase": float(np.sin(2.0 * np.pi * 0.25 * timestamp_s)),
        "heart_phase": 0.1,
        "phase_age_ms": 10,
        "heart_age_ms": 10,
        "sensor_state": "RAW",
    }
    record.update(overrides)
    return record


def json_lines(records):
    return [(json.dumps(record) + "\n").encode() for record in records]


class TestMMWaveV5RealProvider(unittest.TestCase):
    def make_provider(self, serial_obj: FakeSerial, *, fallback_used=False):
        interpreter = FakeInterpreter(fallback_used=fallback_used)
        provider = MMWaveSensorAdapter(
            port="/dev/fake-mr60",
            serial_factory=lambda **kwargs: serial_obj,
            interpreter=interpreter,
        )
        return provider, interpreter

    def test_interface_connect_and_close(self):
        serial_obj = FakeSerial()
        provider, _ = self.make_provider(serial_obj)
        validate_provider_interface(provider, "mmwave")
        settings = load_runtime_settings(ONDEVICE_AI_ROOT).sensors["mmwave"]
        validate_provider_settings(provider, settings)
        self.assertTrue(provider.connect())
        self.assertTrue(provider.connected)
        provider.close()
        self.assertTrue(serial_obj.closed)
        self.assertFalse(provider.connected)

    def test_timeout_is_invalid_and_clears_window(self):
        serial_obj = FakeSerial()
        provider, interpreter = self.make_provider(serial_obj)
        self.assertTrue(provider.connect())
        provider.adapter.estimator.values.append(0.1)
        provider.adapter.estimator.timestamps.append(0.1)
        result = provider.read()
        self.assertFalse(result.valid)
        self.assertEqual(result.state, "UNKNOWN")
        self.assertEqual(result.error, "MMWAVE_SERIAL_TIMEOUT")
        self.assertEqual(len(provider.adapter.estimator.values), 0)
        self.assertEqual(interpreter.calls, 0)

    def test_invalid_json_and_read_failure_are_invalid(self):
        invalid_serial = FakeSerial(lines=[b"not-json\n"])
        provider, _ = self.make_provider(invalid_serial)
        provider.connect()
        invalid = provider.read()
        self.assertFalse(invalid.valid)
        self.assertEqual(invalid.error, "MMWAVE_JSON_INVALID")

        failure_serial = FakeSerial(error=OSError("serial failed"))
        provider, _ = self.make_provider(failure_serial)
        provider.connect()
        failed = provider.read()
        self.assertFalse(failed.valid)
        self.assertEqual(failed.state, "FAULT")
        self.assertEqual(failed.error, "MMWAVE_PROVIDER_READ_FAILURE")

    def test_no_presence_nan_and_large_gap_fail_closed(self):
        cases = (
            (current_record(1, human_detected_raw=False, human_detected_stable=False), "MMWAVE_PRESENCE_NOT_DETECTED"),
            (current_record(1, breath_phase=float("nan")), "MMWAVE_PHASE_INVALID"),
            (current_record(1, breath_phase=float("inf")), "MMWAVE_PHASE_INVALID"),
            (current_record(1, phase_age_ms=501), "MMWAVE_PHASE_STALE"),
        )
        for record, expected in cases:
            with self.subTest(expected=expected):
                provider, interpreter = self.make_provider(FakeSerial(lines=json_lines([record])))
                provider.connect()
                result = provider.read()
                self.assertFalse(result.valid)
                self.assertEqual(result.error, expected)
                self.assertEqual(interpreter.calls, 0)

        records = [current_record(1), current_record(10)]
        provider, interpreter = self.make_provider(FakeSerial(lines=json_lines(records)))
        provider.connect()
        warming_up = provider.read()
        self.assertFalse(warming_up.valid)
        self.assertEqual(warming_up.state, "WARMUP")
        self.assertEqual(warming_up.error, "MMWAVE_WARMUP")
        gap = provider.read()
        self.assertFalse(gap.valid)
        self.assertEqual(gap.error, "MMWAVE_STREAM_GAP_TOO_LARGE")
        self.assertEqual(interpreter.calls, 0)

    def test_real_path_shape_contract_and_result_validation(self):
        records = [current_record(index) for index in range(620)]
        provider, interpreter = self.make_provider(FakeSerial(lines=json_lines(records)))
        self.assertTrue(provider.connect())
        result = None
        for _ in records:
            result = provider.read()
        self.assertIsNotNone(result)
        self.assertTrue(result.valid)
        self.assertEqual(result.sensor_id, "mmwave")
        self.assertEqual(result.state, "NORMAL")
        self.assertEqual(result.metadata["window_shape"], [300])
        self.assertEqual(result.metadata["model_input_shape"], [1, 300, 1])
        self.assertFalse(result.metadata["fallback_used"])
        self.assertEqual(interpreter.calls, 20)
        self.assertEqual(validate_provider_result(result, "mmwave"), (True, None))

    def test_fallback_never_becomes_valid_inference(self):
        records = [current_record(index) for index in range(601)]
        provider, interpreter = self.make_provider(
            FakeSerial(lines=json_lines(records)), fallback_used=True
        )
        provider.connect()
        result = None
        for _ in records:
            result = provider.read()
        self.assertIsNotNone(result)
        self.assertFalse(result.valid)
        self.assertEqual(result.state, "UNKNOWN")
        self.assertEqual(result.error, "TFLITE_MODEL_LOAD_ERROR")
        self.assertTrue(result.metadata["fallback_used"])
        self.assertGreater(interpreter.calls, 0)
        self.assertEqual(validate_provider_result(result, "mmwave"), (True, None))


if __name__ == "__main__":
    unittest.main()
