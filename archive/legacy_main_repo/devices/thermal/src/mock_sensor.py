#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sensors/thermal44/mock_sensor.py
Mock Thermal-44 Sensor Adapter for Mac/Simulation Environments
"""

from __future__ import annotations
import time
from pathlib import Path
import numpy as np

from shared.contracts.base_sensor import BaseSensor, SensorState
from ondevice_ai.src.inference.inference_result import InferenceResult
from ondevice_ai.src.inference.thermal_interpreter import ThermalInterpreter, ThermalPrediction


class MockThermalSensor(BaseSensor):
    def __init__(self, project_root: str | Path | None = None, manifest_path: str = "models/model_manifest.json"):
        super().__init__(sensor_id="thermal44")
        self.interpreter = ThermalInterpreter(project_root=project_root, manifest_path=manifest_path)
        self.simulated_scenario = "NORMAL"  # "NORMAL", "FALL", "FAULT"

    def connect(self) -> bool:
        self.connected = True
        self.current_state = SensorState.NORMAL
        return True

    def set_scenario(self, scenario: str) -> None:
        self.simulated_scenario = scenario

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

        if self.simulated_scenario == "FAULT":
            self.current_state = SensorState.NAN_OR_INF
            self.error_count += 1
            return InferenceResult(
                sensor_id=self.sensor_id,
                timestamp=now,
                score=0.0,
                state="FAULT",
                confidence=0.0,
                valid=False,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                error="SIMULATED_THERMAL_SENSOR_FAULT"
            )

        # Generate synthetic 80x62 frame based on scenario
        frame = np.full((62, 80), 22.0, dtype=np.float32)
        if self.simulated_scenario == "FALL":
            # High intensity fall blob in lower grid region
            frame[45:60, 20:60] = 34.5
        else: # NORMAL
            # Standing human blob in center
            frame[15:50, 30:50] = 33.0

        try:
            pred: ThermalPrediction = self.interpreter.predict(frame)
            score = 1.0 if (self.simulated_scenario == "FALL" or pred.class_index == 2) else 0.0
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
                    "simulated_scenario": self.simulated_scenario
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
