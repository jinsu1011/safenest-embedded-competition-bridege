#!/usr/bin/env python3
"""Regression tests for the LCD state-to-buzzer integration."""

from __future__ import annotations

import sys
import types
import unittest
from unittest.mock import patch

import server


class FakeTonalBuzzer:
    def __init__(self, pin: int) -> None:
        self.pin = pin
        self.played: list[float] = []
        self.stop_count = 0
        self.closed = False

    def play(self, frequency_hz: float) -> None:
        self.played.append(frequency_hz)

    def stop(self) -> None:
        self.stop_count += 1

    def close(self) -> None:
        self.closed = True


class RecordingBuzzer:
    def __init__(self) -> None:
        self.emergency_values: list[bool] = []

    def set_emergency(self, emergency: bool) -> None:
        self.emergency_values.append(emergency)


class BuzzerControllerTests(unittest.TestCase):
    def test_tonal_buzzer_turns_on_and_off(self) -> None:
        fake_gpiozero = types.ModuleType("gpiozero")
        fake_gpiozero.TonalBuzzer = FakeTonalBuzzer
        with patch.dict(sys.modules, {"gpiozero": fake_gpiozero}):
            buzzer = server.BuzzerController(pin=18, frequency_hz=880.0)

        device = buzzer._device
        self.assertIsInstance(device, FakeTonalBuzzer)
        self.assertEqual(device.pin, 18)
        buzzer.set_emergency(True)
        self.assertEqual(device.played, [880.0])
        self.assertTrue(buzzer.status()["sounding"])
        buzzer.set_emergency(False)
        self.assertFalse(buzzer.status()["sounding"])
        buzzer.close()
        self.assertTrue(device.closed)

    def test_state_change_drives_emergency_and_clear(self) -> None:
        original_state = server.APP_STATE.copy()
        buzzer = RecordingBuzzer()
        try:
            with patch.object(server, "persist_state"):
                response = server.apply_state_change(buzzer, "emergency", None)
                self.assertEqual(response["state"], "emergency")
                response = server.apply_state_change(buzzer, "normal-empty", None)
                self.assertEqual(response["state"], "normal-empty")
            self.assertEqual(buzzer.emergency_values, [True, False])
        finally:
            server.APP_STATE.clear()
            server.APP_STATE.update(original_state)


if __name__ == "__main__":
    unittest.main()
