#!/usr/bin/env python3
"""Real MR60 ESP Serial provider for the SafeNest V5 sensor contract."""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import time
from typing import Any, Callable

import numpy as np


# V5 production modules are top-level packages when ``ondevice_ai`` is on
# sys.path.  Keep that module identity so provider_contract isinstance checks
# see the exact same InferenceResult class.
REPO_ROOT = Path(__file__).resolve().parents[3]
ONDEVICE_AI_ROOT = REPO_ROOT / "ondevice_ai"
if str(ONDEVICE_AI_ROOT) not in sys.path:
    sys.path.insert(0, str(ONDEVICE_AI_ROOT))

from inference.inference_result import InferenceResult
from inference.mmwave_interpreter import MMWaveInterpreter, MMWavePrediction

from devices.mmwave.src.mr60_esp_adapter import MR60ESPAdapter


SerialFactory = Callable[..., Any]


class MMWaveSensorAdapter:
    """Injectable V5 provider backed by real ESP USB Serial JSONL.

    The provider deliberately reuses :class:`MR60ESPAdapter` for provenance,
    presence, distance, phase freshness, sequence, gap, and warm-up gates.
    Only a complete validated 300-sample phase window reaches TFLite.
    """

    sensor_id = "mmwave"

    def __init__(
        self,
        port: str = "EXTERNAL_SENSOR_PROVIDER_REQUIRED",
        baudrate: int = 115200,
        *,
        project_root: str | Path | None = None,
        manifest_path: str = "models/model_manifest.json",
        config_path: str | Path | None = None,
        timeout_sec: float = 2.0,
        stale_sec: float = 3.0,
        sample_rate_hz: float = 10.0,
        window_samples: int = 300,
        window_seconds: float = 30.0,
        serial_factory: SerialFactory | None = None,
        interpreter: MMWaveInterpreter | None = None,
        strict_provenance: bool = True,
    ) -> None:
        self.port = port
        self.baudrate = int(baudrate)
        self.timeout_sec = float(timeout_sec)
        self.stale_sec = float(stale_sec)
        self.sample_rate_hz = float(sample_rate_hz)
        self.window_samples = int(window_samples)
        self.window_seconds = float(window_seconds)
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
            raise ValueError("mmWave window_samples/sample_rate_hz must equal window_seconds")

        self.project_root = (
            Path(project_root).resolve()
            if project_root is not None
            else ONDEVICE_AI_ROOT
        )
        self.manifest_path = manifest_path
        self.config_path = config_path
        self.strict_provenance = strict_provenance
        self.serial_factory = serial_factory
        self.interpreter = interpreter or MMWaveInterpreter(
            project_root=self.project_root,
            manifest_path=self.manifest_path,
        )
        self.adapter = self._new_adapter()
        if self.adapter.estimator.window_samples != self.window_samples:
            raise ValueError(
                "MR60 processing window does not match V5 provider window: "
                f"adapter={self.adapter.estimator.window_samples}, "
                f"provider={self.window_samples}"
            )
        if not math.isclose(
            self.adapter.estimator.sample_rate_hz,
            self.sample_rate_hz,
            abs_tol=1e-9,
        ):
            raise ValueError(
                "MR60 processing sample rate does not match V5 provider rate: "
                f"adapter={self.adapter.estimator.sample_rate_hz}, "
                f"provider={self.sample_rate_hz}"
            )

        self.serial: Any | None = None
        self.connected = False
        self.last_error: str | None = None
        self.last_result: InferenceResult | None = None

    def _new_adapter(self) -> MR60ESPAdapter:
        return MR60ESPAdapter(
            self.config_path,
            strict_provenance=self.strict_provenance,
        )

    def _default_serial_factory(self) -> SerialFactory:
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError("PYSERIAL_NOT_INSTALLED") from exc
        return serial.Serial

    def connect(self) -> bool:
        self.close()
        self.adapter = self._new_adapter()
        if self.port == "EXTERNAL_SENSOR_PROVIDER_REQUIRED" or not self.port:
            self.last_error = "EXTERNAL_SENSOR_PROVIDER_REQUIRED"
            return False
        try:
            factory = self.serial_factory or self._default_serial_factory()
            self.serial = factory(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout_sec,
            )
            reset_input = getattr(self.serial, "reset_input_buffer", None)
            if callable(reset_input):
                reset_input()
            self.connected = bool(getattr(self.serial, "is_open", True))
            self.last_error = None if self.connected else "MMWAVE_SERIAL_OPEN_FAILED"
            return self.connected
        except Exception as exc:
            self.serial = None
            self.connected = False
            self.last_error = f"MMWAVE_SERIAL_CONNECT_FAILED:{type(exc).__name__}"
            return False

    @staticmethod
    def _packet_metadata(packet: dict[str, Any]) -> dict[str, Any]:
        mmwave = packet.get("mmwave_mr60", {})
        return {
            "source": "REAL_MR60BHA2_ESP_SERIAL_JSONL",
            "source_timestamp_s": packet.get("timestamp_s"),
            "presence": mmwave.get("presence"),
            "distance_cm": mmwave.get("distance_cm"),
            "window_samples": mmwave.get("window_samples"),
            "communication_valid": mmwave.get("communication_valid"),
            "stale": mmwave.get("stale"),
            "esp_schema_version": mmwave.get("esp_schema_version"),
            "esp_firmware_version": mmwave.get("esp_firmware_version"),
            "esp_config_hash": mmwave.get("esp_config_hash"),
            "pi_config_hash": mmwave.get("pi_config_hash"),
            "sensor_firmware_version": mmwave.get("sensor_firmware_version"),
            "apnea_verified": False,
        }

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

    def read(self) -> InferenceResult:
        started = time.perf_counter()
        if not self.connected or self.serial is None:
            return self._invalid_result(
                started=started,
                error=self.last_error or "SENSOR_NOT_CONNECTED",
                state="NOT_CONNECTED",
                metadata={"source": "REAL_MR60BHA2_ESP_SERIAL_JSONL"},
            )

        try:
            raw = self.serial.readline()
        except Exception as exc:
            return self._invalid_result(
                started=started,
                error="MMWAVE_PROVIDER_READ_FAILURE",
                state="FAULT",
                metadata={"detail": f"{type(exc).__name__}: {exc}"},
            )

        if not raw:
            packet = self.adapter.timeout_packet()
            return self._invalid_result(
                started=started,
                error="MMWAVE_SERIAL_TIMEOUT",
                state="UNKNOWN",
                metadata=self._packet_metadata(packet),
            )

        if isinstance(raw, bytes):
            line = raw.decode("utf-8", errors="replace")
        elif isinstance(raw, str):
            line = raw
        else:
            return self._invalid_result(
                started=started,
                error="MMWAVE_SERIAL_RECORD_TYPE_INVALID",
                state="FAULT",
            )

        packet = self.adapter.process_json_line(line)
        mmwave = packet["mmwave_mr60"]
        metadata = self._packet_metadata(packet)
        if not mmwave["valid"]:
            return self._invalid_result(
                started=started,
                error=mmwave.get("fault_reason") or "MMWAVE_RECORD_INVALID",
                state=mmwave.get("state") or "UNKNOWN",
                metadata=metadata,
            )

        window = np.asarray(self.adapter.estimator.values, dtype=np.float32)
        timestamps = np.asarray(self.adapter.estimator.timestamps, dtype=np.float64)
        if window.shape != (self.window_samples,) or timestamps.shape != (self.window_samples,):
            metadata.update(
                {
                    "window_shape": list(window.shape),
                    "required_window_shape": [self.window_samples],
                }
            )
            return self._invalid_result(
                started=started,
                error="MMWAVE_WINDOW_NOT_READY",
                state="WARMUP",
                metadata=metadata,
            )
        if not np.all(np.isfinite(window)) or not np.all(np.isfinite(timestamps)):
            return self._invalid_result(
                started=started,
                error="MMWAVE_WINDOW_NON_FINITE",
                state="FAULT",
                metadata=metadata,
            )

        intervals = np.diff(timestamps)
        input_info = self.interpreter.input_info
        metadata.update(
            {
                "window_shape": [self.window_samples],
                "window_duration_s": float(timestamps[-1] - timestamps[0]),
                "sample_interval_min_s": float(np.min(intervals)),
                "sample_interval_median_s": float(np.median(intervals)),
                "sample_interval_max_s": float(np.max(intervals)),
                "model_input_shape": [int(value) for value in input_info["shape"]],
                "model_input_dtype": np.dtype(input_info["dtype"]).name,
            }
        )

        try:
            prediction: MMWavePrediction = self.interpreter.predict(window)
        except Exception as exc:
            return self._invalid_result(
                started=started,
                error="MMWAVE_TFLITE_INFERENCE_FAILED",
                state="INFER_ERROR",
                metadata={**metadata, "detail": f"{type(exc).__name__}: {exc}"},
            )

        metadata.update(
            {
                "model_id": prediction.model_id,
                "model_version": prediction.model_version,
                "model_sha256": self.interpreter.sha256_hash,
                "model_sha256_matches": self.interpreter.sha256_matches,
                "class_index": prediction.class_index,
                "class_name": prediction.class_name,
                "probabilities": prediction.probabilities,
                "inference_latency_ms": prediction.latency_ms,
                "fallback_used": prediction.fallback_used,
                "fallback_reason": prediction.fallback_reason,
            }
        )
        if prediction.fallback_used:
            return self._invalid_result(
                started=started,
                error=prediction.fallback_reason or "MMWAVE_MODEL_UNVERIFIED_FALLBACK",
                state="UNKNOWN",
                metadata=metadata,
            )

        if prediction.class_index == 2:
            score = 0.5
            state = "MODEL_APNEA_CANDIDATE_UNVERIFIED"
        elif prediction.class_index == 1:
            score = 0.5
            state = "RAPID_OR_ABNORMAL"
        else:
            score = 0.0
            state = "NORMAL"

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
                    self.last_error = f"MMWAVE_SERIAL_CLOSE_FAILED:{type(exc).__name__}"
        self.adapter.estimator.reset("MMWAVE_PROVIDER_CLOSED")


def result_to_json(result: InferenceResult) -> str:
    """Serialize a provider result without allowing NaN/Inf."""

    return json.dumps(result.to_dict(), ensure_ascii=False, allow_nan=False)
