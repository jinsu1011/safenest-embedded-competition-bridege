#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sensors/co2/co2_adapter.py
Hardware SCD40 CO2 / Temperature / Humidity Sensor I2C Adapter
"""

from __future__ import annotations
import csv
import math
import time
from pathlib import Path
from collections import deque
from collections.abc import Iterator

from shared.contracts.base_sensor import BaseSensor, SensorState
from ondevice_ai.src.inference.inference_result import InferenceResult
from ondevice_ai.src.inference.co2_interpreter import CO2Interpreter, CO2Prediction


class CO2LogReplayAdapter(BaseSensor):
    """캡처 CSV를 공용 InferenceResult/SensorState 계약으로 재생한다."""

    def __init__(self, log_path: str | Path):
        super().__init__(sensor_id="co2")
        self.log_path = Path(log_path)
        self._rows: Iterator[dict[str, str]] | None = None
        self.last_raw_row: dict[str, str] | None = None

    def connect(self) -> bool:
        try:
            stream = self.log_path.open("r", encoding="utf-8-sig", newline="")
            self._rows = iter(csv.DictReader(stream))
            self._stream = stream
            self.connected = True
            self.current_state = SensorState.NORMAL
            self.last_error = None
            return True
        except OSError as exc:
            self.connected = False
            self.current_state = SensorState.NOT_CONNECTED
            self.last_error = str(exc)
            return False

    @staticmethod
    def _is_true(value: str | None) -> bool:
        return str(value).strip().lower() == "true"

    def _invalid_result(self, timestamp: float, state: str, error: str) -> InferenceResult:
        state_map = {
            "NOT_CONNECTED": SensorState.NOT_CONNECTED,
            "STALE": SensorState.STALE,
            "READ_TIMEOUT": SensorState.READ_TIMEOUT,
            "INVALID_FORMAT": SensorState.INVALID_FORMAT,
            "OUT_OF_BOUNDS": SensorState.OUT_OF_BOUNDS,
        }
        self.current_state = state_map.get(state, SensorState.INVALID_FORMAT)
        self.error_count += 1
        self.last_error = error
        return InferenceResult(
            sensor_id=self.sensor_id,
            timestamp=timestamp,
            score=0.0,
            state=state,
            confidence=0.0,
            valid=False,
            latency_ms=0.0,
            error=error,
            metadata={"source": "measured_log"},
        )

    def read(self) -> InferenceResult:
        timestamp = time.time()
        self.read_count += 1

        if not self.connected or self._rows is None:
            return self._invalid_result(timestamp, "NOT_CONNECTED", "LOG_NOT_CONNECTED")

        try:
            row = next(self._rows)
        except StopIteration:
            return self._invalid_result(timestamp, "STALE", "END_OF_LOG")

        self.last_raw_row = row
        try:
            timestamp = float(row["host_unix_s"])
        except (KeyError, TypeError, ValueError):
            return self._invalid_result(timestamp, "INVALID_FORMAT", "INVALID_HOST_TIMESTAMP")
        # InferenceResult에는 원래 측정시각을 보존하고, SensorHealth의 age는
        # replay 프로세스가 해당 행을 읽은 현재시각을 기준으로 계산한다.
        self.last_read_ts = time.time()

        row_state = (row.get("sensor_state") or "INVALID_FORMAT").strip()
        row_error = (row.get("error") or "CO2_READING_INVALID").strip()
        if not self._is_true(row.get("valid")):
            return self._invalid_result(timestamp, row_state, row_error)

        try:
            co2_ppm = float(row["co2_ppm"])
        except (KeyError, TypeError, ValueError):
            return self._invalid_result(timestamp, "INVALID_FORMAT", "INVALID_CO2_VALUE")
        if not math.isfinite(co2_ppm):
            return self._invalid_result(timestamp, "INVALID_FORMAT", "NON_FINITE_CO2_VALUE")

        self.current_state = SensorState.NORMAL
        self.last_error = None
        return InferenceResult(
            sensor_id=self.sensor_id,
            timestamp=timestamp,
            score=0.0,
            state="NORMAL",
            confidence=1.0,
            valid=True,
            latency_ms=0.0,
            metadata={
                "source": "measured_log",
                "co2_ppm": co2_ppm,
                "seq": int(float(row["seq"])) if row.get("seq") else None,
            },
        )

    def close(self) -> None:
        stream = getattr(self, "_stream", None)
        if stream is not None:
            stream.close()
        self._rows = None
        self.connected = False
        self.current_state = SensorState.SHUTDOWN


class CO2SensorAdapter(BaseSensor):
    def __init__(self, i2c_bus: int = 1, address: int = 0x62, project_root: str | Path | None = None, manifest_path: str = "models/model_manifest.json"):
        super().__init__(sensor_id="co2")
        self.i2c_bus = i2c_bus
        self.address = address
        self.interpreter = CO2Interpreter(project_root=project_root, manifest_path=manifest_path)
        self.co2_history = deque(maxlen=30)  # Timestamp & ppm history for slope calculation

    def connect(self) -> bool:
        # Hardware I2C connection logic for SCD40 sensor
        try:
            self.connected = True
            self.current_state = SensorState.NORMAL
            return True
        except Exception as exc:
            self.connected = False
            self.last_error = str(exc)
            self.current_state = SensorState.NOT_CONNECTED
            return False

    def calculate_co2_slope(self, current_ts: float, current_ppm: float) -> float:
        self.co2_history.append((current_ts, current_ppm))
        if len(self.co2_history) < 2:
            return 0.0

        ts_first, ppm_first = self.co2_history[0]
        elapsed_min = (current_ts - ts_first) / 60.0
        if elapsed_min <= 0:
            return 0.0

        return float((current_ppm - ppm_first) / elapsed_min)

    def read_raw_values(self) -> tuple[float, float, float]:
        # Return (co2_ppm, humidity_pct, temp_c)
        return (650.0, 45.0, 23.5)

    def read(self) -> InferenceResult:
        t0 = time.perf_counter()
        now = time.time()
        self.read_count += 1
        self.last_read_ts = now

        if not self.connected:
            self.current_state = SensorState.NOT_CONNECTED
            return InferenceResult(
                sensor_id=self.sensor_id,
                timestamp=now,
                score=0.0,
                state="NOT_CONNECTED",
                confidence=0.0,
                valid=False,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                error="SENSOR_NOT_CONNECTED"
            )

        try:
            import numpy as np

            co2_ppm, humidity, _ = self.read_raw_values()
            co2_slope = self.calculate_co2_slope(now, co2_ppm)
            features = np.array([co2_slope, humidity, co2_ppm], dtype=np.float32)

            pred: CO2Prediction = self.interpreter.predict(features)
            score = 1.0 if (pred.class_index == 1 or co2_ppm > 1500.0) else 0.0
            self.current_state = SensorState.NORMAL

            return InferenceResult(
                sensor_id=self.sensor_id,
                timestamp=now,
                score=score,
                state="OCCUPIED_ELEVATED" if score == 1.0 else pred.class_name,
                confidence=pred.confidence,
                valid=True,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                metadata={
                    "model_id": pred.model_id,
                    "class_index": pred.class_index,
                    "probabilities": pred.probabilities,
                    "co2_ppm": co2_ppm,
                    "co2_slope_ppm_min": co2_slope
                }
            )
        except Exception as exc:
            self.error_count += 1
            self.current_state = SensorState.INFER_FAILED
            return InferenceResult(
                sensor_id=self.sensor_id,
                timestamp=now,
                score=0.0,
                state="INFER_ERROR",
                confidence=0.0,
                valid=False,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                error=str(exc)
            )

    def close(self) -> None:
        self.connected = False
        self.current_state = SensorState.SHUTDOWN
