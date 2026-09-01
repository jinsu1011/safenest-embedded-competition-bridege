#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
shared/contracts/base_sensor.py
SafeNest V4 On-Device AI BaseSensor Contract & State Machine
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass
import time
from typing import Optional

from ondevice_ai.src.inference.inference_result import InferenceResult


class SensorState(Enum):
    NORMAL = auto()
    NOT_CONNECTED = auto()
    READ_TIMEOUT = auto()
    INVALID_FORMAT = auto()
    NAN_OR_INF = auto()
    OUT_OF_BOUNDS = auto()
    INFER_FAILED = auto()
    STALE = auto()
    SHUTDOWN = auto()


@dataclass
class SensorHealth:
    sensor_id: str
    connected: bool
    state: SensorState
    last_read_ts: float
    age_sec: float
    read_count: int
    error_count: int
    last_error: Optional[str] = None


class BaseSensor(ABC):
    def __init__(self, sensor_id: str, timeout_sec: float = 2.0, stale_sec: float = 5.0):
        self.sensor_id = sensor_id
        self.timeout_sec = timeout_sec
        self.stale_sec = stale_sec
        self.connected = False
        self.last_read_ts = 0.0
        self.read_count = 0
        self.error_count = 0
        self.last_error: Optional[str] = None
        self.current_state = SensorState.NOT_CONNECTED

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection to physical sensor hardware or mock interface."""
        pass

    @abstractmethod
    def read(self) -> InferenceResult:
        """Read sensor telemetry, execute preprocessing/inference, and return InferenceResult."""
        pass

    def health(self) -> SensorHealth:
        now = time.time()
        age = now - self.last_read_ts if self.last_read_ts > 0 else 9999.0
        if age > self.stale_sec and self.connected:
            self.current_state = SensorState.STALE

        return SensorHealth(
            sensor_id=self.sensor_id,
            connected=self.connected,
            state=self.current_state,
            last_read_ts=self.last_read_ts,
            age_sec=age,
            read_count=self.read_count,
            error_count=self.error_count,
            last_error=self.last_error
        )

    @abstractmethod
    def close(self) -> None:
        """Safely release SPI, I2C, Serial UART, GPIO, or memory resources."""
        pass
