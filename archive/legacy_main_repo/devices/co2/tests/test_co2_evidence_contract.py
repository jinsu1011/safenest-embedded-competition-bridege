#!/usr/bin/env python3
"""실측 SCD40 로그와 공용 센서 계약의 불변식을 검증한다."""

from __future__ import annotations

import csv
import importlib.util
import math
import sys
import tempfile
import types
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


# shared 계약의 오래된 import 경로를 실제 V5 InferenceResult로 연결한다.
inference_path = REPO_ROOT / "ondevice_ai" / "inference" / "inference_result.py"
spec = importlib.util.spec_from_file_location(
    "ondevice_ai.src.inference.inference_result", inference_path
)
assert spec and spec.loader
inference_module = importlib.util.module_from_spec(spec)
sys.modules.setdefault("ondevice_ai.src", types.ModuleType("ondevice_ai.src"))
sys.modules.setdefault("ondevice_ai.src.inference", types.ModuleType("ondevice_ai.src.inference"))
sys.modules[spec.name] = inference_module
spec.loader.exec_module(inference_module)

# 이 테스트는 로그 재생 계약만 사용하므로 무거운 모델 로더는 가져오지 않는다.
co2_interpreter_module = types.ModuleType("ondevice_ai.src.inference.co2_interpreter")
co2_interpreter_module.CO2Interpreter = object
co2_interpreter_module.CO2Prediction = object
sys.modules[co2_interpreter_module.__name__] = co2_interpreter_module

from devices.co2.src.co2_adapter import CO2LogReplayAdapter
from shared.contracts.base_sensor import SensorState


FIELDS = [
    "host_timestamp",
    "host_unix_s",
    "host_monotonic_ns",
    "scenario",
    "source_url",
    "device_id",
    "seq",
    "uptime_ms",
    "co2_ppm",
    "valid",
    "sensor_state",
    "error",
    "connected",
    "fresh",
    "transport_status",
    "peer",
    "age_seconds",
    "last_received_at",
    "raw_response_json",
]


def write_log(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


class CO2EvidenceContractTest(unittest.TestCase):
    def test_valid_measured_row_returns_normal_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "measured.csv"
            write_log(
                path,
                [{"host_unix_s": "1786520647.1", "seq": "1105", "co2_ppm": "496", "valid": "True", "sensor_state": "NORMAL"}],
            )
            adapter = CO2LogReplayAdapter(path)
            self.addCleanup(adapter.close)
            self.assertTrue(adapter.connect())
            result = adapter.read()
            self.assertTrue(result.valid)
            self.assertEqual(result.state, "NORMAL")
            self.assertEqual(result.metadata["co2_ppm"], 496.0)
            self.assertEqual(adapter.health().state, SensorState.NORMAL)
            adapter.close()

    def test_disconnect_is_invalid_and_never_zero_filled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "disconnect.csv"
            write_log(
                path,
                [{"host_unix_s": "1786520648.1", "co2_ppm": "", "valid": "False", "sensor_state": "NOT_CONNECTED", "error": "ESP32_NOT_CONNECTED"}],
            )
            adapter = CO2LogReplayAdapter(path)
            self.addCleanup(adapter.close)
            self.assertTrue(adapter.connect())
            result = adapter.read()
            self.assertFalse(result.valid)
            self.assertEqual(result.state, "NOT_CONNECTED")
            self.assertEqual(result.error, "ESP32_NOT_CONNECTED")
            self.assertNotIn("co2_ppm", result.metadata)
            self.assertEqual(adapter.health().state, SensorState.NOT_CONNECTED)
            adapter.close()

    def test_non_numeric_valid_co2_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.csv"
            write_log(
                path,
                [{"host_unix_s": "1786520649.1", "co2_ppm": "not-a-number", "valid": "True", "sensor_state": "NORMAL"}],
            )
            adapter = CO2LogReplayAdapter(path)
            self.addCleanup(adapter.close)
            self.assertTrue(adapter.connect())
            result = adapter.read()
            self.assertFalse(result.valid)
            self.assertEqual(result.state, "INVALID_FORMAT")
            self.assertEqual(result.error, "INVALID_CO2_VALUE")
            adapter.close()

    def test_real_logs_if_present_obey_contract(self) -> None:
        logs_dir = REPO_ROOT / "devices" / "co2" / "firmware" / "logs"
        paths = sorted(logs_dir.glob("*.csv")) if logs_dir.exists() else []
        if not paths:
            self.skipTest("실측 CO2 CSV는 물리 측정 단계에서 생성됩니다.")
        total_rows = 0
        invalid_rows = 0
        for path in paths:
            adapter = CO2LogReplayAdapter(path)
            self.addCleanup(adapter.close)
            self.assertTrue(adapter.connect(), path)
            while True:
                result = adapter.read()
                if result.error == "END_OF_LOG":
                    break
                total_rows += 1
                self.assertTrue(math.isfinite(result.timestamp), path)
                if result.valid:
                    self.assertIn("co2_ppm", result.metadata, path)
                    self.assertGreater(result.metadata["co2_ppm"], 0.0, path)
                else:
                    invalid_rows += 1
                    self.assertTrue(result.error, path)
                    self.assertNotIn("co2_ppm", result.metadata, path)
            adapter.close()
        self.assertGreater(total_rows, 0)
        self.assertGreaterEqual(invalid_rows, 0)


if __name__ == "__main__":
    unittest.main()
