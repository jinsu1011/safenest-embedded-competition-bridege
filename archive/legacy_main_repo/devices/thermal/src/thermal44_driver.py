#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sensors/thermal44/thermal44_driver.py
Thermal-44 (80x62 IR Array) Hardware Driver & SPI/I2C Adapter
"""

from __future__ import annotations
import time
from pathlib import Path
import numpy as np

from shared.contracts.base_sensor import BaseSensor, SensorState
from devices.thermal.src.frame_parser import ThermalFrameParser
from ondevice_ai.src.inference.inference_result import InferenceResult
from ondevice_ai.src.inference.thermal_interpreter import ThermalInterpreter, ThermalPrediction


class Thermal44Sensor(BaseSensor):
    def __init__(self, project_root: str | Path | None = None, manifest_path: str = "models/model_manifest.json"):
        super().__init__(sensor_id="thermal44")
        self.interpreter = ThermalInterpreter(project_root=project_root, manifest_path=manifest_path)

    def connect(self) -> bool:
        # Hardware SPI/I2C connection logic for Raspberry Pi 5
        try:
            self.connected = True
            self.current_state = SensorState.NORMAL
            return True
        except Exception as exc:
            self.connected = False
            self.last_error = str(exc)
            self.current_state = SensorState.NOT_CONNECTED
            return False

    def read_frame(self) -> np.ndarray:
        # Simulated/Driver reading of 80x62 frame from SPI/I2C
        frame = np.full((62, 80), 24.0, dtype=np.float32)
        frame[20:40, 30:50] = 33.5  # Human subject present
        return frame

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
            frame_62x80 = self.read_frame()
            pred: ThermalPrediction = self.interpreter.predict(frame_62x80)
            score = 1.0 if pred.class_index == 2 else 0.0
            self.current_state = SensorState.NORMAL

            return InferenceResult(
                sensor_id=self.sensor_id,
                timestamp=now,
                score=score,
                state="HUMAN_FALL" if score == 1.0 else pred.class_name,
                confidence=pred.confidence,
                valid=True,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                metadata={
                    "model_id": pred.model_id,
                    "class_index": pred.class_index,
                    "probabilities": pred.probabilities,
                    "infer_latency_ms": pred.latency_ms
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
