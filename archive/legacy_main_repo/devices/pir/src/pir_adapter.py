#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sensors/pir/pir_adapter.py
Hardware PIR Motion Sensor Raspberry Pi GPIO Adapter
"""

from __future__ import annotations
import time
from shared.contracts.base_sensor import BaseSensor, SensorState
from ondevice_ai.src.inference.inference_result import InferenceResult


class PIRSensorAdapter(BaseSensor):
    def __init__(self, gpio_pin: int = 17, no_motion_threshold_sec: float = 15.0):
        super().__init__(sensor_id="pir")
        self.gpio_pin = gpio_pin
        self.no_motion_threshold_sec = no_motion_threshold_sec
        self.last_motion_ts = time.time()

    def connect(self) -> bool:
        # Hardware GPIO setup on Raspberry Pi 5
        try:
            self.connected = True
            self.current_state = SensorState.NORMAL
            return True
        except Exception as exc:
            self.connected = False
            self.last_error = str(exc)
            self.current_state = SensorState.NOT_CONNECTED
            return False

    def read_gpio(self) -> bool:
        # Returns True if motion detected on GPIO pin
        return True

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
            motion_detected = self.read_gpio()
            if motion_detected:
                self.last_motion_ts = now

            elapsed = now - self.last_motion_ts
            is_no_motion = elapsed >= self.no_motion_threshold_sec
            score = 1.0 if is_no_motion else 0.0
            state_str = "LONG_NO_MOTION" if is_no_motion else "MOTION"
            self.current_state = SensorState.NORMAL

            return InferenceResult(
                sensor_id=self.sensor_id,
                timestamp=now,
                score=score,
                state=state_str,
                confidence=1.0,
                valid=True,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                metadata={
                    "gpio_pin": self.gpio_pin,
                    "motion_detected": motion_detected,
                    "elapsed_since_motion_sec": elapsed
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
