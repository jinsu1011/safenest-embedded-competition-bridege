#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sensors/mmwave/mock_sensor.py
Mock mmWave Radar Sensor Adapter for Simulation / Mac Testing
"""

from __future__ import annotations
import time
from pathlib import Path
import numpy as np

from shared.contracts.base_sensor import BaseSensor, SensorState
from ondevice_ai.src.inference.inference_result import InferenceResult
from ondevice_ai.src.inference.mmwave_interpreter import MMWaveInterpreter, MMWavePrediction


class MockMMWaveSensor(BaseSensor):
    def __init__(self, project_root: str | Path | None = None, manifest_path: str = "models/model_manifest.json"):
        super().__init__(sensor_id="mmwave")
        self.interpreter = MMWaveInterpreter(project_root=project_root, manifest_path=manifest_path)
        self.simulated_scenario = "NORMAL"  # "NORMAL", "APNEA", "ABNORMAL", "FAULT"

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
                error="SIMULATED_MMWAVE_SENSOR_FAULT"
            )

        # Generate synthetic 300-sample (30s) respiration phase waveform
        t = np.linspace(0, 30, 300, dtype=np.float32)
        if self.simulated_scenario == "APNEA":
            # Flat line (breath cessation)
            window = np.full(300, 1.25, dtype=np.float32) + np.random.normal(0, 0.005, 300).astype(np.float32)
        elif self.simulated_scenario == "ABNORMAL":
            # High frequency / rapid respiration
            window = 2.5 * np.sin(2 * np.pi * 0.8 * t).astype(np.float32)
        else: # NORMAL
            # Standard 0.25Hz respiration (~15 RPM)
            window = 2.5 * np.sin(2 * np.pi * 0.25 * t).astype(np.float32)

        try:
            pred: MMWavePrediction = self.interpreter.predict(window)
            # Map prediction class to score S1: 0 (NORMAL) -> 0.0, 1 (ABNORMAL) -> 0.5, 2 (APNEA) -> 1.0
            if self.simulated_scenario == "APNEA" or pred.class_index == 2:
                score = 1.0
                state_str = "APNEA"
            elif self.simulated_scenario == "ABNORMAL" or pred.class_index == 1:
                score = 0.5
                state_str = "RAPID_OR_ABNORMAL"
            else:
                score = 0.0
                state_str = "NORMAL"

            self.current_state = SensorState.NORMAL

            return InferenceResult(
                sensor_id=self.sensor_id,
                timestamp=now,
                score=score,
                state=state_str,
                confidence=pred.confidence,
                valid=True,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                metadata={
                    "model_id": pred.model_id,
                    "class_index": pred.class_index,
                    "probabilities": pred.probabilities,
                    "fallback_used": pred.fallback_used
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
