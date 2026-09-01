#!/usr/bin/env python3
"""Real SCD4x ESP USB-Serial provider for the SafeNest V5 sensor contract.

Data path::

    ESP32 USB serial JSONL (schema "safenest.co2.serial.v1")
      -> physical-sample deduplication
      -> production CO2 history / slope (ondevice_ai CO2SensorAdapter)
      -> production CO2Interpreter (INT8 TFLite)
      -> InferenceResult(sensor_id="co2")
      -> V5 run_node provider injection

The provider owns transport and physical-sample identity only.  History,
slope and the model contract are reused verbatim from the V5 production
implementation so this file cannot drift from it.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Callable


# V5 production modules are top-level packages when ``ondevice_ai`` is on
# sys.path.  Keep that module identity so provider_contract isinstance checks
# see the exact same InferenceResult class.
REPO_ROOT = Path(__file__).resolve().parents[3]
ONDEVICE_AI_ROOT = REPO_ROOT / "ondevice_ai"
if str(ONDEVICE_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(ONDEVICE_AI_ROOT))

from inference.co2_interpreter import CO2Interpreter, CO2Prediction  # noqa: E402
from inference.inference_result import InferenceResult  # noqa: E402
from sensors.co2.co2_adapter import CO2SensorAdapter  # noqa: E402


SerialFactory = Callable[..., Any]

SERIAL_SCHEMA = "safenest.co2.serial.v1"

# Mirrors the local constant inside the production CO2SensorAdapter.read()
# (ondevice_ai/sensors/co2/co2_adapter.py).  Kept as a named default so the
# AI history warm-up requirement stays visible and configurable in one place.
PRODUCTION_REQUIRED_HISTORY_SEC = 5.0

# Physical bounds of the SCD4x measurement range.  Values outside these bounds
# are rejected instead of being fed to the model.
CO2_PPM_MIN = 1.0
CO2_PPM_MAX = 40000.0
HUMIDITY_PCT_MIN = 0.0
HUMIDITY_PCT_MAX = 100.0
TEMPERATURE_C_MIN = -40.0
TEMPERATURE_C_MAX = 125.0

_REQUIRED_FIELDS = (
    "co2_ppm",
    "humidity_pct",
    "temperature_c",
    "co2_valid",
    "co2_sample_seq",
    "co2_sample_ts_ms",
)


def _finite_number(value: object) -> bool:
    """True only for a real finite int/float. Booleans are explicitly rejected."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


class CO2SerialProvider:
    """Injectable V5 provider backed by real SCD4x ESP USB Serial JSONL.

    The ESP emits a 1 Hz heartbeat line, but the SCD4x produces a new physical
    measurement only about every 5 s.  Every line therefore carries the physical
    sample identity (``co2_sample_seq`` / ``co2_sample_ts_ms``) and the provider
    appends to the AI history exactly once per physical sample.
    """

    sensor_id = "co2"

    def __init__(
        self,
        port: str = "EXTERNAL_SENSOR_PROVIDER_REQUIRED",
        baudrate: int = 115200,
        *,
        project_root: str | Path | None = None,
        manifest_path: str = "models/model_manifest.json",
        timeout_sec: float = 5.0,
        stale_sec: float = 10.0,
        sample_rate_hz: float = 0.2,
        window_samples: int = 30,
        window_seconds: float = 150.0,
        required_history_sec: float = PRODUCTION_REQUIRED_HISTORY_SEC,
        max_lines_per_read: int = 32,
        serial_poll_timeout_sec: float = 1.5,
        read_deadline_ratio: float = 0.8,
        expected_firmware_version: str | None = None,
        serial_factory: SerialFactory | None = None,
        interpreter: CO2Interpreter | None = None,
    ) -> None:
        self.port = port
        self.baudrate = int(baudrate)
        self.timeout_sec = float(timeout_sec)
        self.stale_sec = float(stale_sec)
        self.sample_rate_hz = float(sample_rate_hz)
        self.window_samples = int(window_samples)
        self.window_seconds = float(window_seconds)
        self.required_history_sec = float(required_history_sec)
        self.max_lines_per_read = int(max_lines_per_read)
        # The ESP streams a 1 Hz heartbeat continuously, so the serial object is
        # polled on a shorter timeout than the provider's own read budget and a
        # single read() is bounded well inside timeout_sec.
        self.serial_poll_timeout_sec = min(float(serial_poll_timeout_sec), float(timeout_sec))
        self.read_deadline_sec = float(timeout_sec) * float(read_deadline_ratio)
        self.expected_firmware_version = expected_firmware_version
        self.runtime_settings = {
            "timeout_sec": self.timeout_sec,
            "stale_sec": self.stale_sec,
            "sample_rate_hz": self.sample_rate_hz,
            "window_samples": self.window_samples,
            "window_seconds": self.window_seconds,
        }
        if not math.isclose(
            self.window_samples / self.sample_rate_hz,
            self.window_seconds,
            abs_tol=1e-9,
        ):
            raise ValueError("CO2 window_samples/sample_rate_hz must equal window_seconds")

        self.project_root = (
            Path(project_root).resolve()
            if project_root is not None
            else ONDEVICE_AI_ROOT
        )
        self.manifest_path = manifest_path
        self.serial_factory = serial_factory

        # The production adapter supplies the authoritative history container and
        # slope algorithm.  Its connect()/read_raw_values() are never called, so
        # no hardware-backend or placeholder path can be reached from here.
        self.production = CO2SensorAdapter(
            project_root=self.project_root,
            manifest_path=self.manifest_path,
            timeout_sec=self.timeout_sec,
            stale_sec=self.stale_sec,
            sample_rate_hz=self.sample_rate_hz,
            window_samples=self.window_samples,
            window_seconds=self.window_seconds,
        )
        if interpreter is not None:
            self.production.interpreter = interpreter
        self.interpreter: CO2Interpreter = self.production.interpreter

        self.serial: Any | None = None
        self.connected = False
        self.last_error: str | None = None
        self.last_result: InferenceResult | None = None

        # Physical-sample identity tracking (transport-owned, not AI-owned).
        self.last_sample_seq: int | None = None
        self.last_sample_ts_ms: int | None = None
        self.physical_sample_count = 0
        self.duplicate_line_count = 0
        self.non_telemetry_line_count = 0
        self.tflite_invocations = 0

    # ------------------------------------------------------------------
    # transport
    # ------------------------------------------------------------------
    def _default_serial_factory(self) -> SerialFactory:
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("PYSERIAL_NOT_INSTALLED") from exc
        return serial.Serial

    def _bytes_waiting(self) -> int:
        try:
            return int(getattr(self.serial, "in_waiting", 0) or 0)
        except Exception:
            return 0

    def _reset_history(self, reason: str) -> None:
        self.production.co2_history.clear()
        self.last_sample_seq = None
        self.last_sample_ts_ms = None
        self.last_error = reason

    def connect(self) -> bool:
        self.close()
        self._reset_history("CO2_PROVIDER_CONNECTING")
        if self.port == "EXTERNAL_SENSOR_PROVIDER_REQUIRED" or not self.port:
            self.last_error = "EXTERNAL_SENSOR_PROVIDER_REQUIRED"
            return False
        try:
            factory = self.serial_factory or self._default_serial_factory()
            self.serial = factory(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.serial_poll_timeout_sec,
            )
            reset_input = getattr(self.serial, "reset_input_buffer", None)
            if callable(reset_input):
                reset_input()
            self.connected = bool(getattr(self.serial, "is_open", True))
            self.last_error = None if self.connected else "CO2_SERIAL_OPEN_FAILED"
            return self.connected
        except Exception as exc:
            self.serial = None
            self.connected = False
            self.last_error = f"CO2_SERIAL_CONNECT_FAILED:{type(exc).__name__}"
            return False

    def close(self) -> None:
        serial_obj = self.serial
        self.serial = None
        self.connected = False
        if serial_obj is not None:
            close = getattr(serial_obj, "close", None)
            if callable(close):
                try:
                    close()
                except Exception as exc:
                    self.last_error = f"CO2_SERIAL_CLOSE_FAILED:{type(exc).__name__}"
        self._reset_history("CO2_PROVIDER_CLOSED")

    # ------------------------------------------------------------------
    # serial schema parsing
    # ------------------------------------------------------------------
    def parse_line(self, line: str) -> tuple[dict[str, Any] | None, str | None]:
        """Validate one JSONL record. Returns (record, error_code)."""

        text = line.strip()
        if not text:
            return None, "CO2_SERIAL_EMPTY_LINE"
        if not text.startswith("{"):
            # The same USB serial carries the firmware's human-readable boot and
            # "[health] ..." lines. Those are not corrupt telemetry, so they are
            # skipped rather than reported as a CO2 fault.
            return None, "CO2_SERIAL_NON_TELEMETRY_LINE"
        try:
            record = json.loads(text)
        except (ValueError, TypeError):
            return None, "CO2_MALFORMED_JSON"
        if not isinstance(record, dict):
            return None, "CO2_RECORD_TYPE_INVALID"
        if record.get("schema") != SERIAL_SCHEMA:
            return None, "CO2_SCHEMA_MISMATCH"
        if any(field not in record for field in _REQUIRED_FIELDS):
            return None, "CO2_RECORD_FIELD_MISSING"
        if (
            self.expected_firmware_version is not None
            and record.get("firmware_version") != self.expected_firmware_version
        ):
            return None, "CO2_FIRMWARE_VERSION_MISMATCH"
        return record, None

    def _validate_measurement(
        self, record: dict[str, Any]
    ) -> tuple[dict[str, float] | None, str | None]:
        """Fail-closed gate for one physical measurement."""

        if record.get("co2_valid") is not True:
            reported = record.get("co2_error")
            if isinstance(reported, str) and reported:
                return None, f"CO2_TELEMETRY_INVALID:{reported}"
            return None, "CO2_TELEMETRY_INVALID"

        values: dict[str, float] = {}
        for field in ("co2_ppm", "humidity_pct", "temperature_c"):
            value = record.get(field)
            if value is None:
                return None, f"CO2_{field.upper()}_MISSING"
            if not _finite_number(value):
                return None, "CO2_VALUE_NON_FINITE"
            values[field] = float(value)

        if not CO2_PPM_MIN <= values["co2_ppm"] <= CO2_PPM_MAX:
            return None, "CO2_VALUE_OUT_OF_RANGE"
        if not HUMIDITY_PCT_MIN <= values["humidity_pct"] <= HUMIDITY_PCT_MAX:
            return None, "CO2_VALUE_OUT_OF_RANGE"
        if not TEMPERATURE_C_MIN <= values["temperature_c"] <= TEMPERATURE_C_MAX:
            return None, "CO2_VALUE_OUT_OF_RANGE"

        age_ms = record.get("co2_sample_age_ms")
        if age_ms is not None:
            if not _finite_number(age_ms) or age_ms < 0:
                return None, "CO2_SAMPLE_AGE_INVALID"
            if float(age_ms) > self.stale_sec * 1000.0:
                return None, "CO2_SAMPLE_STALE"
        return values, None

    # ------------------------------------------------------------------
    # physical-sample deduplication
    # ------------------------------------------------------------------
    def classify_sample(self, record: dict[str, Any]) -> tuple[str, str | None]:
        """Decide whether a record carries a NEW physical SCD4x measurement.

        Returns one of ``"new"``, ``"duplicate"``, ``"invalid"`` plus an error
        code for the invalid case.  A 1 Hz heartbeat repeating the last physical
        sample is a ``duplicate`` and must never reach the history.
        """

        seq = record.get("co2_sample_seq")
        ts_ms = record.get("co2_sample_ts_ms")
        if not _finite_number(seq) or float(seq) < 0 or float(seq) != int(seq):
            return "invalid", "CO2_SAMPLE_SEQUENCE_INVALID"
        if ts_ms is None or not _finite_number(ts_ms) or float(ts_ms) < 0:
            return "invalid", "CO2_SAMPLE_TIMESTAMP_INVALID"
        seq = int(seq)
        ts_ms = int(ts_ms)

        if self.last_sample_seq is None:
            return "new", None
        if seq == self.last_sample_seq:
            # Same physical measurement re-announced by the heartbeat. The
            # physical timestamp must not have moved.
            if ts_ms != self.last_sample_ts_ms:
                return "invalid", "CO2_SAMPLE_IDENTITY_INCONSISTENT"
            return "duplicate", None
        if seq < self.last_sample_seq:
            return "invalid", "CO2_SAMPLE_SEQUENCE_RESET"
        if self.last_sample_ts_ms is not None and ts_ms <= self.last_sample_ts_ms:
            return "invalid", "CO2_SAMPLE_TIMESTAMP_NON_MONOTONIC"
        return "new", None

    # ------------------------------------------------------------------
    # results
    # ------------------------------------------------------------------
    def _base_metadata(self, record: dict[str, Any] | None = None) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "source": "REAL_SCD4X_ESP_SERIAL_JSONL",
            "serial_schema": SERIAL_SCHEMA,
            "physical_sample_count": self.physical_sample_count,
            "duplicate_line_count": self.duplicate_line_count,
            "non_telemetry_line_count": self.non_telemetry_line_count,
            "history_samples": len(self.production.co2_history),
        }
        if record is not None:
            metadata.update(
                {
                    "esp_device_id": record.get("device_id"),
                    "esp_firmware_version": record.get("firmware_version"),
                    "esp_seq": record.get("seq"),
                    "esp_ts_monotonic_ms": record.get("ts_monotonic_ms"),
                    "co2_sample_seq": record.get("co2_sample_seq"),
                    "co2_sample_ts_ms": record.get("co2_sample_ts_ms"),
                    "co2_sample_age_ms": record.get("co2_sample_age_ms"),
                }
            )
        return metadata

    def _invalid_result(
        self,
        *,
        started: float,
        error: str,
        state: str = "UNKNOWN",
        metadata: dict[str, Any] | None = None,
    ) -> InferenceResult:
        self.last_error = error
        result = InferenceResult(
            sensor_id=self.sensor_id,
            timestamp=time.time(),
            score=0.0,
            state=state,
            confidence=0.0,
            valid=False,
            latency_ms=(time.perf_counter() - started) * 1000.0,
            error=error,
            metadata=dict(metadata or {}),
        )
        self.last_result = result
        return result

    # ------------------------------------------------------------------
    # read
    # ------------------------------------------------------------------
    def read(self) -> InferenceResult:
        started = time.perf_counter()
        if not self.connected or self.serial is None:
            return self._invalid_result(
                started=started,
                error=self.last_error or "SENSOR_NOT_CONNECTED",
                state="NOT_CONNECTED",
                metadata=self._base_metadata(),
            )

        latest: dict[str, Any] | None = None
        latest_values: dict[str, float] | None = None
        latest_slope: float | None = None
        pending_error: str | None = None
        pending_record: dict[str, Any] | None = None
        pending_state = "UNKNOWN"
        lines_read = 0

        # The ESP heartbeat runs faster than the SCD4x physical cadence, so drain
        # what is buffered and keep the newest physical sample. Every new
        # physical sample still enters the history exactly once, in order. The
        # drain is bounded by read_deadline_sec so one read() always returns
        # inside the configured provider timeout.
        deadline = started + self.read_deadline_sec
        while lines_read < self.max_lines_per_read:
            # A blocking readline can itself consume a full poll timeout, so the
            # budget check reserves that time. One read() therefore always
            # returns inside the configured provider timeout_sec.
            if time.perf_counter() + self.serial_poll_timeout_sec > deadline:
                break
            try:
                raw = self.serial.readline()
            except Exception as exc:
                return self._invalid_result(
                    started=started,
                    error="CO2_PROVIDER_READ_FAILURE",
                    state="FAULT",
                    metadata={
                        **self._base_metadata(latest),
                        "detail": f"{type(exc).__name__}: {exc}",
                    },
                )
            if not raw:
                break
            lines_read += 1

            if isinstance(raw, bytes):
                line = raw.decode("utf-8", errors="replace")
            elif isinstance(raw, str):
                line = raw
            else:
                pending_error = "CO2_SERIAL_RECORD_TYPE_INVALID"
                pending_state = "FAULT"
                continue

            record, error = self.parse_line(line)
            if error == "CO2_SERIAL_NON_TELEMETRY_LINE":
                self.non_telemetry_line_count += 1
                continue
            if error is not None:
                pending_error, pending_record, pending_state = error, None, "FAULT"
                continue

            assert record is not None
            classification, identity_error = self.classify_sample(record)
            if classification == "invalid":
                assert identity_error is not None
                # A broken physical-sample sequence invalidates the slope basis.
                self._reset_history(identity_error)
                pending_error = identity_error
                pending_record = record
                pending_state = "INVALID_FORMAT"
                continue
            if classification == "duplicate":
                self.duplicate_line_count += 1
                # A heartbeat carries no measurement, so it must not mask a more
                # specific state (warm-up, fault) already seen in this drain.
                if latest is None and pending_error is None:
                    pending_error = "CO2_NO_NEW_PHYSICAL_SAMPLE"
                    pending_record = record
                    pending_state = "WAITING_FOR_PHYSICAL_SAMPLE"
                continue

            values, measurement_error = self._validate_measurement(record)
            if measurement_error is not None:
                # The identity is accepted so a later sample is still "new", but
                # the measurement itself never enters the history.
                self.last_sample_seq = int(record["co2_sample_seq"])
                self.last_sample_ts_ms = int(record["co2_sample_ts_ms"])
                pending_error = measurement_error
                pending_record = record
                pending_state = "INVALID_FORMAT"
                latest, latest_values, latest_slope = None, None, None
                continue

            assert values is not None
            self.last_sample_seq = int(record["co2_sample_seq"])
            self.last_sample_ts_ms = int(record["co2_sample_ts_ms"])
            self.physical_sample_count += 1

            # Production slope, driven by the PHYSICAL sample timestamp from the
            # sensor node - never by the host receive time.
            physical_ts_s = float(self.last_sample_ts_ms) / 1000.0
            slope, slope_error = self.production.calculate_co2_slope(
                physical_ts_s,
                values["co2_ppm"],
                required_history_sec=self.required_history_sec,
            )
            if slope_error is not None:
                pending_error = slope_error
                pending_record = record
                pending_state = (
                    "WARMING_UP"
                    if slope_error == "INSUFFICIENT_HISTORY"
                    else "INVALID_FORMAT"
                )
                latest, latest_values, latest_slope = None, None, None
                continue

            latest, latest_values, latest_slope = record, values, slope
            pending_error = None

            # A fresh physical sample is ready and nothing else is buffered, so
            # there is no reason to keep the caller waiting.
            if not self._bytes_waiting():
                break

        if latest is None or latest_values is None or latest_slope is None:
            metadata = self._base_metadata(pending_record)
            if pending_error is None:
                pending_error = "CO2_SERIAL_TIMEOUT"
                pending_state = "READ_TIMEOUT"
            if pending_error == "INSUFFICIENT_HISTORY":
                metadata["required_history_sec"] = self.required_history_sec
            return self._invalid_result(
                started=started,
                error=pending_error,
                state=pending_state,
                metadata=metadata,
            )

        metadata = self._base_metadata(latest)
        metadata.update(
            {
                "co2_ppm": latest_values["co2_ppm"],
                "humidity_pct": latest_values["humidity_pct"],
                # Temperature is real hardware evidence. The current model does
                # not take it as an input feature and it is never injected.
                "temperature_c": latest_values["temperature_c"],
                "co2_slope_ppm_min": latest_slope,
                "feature_order": ["co2_slope", "humidity", "co2_ppm"],
                "feature_vector": [
                    latest_slope,
                    latest_values["humidity_pct"],
                    latest_values["co2_ppm"],
                ],
                "slope_timestamp_source": "esp_co2_sample_ts_ms",
                "required_history_sec": self.required_history_sec,
                "model_sha256": self.interpreter.sha256_hash,
                "model_sha256_matches": self.interpreter.sha256_matches,
            }
        )

        try:
            prediction: CO2Prediction = self.interpreter.predict(
                latest_slope,
                latest_values["humidity_pct"],
                latest_values["co2_ppm"],
            )
        except Exception as exc:
            return self._invalid_result(
                started=started,
                error="CO2_TFLITE_INFERENCE_FAILED",
                state="INFER_ERROR",
                metadata={**metadata, "detail": f"{type(exc).__name__}: {exc}"},
            )
        self.tflite_invocations += 1

        # Production decision rule, identical to CO2SensorAdapter.read().
        score = 1.0 if (prediction.class_index == 1 or latest_values["co2_ppm"] > 1500.0) else 0.0
        state = "OCCUPIED_ELEVATED" if score == 1.0 else prediction.class_name

        metadata.update(
            {
                "model_id": prediction.model_id,
                "model_version": prediction.model_version,
                "class_index": prediction.class_index,
                "class_name": prediction.class_name,
                "probabilities": prediction.probabilities,
                "inference_latency_ms": prediction.latency_ms,
                "tflite_invocations": self.tflite_invocations,
                "fallback_used": False,
            }
        )

        result = InferenceResult(
            sensor_id=self.sensor_id,
            timestamp=time.time(),
            score=score,
            state=state,
            confidence=prediction.confidence,
            valid=True,
            latency_ms=(time.perf_counter() - started) * 1000.0,
            error=None,
            metadata=metadata,
        )
        self.last_error = None
        self.last_result = result
        return result


def result_to_json(result: InferenceResult) -> str:
    """Serialize a provider result without allowing NaN/Inf."""

    return json.dumps(result.to_dict(), ensure_ascii=False, allow_nan=False)
