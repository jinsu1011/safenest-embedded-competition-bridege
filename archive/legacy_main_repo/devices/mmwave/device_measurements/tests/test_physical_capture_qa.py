import importlib.util
import unittest
from pathlib import Path


TOOL = Path(__file__).parents[1] / "tools" / "physical_capture_qa.py"
SPEC = importlib.util.spec_from_file_location("physical_capture_qa", TOOL)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class PhysicalCaptureQATest(unittest.TestCase):
    def test_phase_age_summary_counts_missing_invalid_and_values(self):
        summary = MODULE.summarize_phase_age([
            {"phase_age_ms": 0},
            {"phase_age_ms": 15},
            {"phase_age_ms": None},
            {},
            {"phase_age_ms": -1},
            {"phase_age_ms": "15"},
        ])
        self.assertEqual(summary["count"], 2)
        self.assertEqual(summary["missing_or_null"], 2)
        self.assertEqual(summary["invalid"], 2)
        self.assertEqual(summary["min_ms"], 0.0)
        self.assertEqual(summary["median_ms"], 7.5)
        self.assertEqual(summary["p95_ms"], 15.0)
        self.assertEqual(summary["max_ms"], 15.0)
        self.assertEqual(summary["threshold_classification"], "PRODUCER_VALIDITY_THRESHOLD_DEFINED")
        self.assertEqual(summary["threshold_ms"], 500)
        self.assertEqual(summary["at_or_above_threshold"], 0)


if __name__ == "__main__":
    unittest.main()
