#!/usr/bin/env python3
"""Conservative Pi-side SafeNest rule engine based on documented scenarios."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class RiskLevel(str, Enum):
    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    DANGER = "DANGER"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RiskConfig:
    breath_normal_min_rpm: float
    breath_normal_max_rpm: float
    require_thermal_confirmation_for_mmwave_danger: bool
    heart_rate_used_for_risk: bool

    @classmethod
    def from_file(cls, path: Path) -> "RiskConfig":
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            breath_normal_min_rpm=float(payload["breath_normal_min_rpm"]),
            breath_normal_max_rpm=float(payload["breath_normal_max_rpm"]),
            require_thermal_confirmation_for_mmwave_danger=bool(
                payload["require_thermal_confirmation_for_mmwave_danger"]
            ),
            heart_rate_used_for_risk=bool(payload["heart_rate_used_for_risk"]),
        )


@dataclass(frozen=True)
class RiskInput:
    presence: bool | None
    breath_rate_rpm: float | None
    breath_valid: bool
    sensor_state: str
    uart_ok: bool
    thermal_human_match: bool | None
    movement_detected: bool | None
    co2_elevated: bool | None
    heart_rate_bpm: float | None = None


@dataclass(frozen=True)
class RiskResult:
    level: RiskLevel
    reason_codes: tuple[str, ...]


def _finite_positive(value: float | None) -> bool:
    return (
        isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
    )


def evaluate_risk(sample: RiskInput, config: RiskConfig) -> RiskResult:
    if not sample.uart_ok or sample.sensor_state in {"WARMUP", "UNKNOWN", "FAULT"}:
        return RiskResult(RiskLevel.UNKNOWN, ("SENSOR_NOT_VALID",))
    if sample.presence is None:
        return RiskResult(RiskLevel.UNKNOWN, ("PRESENCE_UNKNOWN",))

    if sample.presence is False:
        if sample.co2_elevated is True:
            return RiskResult(RiskLevel.CAUTION, ("EMPTY_CO2_ELEVATED",))
        if sample.co2_elevated is False:
            return RiskResult(RiskLevel.NORMAL, ("EMPTY_ENVIRONMENT_OK",))
        return RiskResult(RiskLevel.UNKNOWN, ("ENVIRONMENT_UNKNOWN",))

    if sample.thermal_human_match is False:
        return RiskResult(RiskLevel.CAUTION, ("MMWAVE_THERMAL_MISMATCH",))
    if not sample.breath_valid or not _finite_positive(sample.breath_rate_rpm):
        return RiskResult(RiskLevel.UNKNOWN, ("BREATH_UNKNOWN",))

    breath_normal = (
        config.breath_normal_min_rpm
        <= float(sample.breath_rate_rpm)
        <= config.breath_normal_max_rpm
    )
    if not breath_normal:
        if (
            not config.require_thermal_confirmation_for_mmwave_danger
            or sample.thermal_human_match is True
        ):
            return RiskResult(RiskLevel.DANGER, ("CONFIRMED_BREATH_OUT_OF_RANGE",))
        return RiskResult(RiskLevel.CAUTION, ("BREATH_OUT_OF_RANGE_NEEDS_FUSION",))

    if sample.movement_detected is False:
        return RiskResult(RiskLevel.CAUTION, ("IMMOBILITY_SUSPECTED",))
    if sample.movement_detected is None or sample.thermal_human_match is None:
        return RiskResult(RiskLevel.UNKNOWN, ("FUSION_INPUT_UNKNOWN",))
    if sample.co2_elevated is True:
        return RiskResult(RiskLevel.CAUTION, ("OCCUPIED_CO2_ELEVATED",))
    if sample.co2_elevated is None:
        return RiskResult(RiskLevel.UNKNOWN, ("ENVIRONMENT_UNKNOWN",))
    return RiskResult(RiskLevel.NORMAL, ("OCCUPIED_BREATH_AND_ENVIRONMENT_OK",))
