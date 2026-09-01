"""Focused tests for the SafeNest CO2 C-B6 candidate boundary."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_co2_c_b6_candidate import (
    CANDIDATE_ID,
    FEATURE_ORDER,
    RESULT_REL,
    validate,
)


ROOT = Path(__file__).resolve().parent.parent


def load_result() -> dict:
    return json.loads((ROOT / RESULT_REL).read_text(encoding="utf-8"))


def test_c_b6_validator_passes() -> None:
    result = validate(ROOT)
    assert result["status"] == "PASS", result["errors"]
    assert result["candidate_id"] == CANDIDATE_ID
    assert result["locked_test_predictive_access"] is False
    assert result["b5_modified"] is False


def test_reduced_feature_contract_is_exactly_two_features() -> None:
    result = load_result()
    assert result["features"] == FEATURE_ORDER
    assert "Temperature" not in result["features"]
    assert "Humidity" not in result["features"]
    assert len(result["scaler"]["mean"]) == 2
    assert len(result["scaler"]["scale"]) == 2


def test_threshold_is_train_internal_and_not_b5_inherited() -> None:
    result = load_result()
    threshold = result["threshold"]
    assert threshold["source"] == "TRAIN_INTERNAL_ONLY"
    assert threshold["b5_threshold_inherited"] is False
    assert threshold["value"] != 0.58
    policy = json.loads((ROOT / threshold["policy_path"]).read_text(encoding="utf-8"))
    assert policy["status"] == "PREDECLARED_BEFORE_THRESHOLD_SELECTION"
    assert policy["source"] == "TRAIN_INTERNAL_ONLY"
    assert policy["outer_validation_rows_used"] == 0


def test_locked_test_guard_and_physical_boundaries() -> None:
    result = load_result()
    locked = result["locked_test"]
    assert locked["feature_rows_decoded"] == 0
    assert locked["target_rows_decoded"] == 0
    assert locked["predictive_metrics"] == 0
    assert locked["threshold_selection"] == 0
    assert locked["model_selection"] == 0
    assert result["physical_acquisition"]["started"] is False
    assert result["c_c2"]["started"] is False
    assert result["c_d"]["authorized"] is False


def test_candidate_metadata_and_lock_are_separate_from_b5() -> None:
    result = load_result()
    metadata = json.loads((ROOT / "models/co2/candidates/c_b6/candidate_metadata.json").read_text(encoding="utf-8"))
    lock = json.loads((ROOT / "datasets/co2/manifests/c_b6_reduced_feature_candidate/candidate_lock.json").read_text(encoding="utf-8"))
    assert metadata["candidate_id"] == CANDIDATE_ID
    assert metadata["feature_order"] == FEATURE_ORDER
    assert "c_b5" not in metadata["reference_model_path"]
    assert lock["candidate_id"] == CANDIDATE_ID
    assert lock["feature_order"] == FEATURE_ORDER
    assert lock["historical_b5_modified"] is False
    assert all("c_b5" not in artifact["path"] for artifact in lock["artifacts"])
    assert result["b5"]["modified"] is False


def test_tflite_contract_is_two_feature_full_integer_int8() -> None:
    result = load_result()
    float_contract = result["tflite"]["float_contract"]
    int8_contract = result["tflite"]["int8_contract"]
    assert float_contract["input_shape"] == [1, 2]
    assert int8_contract["input_shape"] == [1, 2]
    assert int8_contract["input_dtype"] == "int8"
    assert int8_contract["output_dtype"] == "int8"
    assert int8_contract["full_integer_ops"] is True
    assert int8_contract["input_quantization"]["scale"] > 0
    assert int8_contract["output_quantization"]["scale"] > 0


def test_determinism_and_quantization_diagnostics_are_recorded() -> None:
    result = load_result()
    determinism = json.loads((ROOT / "datasets/co2/manifests/c_b6_reduced_feature_candidate/determinism_report.json").read_text(encoding="utf-8"))
    quantization = result["quantization"]
    assert determinism["data_pipeline_determinism"] == "PASS"
    assert determinism["threshold_determinism"] == "PASS"
    assert determinism["float_tflite_bytes_identical_on_repeat"] is True
    assert determinism["int8_tflite_bytes_identical_on_repeat"] is True
    assert quantization["gate"]["status"] == "PASS"
    assert set(quantization["saturation"]["train"]["per_feature"]) == set(FEATURE_ORDER)
    assert set(quantization["saturation"]["validation"]["per_feature"]) == set(FEATURE_ORDER)
