#!/usr/bin/env python3

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[3]
TOOL_PATH = REPO_ROOT / "devices/mmwave/tools/mmwave_20rpm_root_cause.py"
SPEC = importlib.util.spec_from_file_location("mmwave_20rpm_root_cause", TOOL_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class TestMMWave20RPMRootCause(unittest.TestCase):
    def test_pure_20rpm_signal_is_resolved_by_current_fft(self) -> None:
        timestamps = np.arange(300, dtype=np.float64) / 10.0
        values = np.sin(2.0 * np.pi * (20.0 / 60.0) * timestamps)
        result = MODULE.spectral_diagnostic(timestamps, values)
        self.assertAlmostEqual(result["selected_rpm"], 20.0, delta=0.1)
        self.assertAlmostEqual(result["observation_resolution_hz"], 1.0 / 30.0, places=9)
        self.assertAlmostEqual(result["zero_padded_bin_hz"], 10.0 / 4096.0, places=9)

    def test_real_20rpm_windows_separate_at_peak_ratio_two(self) -> None:
        target, path = MODULE.CASES[2]
        self.assertEqual(target, 20.0)
        records, measurement, bounds = MODULE.load_measurement(path)
        windows, resets = MODULE.capture_production_windows(records, measurement, bounds, target)
        self.assertEqual(len(windows), 4)
        self.assertEqual([item["peak_ratio"] >= 2.0 for item in windows], [False, False, True, True])
        self.assertLess(abs(windows[2]["selected_rpm"] - target), 2.0)
        self.assertLess(abs(windows[3]["selected_rpm"] - target), 2.0)
        self.assertEqual(resets["MMWAVE_PRESENCE_NOT_DETECTED"], 1)

    def test_gate_preserves_all_real_12_and_15rpm_windows(self) -> None:
        for target, path in MODULE.CASES[:2]:
            with self.subTest(target=target):
                records, measurement, bounds = MODULE.load_measurement(path)
                windows, _ = MODULE.capture_production_windows(records, measurement, bounds, target)
                self.assertEqual(len(windows), 6)
                self.assertTrue(all(item["peak_ratio"] >= 2.0 for item in windows))
                self.assertTrue(all(abs(item["selected_rpm"] - target) <= 2.0 for item in windows))


if __name__ == "__main__":
    unittest.main()
