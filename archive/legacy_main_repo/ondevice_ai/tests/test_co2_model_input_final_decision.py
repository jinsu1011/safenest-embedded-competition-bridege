"""Focused tests for the CO2 pre-acquisition input decision boundary."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_co2_model_input_final_decision import (
    EXPECTED_A_FEATURES,
    EXPECTED_B_FEATURES,
    EXPECTED_DECISION,
    EXPECTED_SEEDS,
    RESULT_REL,
    validate,
)


ROOT = Path(__file__).resolve().parent.parent


def test_final_input_decision_validator_passes() -> None:
    result = validate(ROOT)
    assert result["status"] == "PASS", result["errors"]
    assert result["decision"] == EXPECTED_DECISION
    assert result["locked_test_predictive_metrics"] == 0
    assert result["physical_acquisition_status"] == "HOLD_PENDING_REDUCED_FEATURE_CANDIDATE_LOCK"


def test_result_keeps_two_explicit_candidates_and_fixed_seeds() -> None:
    result = json.loads((ROOT / RESULT_REL).read_text(encoding="utf-8"))
    assert result["arm_a_features"] == EXPECTED_A_FEATURES
    assert result["arm_b_features"] == EXPECTED_B_FEATURES
    assert result["seed_list"] == EXPECTED_SEEDS
    assert result["fixed_training_contract"]["threshold"] == 0.58
    assert result["fixed_training_contract"]["slope_profile"] == "ENDPOINT_H150"


def test_probability_metrics_use_correct_direction() -> None:
    result = json.loads((ROOT / RESULT_REL).read_text(encoding="utf-8"))
    wins = result["aggregate_results"]["seed_win_table"]
    assert wins["brier_score"]["direction"] == "LOWER_IS_BETTER"
    assert wins["brier_score"]["a_better"] == 5
    assert wins["log_loss"]["direction"] == "LOWER_IS_BETTER"
    assert wins["log_loss"]["a_better"] == 5


def test_current_b5_and_c_c2_boundaries_remain_unchanged() -> None:
    result = json.loads((ROOT / RESULT_REL).read_text(encoding="utf-8"))
    assert result["b5"]["modified"] is False
    assert result["b5"]["feature_order"] == EXPECTED_A_FEATURES
    assert result["status_boundary"]["c_c2_started"] is False
    assert result["status_boundary"]["new_physical_measurement"] is False


def test_interpretation_qualifies_predictive_result_and_threshold() -> None:
    result = json.loads((ROOT / RESULT_REL).read_text(encoding="utf-8"))
    interpretation = result["interpretation"]
    assert interpretation["four_feature_predictive_benefit_observed"] is True
    assert interpretation["reduced_feature_predictive_superiority_established"] is False
    assert interpretation["occupied_recall_tradeoff_observed"] is True
    assert interpretation["occupied_recall_advantage_threshold_conditioned"] is True
    assert interpretation["threshold_origin"] == "CURRENT_FOUR_FEATURE_B5_LINEAGE"
    assert interpretation["reduced_feature_threshold_not_finalized"] is True


def test_next_phase_is_separate_c_b6_candidate_lock() -> None:
    result = json.loads((ROOT / RESULT_REL).read_text(encoding="utf-8"))
    assert result["next_phase"]["phase_id"] == "C-B6"
    assert result["next_phase"]["authorization_required"] is True
    assert result["next_phase"]["physical_acquisition_before_lock"] is False
    assert result["recommended_next_phase"].startswith("C-B6_")


def test_historical_c_c1_protocol_points_to_c_b6_without_changing_features() -> None:
    protocol = json.loads(
        (ROOT / "datasets/co2/manifests/c_c1_measurement_protocol/protocol.json").read_text(
            encoding="utf-8"
        )
    )
    assert [entry["name"] for entry in protocol["required_features"]] == EXPECTED_A_FEATURES
    assert protocol["post_c_c1_model_input_decision"]["next_model_phase"]["phase_id"] == "C-B6"
    assert protocol["post_c_c1_model_input_decision"]["b5_threshold_0_58_inheritance_to_reduced_model"] == "FORBIDDEN"
