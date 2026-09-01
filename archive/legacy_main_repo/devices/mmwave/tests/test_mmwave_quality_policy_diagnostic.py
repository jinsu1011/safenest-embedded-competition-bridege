#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_ROOT = REPO_ROOT / "devices/mmwave/tools"
for search_path in (REPO_ROOT, TOOLS_ROOT):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

from mmwave_quality_policy_diagnostic import POLICIES, QualityPolicy


class TestQualityPolicy(unittest.TestCase):
    def test_candidate_a_rejects_weak_then_recovers_without_state_reset(self):
        policy = QualityPolicy(POLICIES["candidate_a_rolling_peak"])
        rejected = policy.decide(14.0, 1.6)
        recovered = policy.decide(19.5, 2.1)
        self.assertFalse(rejected.accept)
        self.assertEqual(rejected.reason, "MMWAVE_SPECTRAL_QUALITY_WEAK")
        self.assertTrue(recovered.accept)
        self.assertEqual(policy.previous_valid_rpm, 19.5)

    def test_candidate_b_only_relaxes_for_temporally_consistent_rate(self):
        policy = QualityPolicy(POLICIES["candidate_b_temporal"])
        self.assertTrue(policy.decide(15.0, 3.0).accept)
        accepted = policy.decide(16.8, 1.6)
        rejected = policy.decide(20.0, 1.6)
        self.assertTrue(accepted.accept)
        self.assertEqual(accepted.reason, "TEMPORAL_ACCEPT")
        self.assertFalse(rejected.accept)

    def test_candidate_b_rejects_even_strong_abrupt_jump(self):
        policy = QualityPolicy(POLICIES["candidate_b_temporal"])
        self.assertTrue(policy.decide(20.0, 5.0).accept)
        self.assertFalse(policy.decide(14.0, 3.0).accept)

    def test_candidate_c_uses_remain_threshold_until_physical_reset(self):
        policy = QualityPolicy(POLICIES["candidate_c_hysteresis"])
        self.assertTrue(policy.decide(15.0, 2.1).accept)
        remained = policy.decide(15.5, 1.6)
        self.assertTrue(remained.accept)
        self.assertEqual(remained.threshold, 1.5)
        policy.physical_reset()
        entered = policy.decide(15.5, 1.6)
        self.assertFalse(entered.accept)
        self.assertEqual(entered.threshold, 2.0)

    def test_baseline_never_rejects_finite_estimate(self):
        policy = QualityPolicy(POLICIES["baseline"])
        self.assertTrue(policy.decide(10.0, 1.01).accept)

    def test_candidate_d_requires_dominance_over_competing_peak(self):
        policy = QualityPolicy(POLICIES["candidate_d_peak_dominance"])
        self.assertFalse(policy.decide(7.0, 4.2, 1.75).accept)
        self.assertTrue(policy.decide(20.0, 5.4, 2.3).accept)

    def test_candidate_e_uses_temporal_hold_and_strong_reanchor(self):
        policy = QualityPolicy(POLICIES["candidate_e_temporal_reanchor"])
        self.assertFalse(policy.decide(7.0, 4.3).accept)
        self.assertTrue(policy.decide(20.0, 5.2).accept)
        self.assertTrue(policy.decide(18.5, 1.6).accept)
        self.assertFalse(policy.decide(12.0, 4.9).accept)
        decision = policy.decide(12.0, 5.1)
        self.assertTrue(decision.accept)
        self.assertEqual(decision.reason, "STRONG_REANCHOR_ACCEPT")


if __name__ == "__main__":
    unittest.main()
