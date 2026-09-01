from __future__ import annotations

import unittest
from pathlib import Path

from risk_engine import RiskConfig, RiskInput, RiskLevel, evaluate_risk


CONFIG = RiskConfig.from_file(
    Path(__file__).resolve().parents[1] / "config" / "risk_rules.json"
)


def sample(**overrides: object) -> RiskInput:
    values: dict[str, object] = {
        "presence": True,
        "breath_rate_rpm": 15.0,
        "breath_valid": True,
        "sensor_state": "VALID",
        "uart_ok": True,
        "thermal_human_match": True,
        "movement_detected": True,
        "co2_elevated": False,
    }
    values.update(overrides)
    return RiskInput(**values)  # type: ignore[arg-type]


class RiskEngineTest(unittest.TestCase):
    def test_occupied_normal(self) -> None:
        self.assertEqual(evaluate_risk(sample(), CONFIG).level, RiskLevel.NORMAL)

    def test_confirmed_abnormal_breath_is_danger(self) -> None:
        result = evaluate_risk(sample(breath_rate_rpm=8.0), CONFIG)
        self.assertEqual(result.level, RiskLevel.DANGER)

    def test_abnormal_breath_without_fusion_is_not_danger(self) -> None:
        result = evaluate_risk(
            sample(breath_rate_rpm=8.0, thermal_human_match=None), CONFIG
        )
        self.assertEqual(result.level, RiskLevel.CAUTION)

    def test_zero_breath_is_unknown_not_apnea(self) -> None:
        result = evaluate_risk(sample(breath_rate_rpm=0.0), CONFIG)
        self.assertEqual(result.level, RiskLevel.UNKNOWN)

    def test_uart_fault_is_unknown(self) -> None:
        result = evaluate_risk(sample(uart_ok=False), CONFIG)
        self.assertEqual(result.level, RiskLevel.UNKNOWN)

    def test_empty_environment_ok(self) -> None:
        result = evaluate_risk(
            sample(
                presence=False,
                breath_rate_rpm=None,
                breath_valid=False,
                thermal_human_match=False,
                movement_detected=False,
            ),
            CONFIG,
        )
        self.assertEqual(result.level, RiskLevel.NORMAL)

    def test_empty_co2_elevated_is_caution(self) -> None:
        result = evaluate_risk(
            sample(
                presence=False,
                breath_rate_rpm=None,
                breath_valid=False,
                co2_elevated=True,
            ),
            CONFIG,
        )
        self.assertEqual(result.level, RiskLevel.CAUTION)

    def test_heart_rate_does_not_change_risk(self) -> None:
        baseline = evaluate_risk(sample(heart_rate_bpm=70.0), CONFIG)
        noisy = evaluate_risk(sample(heart_rate_bpm=220.0), CONFIG)
        self.assertEqual(baseline, noisy)


if __name__ == "__main__":
    unittest.main()
