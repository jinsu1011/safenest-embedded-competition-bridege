import unittest

from scripts.mmwave_m_c0_correspondence_audit import (
    assert_freshness_estimator_consistency,
    assert_no_combined_fresh_window_total,
)


class FreshnessEstimatorGuardTests(unittest.TestCase):
    def test_low_age_cadence_undercount_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            AssertionError, "FRESHNESS_GUARD_LOW_AGE_CADENCE_UNDERCOUNT"
        ):
            assert_freshness_estimator_consistency(
                max_phase_age_ms=15.0,
                telemetry_interval_ms=100.0,
                fresh_cadence_hz=3.5,
                row_cadence_hz=10.0,
                timestamp_age_transition_count=350,
                age_interval_transition_count=350,
            )

    def test_timestamp_age_and_age_interval_divergence_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            AssertionError, "FRESHNESS_GUARD_ESTIMATOR_DIVERGENCE"
        ):
            assert_freshness_estimator_consistency(
                max_phase_age_ms=500.0,
                telemetry_interval_ms=100.0,
                fresh_cadence_hz=8.4,
                row_cadence_hz=10.0,
                timestamp_age_transition_count=840,
                age_interval_transition_count=839,
            )

    def test_combined_fresh_window_total_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            AssertionError, "FRESHNESS_GUARD_COMBINED_WINDOW_TOTAL"
        ):
            assert_no_combined_fresh_window_total(
                {
                    "valid_300_fresh_windows": 36,
                    "valid_300_fresh_windows_aggregate_reported": True,
                }
            )

    def test_valid_separate_results_pass_all_guards(self) -> None:
        result = assert_freshness_estimator_consistency(
            max_phase_age_ms=15.0,
            telemetry_interval_ms=100.0,
            fresh_cadence_hz=9.99,
            row_cadence_hz=10.0,
            timestamp_age_transition_count=999,
            age_interval_transition_count=999,
        )
        self.assertEqual(result["status"], "PASS")
        assert_no_combined_fresh_window_total(
            {
                "valid_300_fresh_windows": {
                    "PRE_PR18_LEGACY_LOGS": 27,
                    "PR18_PILOT_CAPTURE": 9,
                },
                "valid_300_fresh_windows_aggregate_reported": False,
            }
        )


if __name__ == "__main__":
    unittest.main()
