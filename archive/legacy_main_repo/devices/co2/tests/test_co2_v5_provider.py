#!/usr/bin/env python3
"""CO2 V5 USB-serial provider tests.

SYNTHETIC TEST — NOT REAL SENSOR EVIDENCE.

Every telemetry record below is a hand-written fixture used to verify software
behaviour (parsing, physical-sample deduplication, history/slope, fail-closed
gates, TFLite wiring, V5 contract).  The actual INT8 TFLite model IS invoked,
but only on synthetic input, so nothing here may be reported as real-sensor or
real-AI validation evidence.
"""

from __future__ import annotations

from collections import deque
import json
from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
ONDEVICE_AI_ROOT = REPO_ROOT / "ondevice_ai"
for path in (REPO_ROOT, ONDEVICE_AI_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from devices.co2.src.co2_serial_adapter import (  # noqa: E402
    SERIAL_SCHEMA,
    CO2SerialProvider,
    result_to_json,
)
from inference.inference_result import InferenceResult  # noqa: E402
from integrated_node.run_node import SafeNestIntegratedNode  # noqa: E402
from sensors.provider_contract import (  # noqa: E402
    validate_provider_interface,
    validate_provider_result,
)


# Fixture values are deliberately different from the legacy placeholder triple
# (650 ppm / 45 % / 23.5 C) so a placeholder leak would be visible.
FIXTURE_CO2_PPM = 812.0
FIXTURE_HUMIDITY_PCT = 41.375
FIXTURE_TEMPERATURE_C = 24.625


class FakeSerial:
    """Minimal pyserial stand-in. Returns queued lines, then read timeouts."""

    def __init__(self, lines=None, error: Exception | None = None, **kwargs):
        self.lines = deque(lines or [])
        self.error = error
        self.is_open = True
        self.closed = False
        self.kwargs = kwargs

    @property
    def in_waiting(self) -> int:
        return sum(len(line) for line in self.lines)

    def reset_input_buffer(self):
        return None

    def readline(self):
        if self.error is not None:
            raise self.error
        return self.lines.popleft() if self.lines else b""

    def close(self):
        self.closed = True
        self.is_open = False


def serial_line(
    *,
    sample_seq: int,
    sample_ts_ms: int,
    seq: int | None = None,
    co2_ppm: object = FIXTURE_CO2_PPM,
    humidity_pct: object = FIXTURE_HUMIDITY_PCT,
    temperature_c: object = FIXTURE_TEMPERATURE_C,
    co2_valid: bool = True,
    co2_error: object = None,
    age_ms: object = 250,
    schema: str = SERIAL_SCHEMA,
    raw: str | None = None,
    **overrides,
) -> bytes:
    """Build one synthetic `safenest.co2.serial.v1` line."""

    if raw is not None:
        return raw.encode("utf-8")
    record = {
        "schema": schema,
        "device_id": "esp32-01",
        "firmware_version": "safenest-integrated-esp/1.0.0",
        "seq": sample_seq if seq is None else seq,
        "ts_monotonic_ms": sample_ts_ms + 100,
        "co2_ppm": co2_ppm,
        "humidity_pct": humidity_pct,
        "temperature_c": temperature_c,
        "co2_valid": co2_valid,
        "co2_error": co2_error,
        "co2_sample_seq": sample_seq,
        "co2_sample_ts_ms": sample_ts_ms,
        "co2_sample_age_ms": age_ms,
    }
    record.update(overrides)
    return (json.dumps(record) + "\n").encode("utf-8")


def build_provider(lines, **kwargs) -> CO2SerialProvider:
    fake = FakeSerial(lines)
    provider = CO2SerialProvider(
        port="/dev/fake-co2",
        serial_factory=lambda **_: fake,
        **kwargs,
    )
    provider._fake_serial = fake  # test handle only
    return provider


def connected_provider(lines, **kwargs) -> CO2SerialProvider:
    provider = build_provider(lines, **kwargs)
    assert provider.connect() is True
    return provider


class TestSerialSchemaParser(unittest.TestCase):
    """SYNTHETIC TEST — NOT REAL SENSOR EVIDENCE."""

    def setUp(self):
        self.provider = build_provider([])

    def test_valid_record_parses(self):
        record, error = self.provider.parse_line(
            serial_line(sample_seq=1, sample_ts_ms=5000).decode()
        )
        self.assertIsNone(error)
        self.assertEqual(record["schema"], SERIAL_SCHEMA)
        self.assertEqual(record["co2_ppm"], FIXTURE_CO2_PPM)

    def test_malformed_json_rejected(self):
        record, error = self.provider.parse_line('{"schema": "safenest.co2')
        self.assertIsNone(record)
        self.assertEqual(error, "CO2_MALFORMED_JSON")

    def test_wrong_schema_rejected(self):
        record, error = self.provider.parse_line(
            serial_line(sample_seq=1, sample_ts_ms=5000, schema="safenest.telemetry.v1").decode()
        )
        self.assertIsNone(record)
        self.assertEqual(error, "CO2_SCHEMA_MISMATCH")

    def test_mmwave_line_rejected(self):
        """The mmWave firmware's schema 1.2 line must never be accepted."""
        record, error = self.provider.parse_line(
            '{"schema_version":"1.2","device_id":"safenest-node-01","seq":3,'
            '"breath_rate_raw":13.0,"sensor_state":"WARMUP"}'
        )
        self.assertIsNone(record)
        self.assertEqual(error, "CO2_SCHEMA_MISMATCH")

    def test_firmware_health_log_line_is_skipped_not_a_fault(self):
        """The firmware's human-readable log shares the same USB serial."""
        record, error = self.provider.parse_line(
            "[health] wifi=down rpi=192.168.1.44 resp=14.0 heart=85.0 co2=1314 pir=0"
        )
        self.assertIsNone(record)
        self.assertEqual(error, "CO2_SERIAL_NON_TELEMETRY_LINE")

    def test_health_line_does_not_break_a_valid_read(self):
        provider = connected_provider(
            [
                serial_line(sample_seq=1, sample_ts_ms=0),
                b"[health] wifi=down co2=812 pir=0 free_heap=163532\n",
                b"SafeNest ESP32 sensor node starting\n",
                serial_line(sample_seq=2, sample_ts_ms=60000),
            ]
        )
        result = provider.read()
        self.assertTrue(result.valid, result.error)
        self.assertEqual(provider.non_telemetry_line_count, 2)
        self.assertEqual(provider.physical_sample_count, 2)

    def test_missing_field_rejected(self):
        line = json.dumps(
            {"schema": SERIAL_SCHEMA, "co2_ppm": 800.0, "co2_valid": True}
        )
        record, error = self.provider.parse_line(line)
        self.assertIsNone(record)
        self.assertEqual(error, "CO2_RECORD_FIELD_MISSING")

    def test_firmware_version_gate(self):
        provider = build_provider([], expected_firmware_version="safenest-integrated-esp/9.9.9")
        record, error = provider.parse_line(
            serial_line(sample_seq=1, sample_ts_ms=5000).decode()
        )
        self.assertIsNone(record)
        self.assertEqual(error, "CO2_FIRMWARE_VERSION_MISMATCH")


class TestFailClosed(unittest.TestCase):
    """SYNTHETIC FAULT INJECTION — NOT REAL SENSOR EVIDENCE."""

    def assert_invalid(self, lines, expected_error, **kwargs):
        provider = connected_provider(lines, **kwargs)
        result = provider.read()
        self.assertIsInstance(result, InferenceResult)
        self.assertEqual(result.sensor_id, "co2")
        self.assertFalse(result.valid)
        self.assertEqual(result.score, 0.0)
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.error, expected_error)
        self.assertNotEqual(result.state, "NORMAL")
        return provider, result

    def test_read_before_connect(self):
        provider = build_provider([serial_line(sample_seq=1, sample_ts_ms=1000)])
        result = provider.read()
        self.assertFalse(result.valid)
        self.assertEqual(result.state, "NOT_CONNECTED")

    def test_read_after_close(self):
        provider = connected_provider([serial_line(sample_seq=1, sample_ts_ms=1000)])
        provider.close()
        result = provider.read()
        self.assertFalse(result.valid)
        self.assertEqual(result.state, "NOT_CONNECTED")
        self.assertEqual(result.error, "CO2_PROVIDER_CLOSED")

    def test_provider_not_connected_without_port(self):
        provider = CO2SerialProvider()
        self.assertFalse(provider.connect())
        self.assertEqual(provider.last_error, "EXTERNAL_SENSOR_PROVIDER_REQUIRED")
        result = provider.read()
        self.assertFalse(result.valid)
        self.assertEqual(result.error, "EXTERNAL_SENSOR_PROVIDER_REQUIRED")

    def test_serial_timeout(self):
        self.assert_invalid([], "CO2_SERIAL_TIMEOUT")

    def test_telemetry_invalid_flag(self):
        self.assert_invalid(
            [
                serial_line(
                    sample_seq=1,
                    sample_ts_ms=1000,
                    co2_ppm=None,
                    humidity_pct=None,
                    temperature_c=None,
                    co2_valid=False,
                    co2_error="CO2_WARMING_UP",
                )
            ],
            "CO2_TELEMETRY_INVALID:CO2_WARMING_UP",
        )

    def test_null_co2_with_valid_flag(self):
        self.assert_invalid(
            [serial_line(sample_seq=1, sample_ts_ms=1000, co2_ppm=None)],
            "CO2_CO2_PPM_MISSING",
        )

    def test_null_humidity_with_valid_flag(self):
        self.assert_invalid(
            [serial_line(sample_seq=1, sample_ts_ms=1000, humidity_pct=None)],
            "CO2_HUMIDITY_PCT_MISSING",
        )

    def test_nan_rejected(self):
        self.assert_invalid(
            [
                serial_line(
                    sample_seq=1,
                    sample_ts_ms=1000,
                    raw='{"schema":"%s","device_id":"esp32-01","seq":1,'
                    '"ts_monotonic_ms":1100,"co2_ppm":NaN,"humidity_pct":41.375,'
                    '"temperature_c":24.625,"co2_valid":true,"co2_error":null,'
                    '"co2_sample_seq":1,"co2_sample_ts_ms":1000,'
                    '"co2_sample_age_ms":250}\n' % SERIAL_SCHEMA,
                )
            ],
            "CO2_VALUE_NON_FINITE",
        )

    def test_infinity_rejected(self):
        self.assert_invalid(
            [
                serial_line(
                    sample_seq=1,
                    sample_ts_ms=1000,
                    raw='{"schema":"%s","device_id":"esp32-01","seq":1,'
                    '"ts_monotonic_ms":1100,"co2_ppm":812.0,"humidity_pct":Infinity,'
                    '"temperature_c":24.625,"co2_valid":true,"co2_error":null,'
                    '"co2_sample_seq":1,"co2_sample_ts_ms":1000,'
                    '"co2_sample_age_ms":250}\n' % SERIAL_SCHEMA,
                )
            ],
            "CO2_VALUE_NON_FINITE",
        )

    def test_boolean_is_not_a_measurement(self):
        self.assert_invalid(
            [serial_line(sample_seq=1, sample_ts_ms=1000, co2_ppm=True)],
            "CO2_VALUE_NON_FINITE",
        )

    def test_out_of_range_humidity_rejected(self):
        self.assert_invalid(
            [serial_line(sample_seq=1, sample_ts_ms=1000, humidity_pct=145.0)],
            "CO2_VALUE_OUT_OF_RANGE",
        )

    def test_stale_physical_sample_rejected(self):
        self.assert_invalid(
            [serial_line(sample_seq=1, sample_ts_ms=1000, age_ms=25000)],
            "CO2_SAMPLE_STALE",
        )

    def test_non_monotonic_physical_timestamp(self):
        provider, result = self.assert_invalid(
            [
                serial_line(sample_seq=1, sample_ts_ms=10000),
                serial_line(sample_seq=2, sample_ts_ms=9000),
            ],
            "CO2_SAMPLE_TIMESTAMP_NON_MONOTONIC",
        )
        self.assertEqual(len(provider.production.co2_history), 0)

    def test_sequence_reset_clears_history(self):
        provider, result = self.assert_invalid(
            [
                serial_line(sample_seq=7, sample_ts_ms=10000),
                serial_line(sample_seq=2, sample_ts_ms=20000),
            ],
            "CO2_SAMPLE_SEQUENCE_RESET",
        )
        self.assertEqual(len(provider.production.co2_history), 0)

    def test_serial_read_exception(self):
        provider = build_provider([])
        provider._fake_serial.error = OSError("device disconnected")
        provider.connect()
        result = provider.read()
        self.assertFalse(result.valid)
        self.assertEqual(result.error, "CO2_PROVIDER_READ_FAILURE")

    def test_recovery_after_valid_input_resumes(self):
        provider = connected_provider(
            [serial_line(sample_seq=1, sample_ts_ms=1000, co2_ppm=None)]
        )
        first = provider.read()
        self.assertFalse(first.valid)
        self.assertEqual(first.error, "CO2_CO2_PPM_MISSING")

        provider._fake_serial.lines.extend(
            [
                serial_line(sample_seq=2, sample_ts_ms=7000),
                serial_line(sample_seq=3, sample_ts_ms=13000),
            ]
        )
        recovered = provider.read()
        self.assertTrue(recovered.valid, recovered.error)
        self.assertEqual(recovered.sensor_id, "co2")


class TestPhysicalSampleDeduplication(unittest.TestCase):
    """SYNTHETIC TEST — NOT REAL SENSOR EVIDENCE."""

    def test_heartbeat_duplicate_does_not_duplicate_history(self):
        provider = connected_provider(
            [
                serial_line(sample_seq=1, sample_ts_ms=5000, seq=10),
                serial_line(sample_seq=1, sample_ts_ms=5000, seq=11, age_ms=1250),
                serial_line(sample_seq=1, sample_ts_ms=5000, seq=12, age_ms=2250),
            ]
        )
        result = provider.read()
        self.assertEqual(provider.physical_sample_count, 1)
        self.assertEqual(provider.duplicate_line_count, 2)
        self.assertEqual(len(provider.production.co2_history), 1)
        self.assertFalse(result.valid)
        self.assertEqual(result.error, "INSUFFICIENT_HISTORY")

    def test_sequence_increase_adds_exactly_one_sample(self):
        provider = connected_provider(
            [
                serial_line(sample_seq=1, sample_ts_ms=5000),
                serial_line(sample_seq=1, sample_ts_ms=5000),
                serial_line(sample_seq=2, sample_ts_ms=10000),
                serial_line(sample_seq=2, sample_ts_ms=10000),
                serial_line(sample_seq=3, sample_ts_ms=15000),
            ]
        )
        provider.read()
        self.assertEqual(provider.physical_sample_count, 3)
        self.assertEqual(provider.duplicate_line_count, 2)
        self.assertEqual(len(provider.production.co2_history), 3)

    def test_only_heartbeats_yield_no_new_physical_sample(self):
        provider = connected_provider(
            [serial_line(sample_seq=1, sample_ts_ms=5000)]
        )
        provider.read()
        provider._fake_serial.lines.append(
            serial_line(sample_seq=1, sample_ts_ms=5000, seq=99, age_ms=3000)
        )
        result = provider.read()
        self.assertFalse(result.valid)
        self.assertEqual(result.error, "CO2_NO_NEW_PHYSICAL_SAMPLE")
        self.assertEqual(len(provider.production.co2_history), 1)

    def test_same_sequence_with_moved_timestamp_is_inconsistent(self):
        provider = connected_provider(
            [
                serial_line(sample_seq=1, sample_ts_ms=5000),
                serial_line(sample_seq=1, sample_ts_ms=6000),
            ]
        )
        result = provider.read()
        self.assertEqual(result.error, "CO2_SAMPLE_IDENTITY_INCONSISTENT")
        self.assertEqual(len(provider.production.co2_history), 0)

    def test_history_uses_physical_timestamps_not_host_time(self):
        provider = connected_provider(
            [
                serial_line(sample_seq=1, sample_ts_ms=5000),
                serial_line(sample_seq=2, sample_ts_ms=11000),
            ]
        )
        provider.read()
        timestamps = [entry[0] for entry in provider.production.co2_history]
        self.assertEqual(timestamps, [5.0, 11.0])


class TestHistoryAndSlope(unittest.TestCase):
    """SYNTHETIC TEST — NOT REAL SENSOR EVIDENCE."""

    def test_insufficient_history_is_warming_up(self):
        provider = connected_provider([serial_line(sample_seq=1, sample_ts_ms=1000)])
        result = provider.read()
        self.assertFalse(result.valid)
        self.assertEqual(result.error, "INSUFFICIENT_HISTORY")
        self.assertEqual(result.state, "WARMING_UP")
        self.assertEqual(result.metadata["required_history_sec"], 5.0)

    def test_history_span_below_requirement_still_warming_up(self):
        provider = connected_provider(
            [
                serial_line(sample_seq=1, sample_ts_ms=1000),
                serial_line(sample_seq=2, sample_ts_ms=4000),  # span 3.0 s < 5.0 s
            ]
        )
        result = provider.read()
        self.assertEqual(result.error, "INSUFFICIENT_HISTORY")
        self.assertEqual(len(provider.production.co2_history), 2)

    def test_slope_unit_is_ppm_per_minute(self):
        provider = connected_provider(
            [
                serial_line(sample_seq=1, sample_ts_ms=0, co2_ppm=600.0),
                serial_line(sample_seq=2, sample_ts_ms=60000, co2_ppm=700.0),
            ]
        )
        result = provider.read()
        self.assertTrue(result.valid, result.error)
        # (700 - 600) ppm over exactly 1.0 minute
        self.assertAlmostEqual(result.metadata["co2_slope_ppm_min"], 100.0, places=6)

    def test_negative_slope_on_ventilation(self):
        provider = connected_provider(
            [
                serial_line(sample_seq=1, sample_ts_ms=0, co2_ppm=1200.0),
                serial_line(sample_seq=2, sample_ts_ms=60000, co2_ppm=900.0),
            ]
        )
        result = provider.read()
        self.assertAlmostEqual(result.metadata["co2_slope_ppm_min"], -300.0, places=6)

    def test_history_window_is_bounded_by_config(self):
        provider = connected_provider([])
        self.assertEqual(provider.production.co2_history.maxlen, 30)
        self.assertEqual(provider.window_seconds, 150.0)


class TestModelInvocation(unittest.TestCase):
    """SYNTHETIC TEST — NOT REAL SENSOR EVIDENCE.

    The real INT8 TFLite model is invoked here, but only on synthetic input.
    """

    def make_valid_result(self, **line_kwargs):
        provider = connected_provider(
            [
                serial_line(sample_seq=1, sample_ts_ms=0, **line_kwargs),
                serial_line(sample_seq=2, sample_ts_ms=60000, **line_kwargs),
            ]
        )
        result = provider.read()
        self.assertTrue(result.valid, result.error)
        return provider, result

    def test_actual_tflite_is_invoked(self):
        provider, result = self.make_valid_result()
        self.assertEqual(provider.tflite_invocations, 1)
        self.assertEqual(result.metadata["tflite_invocations"], 1)
        self.assertFalse(result.metadata["fallback_used"])

    def test_model_contract_from_manifest(self):
        provider, result = self.make_valid_result()
        self.assertEqual(result.metadata["model_id"], "co2_occupancy_int8")
        self.assertEqual(result.metadata["model_version"], "0.1.0")
        self.assertTrue(result.metadata["model_sha256_matches"])
        self.assertEqual(
            result.metadata["model_sha256"],
            "3a8c86c4c132df0f1edaac668d9a136c3f6234789df48f02bdda8e92f29d0462",
        )

    def test_input_tensor_contract(self):
        provider = connected_provider([])
        info = provider.interpreter.input_info
        self.assertEqual([int(v) for v in info["shape"]], [1, 3])
        self.assertEqual(info["dtype"].__name__, "int8")

    def test_feature_order_matches_production(self):
        provider, result = self.make_valid_result()
        self.assertEqual(
            result.metadata["feature_order"], ["co2_slope", "humidity", "co2_ppm"]
        )
        slope, humidity, ppm = result.metadata["feature_vector"]
        self.assertAlmostEqual(slope, result.metadata["co2_slope_ppm_min"])
        self.assertAlmostEqual(humidity, FIXTURE_HUMIDITY_PCT)
        self.assertAlmostEqual(ppm, FIXTURE_CO2_PPM)

    def test_quantized_input_uses_scaler_then_int8(self):
        provider = connected_provider([])
        quantized = provider.interpreter.prepare_input(
            100.0, FIXTURE_HUMIDITY_PCT, FIXTURE_CO2_PPM
        )
        self.assertEqual(quantized.shape, (1, 3))
        self.assertEqual(quantized.dtype.name, "int8")

    def test_temperature_is_evidence_not_a_model_feature(self):
        provider, result = self.make_valid_result()
        self.assertAlmostEqual(result.metadata["temperature_c"], FIXTURE_TEMPERATURE_C)
        self.assertNotIn(FIXTURE_TEMPERATURE_C, result.metadata["feature_vector"])
        self.assertEqual(len(result.metadata["feature_vector"]), 3)

    def test_high_concentration_rule(self):
        provider, result = self.make_valid_result(co2_ppm=2400.0)
        self.assertEqual(result.score, 1.0)
        self.assertEqual(result.state, "OCCUPIED_ELEVATED")


class TestV5Contract(unittest.TestCase):
    """SYNTHETIC TEST — NOT REAL SENSOR EVIDENCE."""

    def test_provider_interface(self):
        provider = build_provider([])
        validate_provider_interface(provider, "co2")

    def test_connect_read_close_lifecycle(self):
        provider = connected_provider(
            [
                serial_line(sample_seq=1, sample_ts_ms=0),
                serial_line(sample_seq=2, sample_ts_ms=60000),
            ]
        )
        result = provider.read()
        self.assertTrue(result.valid, result.error)
        provider.close()
        self.assertTrue(provider._fake_serial.closed)
        self.assertFalse(provider.connected)

    def test_result_passes_v5_validation(self):
        provider = connected_provider(
            [
                serial_line(sample_seq=1, sample_ts_ms=0),
                serial_line(sample_seq=2, sample_ts_ms=60000),
            ]
        )
        result = provider.read()
        valid, error = validate_provider_result(result, "co2")
        self.assertTrue(valid, error)
        self.assertEqual(result.sensor_id, "co2")
        json.loads(result_to_json(result))  # no NaN/Inf may escape

    def test_invalid_result_also_passes_v5_validation(self):
        provider = connected_provider([])
        result = provider.read()
        valid, error = validate_provider_result(result, "co2")
        self.assertTrue(valid, error)
        self.assertFalse(result.valid)
        self.assertTrue(result.error)

    def test_v5_node_injection(self):
        provider = build_provider(
            [
                serial_line(sample_seq=1, sample_ts_ms=0),
                serial_line(sample_seq=2, sample_ts_ms=60000),
            ]
        )
        node = SafeNestIntegratedNode(mode="real", sensors={"co2": provider})
        self.assertIs(node.sensors["co2"], provider)
        node.start()
        self.assertNotIn("co2", node.backend_errors)
        output = node.step()
        co2_result = output.sensors["co2"]
        self.assertTrue(co2_result["valid"], co2_result.get("error"))
        self.assertEqual(co2_result["sensor_id"], "co2")
        # The other three providers stay explicitly missing in real mode.
        for other in ("thermal44", "mmwave", "pir"):
            self.assertEqual(
                node.backend_errors[other], "EXTERNAL_SENSOR_PROVIDER_REQUIRED"
            )
        node.shutdown()

    def test_provider_settings_match_config(self):
        provider = build_provider([])
        self.assertEqual(
            provider.runtime_settings,
            {
                "timeout_sec": 5.0,
                "stale_sec": 10.0,
                "sample_rate_hz": 0.2,
                "window_samples": 30,
                "window_seconds": 150.0,
            },
        )


class TestPlaceholderExclusion(unittest.TestCase):
    """SYNTHETIC TEST — NOT REAL SENSOR EVIDENCE."""

    PLACEHOLDERS = (650.0, 45.0, 23.5)

    def test_provider_source_has_no_placeholder_triple(self):
        source = (
            REPO_ROOT / "devices" / "co2" / "src" / "co2_serial_adapter.py"
        ).read_text(encoding="utf-8")
        for literal in ("650.0", "45.0", "23.5"):
            self.assertNotIn(literal, source)

    def test_legacy_placeholder_adapter_is_not_imported(self):
        source = (
            REPO_ROOT / "devices" / "co2" / "src" / "co2_serial_adapter.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("co2_adapter import CO2SensorAdapter\nfrom devices", source)
        self.assertNotIn("devices.co2.src.co2_adapter", source)

    def test_real_read_never_returns_placeholder_values(self):
        provider = connected_provider(
            [
                serial_line(sample_seq=1, sample_ts_ms=0),
                serial_line(sample_seq=2, sample_ts_ms=60000),
            ]
        )
        result = provider.read()
        self.assertTrue(result.valid, result.error)
        for key in ("co2_ppm", "humidity_pct", "temperature_c"):
            self.assertNotIn(result.metadata[key], self.PLACEHOLDERS)

    def test_production_hardware_backend_is_never_called(self):
        """The composed production adapter must not reach its I2C stubs."""
        provider = connected_provider(
            [
                serial_line(sample_seq=1, sample_ts_ms=0),
                serial_line(sample_seq=2, sample_ts_ms=60000),
            ]
        )

        def explode(*args, **kwargs):
            raise AssertionError("placeholder hardware path was reached")

        provider.production.read_raw_values = explode
        provider.production.connect = explode
        result = provider.read()
        self.assertTrue(result.valid, result.error)


if __name__ == "__main__":
    unittest.main()
