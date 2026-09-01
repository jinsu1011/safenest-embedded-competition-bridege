#!/usr/bin/env python3
"""Validate the SafeNest CO2 C-C1R reduced-feature measurement contract."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "datasets/co2/manifests/c_c1r_reduced_measurement_protocol/protocol.json"
VALIDATION_RESULT_PATH = ROOT / "datasets/co2/manifests/c_c1r_reduced_measurement_protocol/validation_result.json"
CHECKSUM_PATH = ROOT / "datasets/co2/manifests/c_c1r_reduced_measurement_protocol/checksums.sha256"
REPORT_PATH = ROOT / "docs/reports/20260815_SafeNest_CO2_C_C1R_Reduced_Feature_Measurement_Protocol_01.md"
GUIDE_PATH = ROOT / "docs/prompts/20260815_SafeNest_CO2_C_C1R_SCD40_Measurement_Operator_Guide_KO_01.md"
HISTORICAL_PROTOCOL_PATH = ROOT / "datasets/co2/manifests/c_c1_measurement_protocol/protocol.json"
B6_LOCK_PATH = ROOT / "datasets/co2/manifests/c_b6_reduced_feature_candidate/candidate_lock.json"
B6_METADATA_PATH = ROOT / "models/co2/candidates/c_b6/candidate_metadata.json"
B6_INPUT_PATH = ROOT / "models/co2/candidates/c_b6/input_contract.json"
B6_THRESHOLD_PATH = ROOT / "models/co2/candidates/c_b6/threshold_contract.json"

EXPECTED_CANDIDATE_ID = "C_B6_REDUCED_CO2_SLOPE_CANDIDATE_001"
EXPECTED_PROTOCOL_ID = "CO2_C_C1R_REDUCED_MEASUREMENT_PROTOCOL_001"
EXPECTED_LOCK_SHA256 = "5f7772ff26ca10ca95aa5216b45f3eebd96c2429b98a7ee66963ec4ea73c6fd2"
EXPECTED_LOCK_CONTENT_SHA256 = "7dd6a4c78731465d258e60d2f5e301df2f7b30dbdcc28addb99a0e72a4ec1a90"
EXPECTED_SCALER_FINGERPRINT = "a92123ad37e9b284929ba0fe53179126345d54d487ec4b3a73c910d00490a462"
EXPECTED_FLOAT_SHA256 = "fc1d4150a818473758f1f2a7c3a5f3afe604cf7c59171524f21dac3a22c3a87c"
EXPECTED_INT8_SHA256 = "c5969b367f5b5e28c4d27f1bdd6220f7d02da92e99604e3f85c9f1291e98dd3b"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_error(errors: list[str], condition: bool, message: str) -> None:
    if condition:
        errors.append(message)


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def working_tree_changed(paths: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", "--", *paths],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def validate(protocol_path: Path = PROTOCOL_PATH) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    required_paths = [
        protocol_path,
        VALIDATION_RESULT_PATH,
        CHECKSUM_PATH,
        REPORT_PATH,
        GUIDE_PATH,
        HISTORICAL_PROTOCOL_PATH,
        B6_LOCK_PATH,
        B6_METADATA_PATH,
        B6_INPUT_PATH,
        B6_THRESHOLD_PATH,
    ]
    for path in required_paths:
        add_error(errors, not path.exists(), f"MISSING_REQUIRED_ARTIFACT:{display_path(path)}")
    if errors:
        return {
            "phase": "C-C1R",
            "protocol_id": EXPECTED_PROTOCOL_ID,
            "status": "FAIL",
            "phase_result": "C_C1R_BLOCKED",
            "errors": errors,
            "warnings": warnings,
        }

    protocol = load_json(protocol_path)
    validation_result = load_json(VALIDATION_RESULT_PATH)
    lock = load_json(B6_LOCK_PATH)
    metadata = load_json(B6_METADATA_PATH)
    input_contract = load_json(B6_INPUT_PATH)
    threshold_contract = load_json(B6_THRESHOLD_PATH)
    historical = load_json(HISTORICAL_PROTOCOL_PATH)
    report = REPORT_PATH.read_text(encoding="utf-8")
    guide = GUIDE_PATH.read_text(encoding="utf-8")

    add_error(errors, protocol.get("phase") != "C-C1R", "PHASE_NOT_C_C1R")
    add_error(errors, protocol.get("protocol_id") != EXPECTED_PROTOCOL_ID, "PROTOCOL_ID_MISMATCH")
    add_error(errors, protocol.get("protocol_version") != "1.0.0", "PROTOCOL_VERSION_MISMATCH")
    add_error(errors, protocol.get("protocol_frozen") is not True, "PROTOCOL_NOT_FROZEN")
    add_error(errors, protocol.get("c_c2_started") is True, "C_C2_STARTED")
    add_error(errors, validation_result.get("protocol_id") != EXPECTED_PROTOCOL_ID, "VALIDATION_RESULT_PROTOCOL_MISMATCH")
    add_error(errors, validation_result.get("status") != "PASS", "VALIDATION_RESULT_NOT_PASS")
    add_error(errors, validation_result.get("phase_result") != "C_C1R_BLOCKED", "VALIDATION_RESULT_PHASE_MISMATCH")

    target = protocol.get("target_candidate", {})
    add_error(errors, target.get("candidate_id") != EXPECTED_CANDIDATE_ID, "TARGET_CANDIDATE_MISMATCH")
    add_error(errors, target.get("feature_order") != ["CO2", "CO2_slope"], "FEATURE_ORDER_MISMATCH")
    add_error(errors, target.get("candidate_status") != "C_B6_PASS_WITH_LIMITATIONS", "C_B6_STATUS_NOT_ACCEPTED")
    add_error(errors, target.get("threshold") != 0.43, "C_B6_THRESHOLD_MISMATCH")
    add_error(errors, target.get("threshold_source") != "TRAIN_INTERNAL_ONLY", "THRESHOLD_PROVENANCE_MISMATCH")
    add_error(errors, target.get("b5_threshold_inherited") is not False, "B5_THRESHOLD_INHERITED")
    add_error(errors, target.get("locked_test_predictive_access") is not False, "LOCKED_TEST_PREDICTIVE_ACCESS")

    model = protocol.get("model_contract", {})
    add_error(errors, model.get("required_model_sensor_fields") != ["CO2"], "MODEL_SENSOR_FIELDS_MUST_BE_CO2_ONLY")
    add_error(errors, model.get("required_derived_fields") != ["CO2_slope"], "CO2_SLOPE_NOT_REQUIRED_DERIVED_FIELD")
    add_error(errors, model.get("temperature_required_for_model") is not False, "TEMPERATURE_REQUIRED_FOR_MODEL")
    add_error(errors, model.get("humidity_required_for_model") is not False, "HUMIDITY_REQUIRED_FOR_MODEL")
    add_error(errors, model.get("co2_slope_computed_by") != "Pi_or_downstream_postprocessing", "CO2_SLOPE_NOT_PI_DERIVED")
    add_error(errors, model.get("operator_computes_co2_slope") is not False, "OPERATOR_MUST_NOT_COMPUTE_SLOPE")
    add_error(errors, model.get("sensor_node_computes_co2_slope") is not False, "SENSOR_NODE_MUST_NOT_COMPUTE_SLOPE")

    slope = protocol.get("slope_contract", {})
    add_error(errors, slope.get("profile_id") != "CO2_SLOPE_FEATURE_PROFILE_001", "SLOPE_PROFILE_CHANGED")
    add_error(errors, slope.get("method") != "ENDPOINT_H150", "H150_METHOD_CHANGED")
    add_error(errors, slope.get("history_sec") != 150, "H150_HISTORY_CHANGED")
    add_error(errors, slope.get("chronology") != "PAST_ONLY", "H150_CHRONOLOGY_CHANGED")
    add_error(errors, slope.get("minimum_samples") != 2, "H150_MINIMUM_SAMPLES_CHANGED")
    add_error(errors, slope.get("gap_reset_sec") != 90, "H150_GAP_RESET_CHANGED")
    add_error(errors, slope.get("cross_session_or_cross_block_history") != "FORBIDDEN", "CROSS_BLOCK_HISTORY_ALLOWED")

    cadence = protocol.get("cadence_contract", {})
    add_error(errors, cadence.get("effective_model_input_interval_sec") != 60, "EFFECTIVE_CADENCE_NOT_60_SEC")
    add_error(errors, cadence.get("normal_co2_export_interval_sec") != 60, "CO2_EXPORT_CADENCE_NOT_60_SEC")
    add_error(errors, cadence.get("native_sensor_cadence_separate") is not True, "NATIVE_CADENCE_CONFLATED")
    add_error(errors, cadence.get("native_scd40_cadence_claim") != "NOT_CLAIMED_BY_THIS_PROTOCOL", "NATIVE_CADENCE_OVERCLAIMED")

    freshness = protocol.get("freshness_contract", {})
    add_error(errors, freshness.get("fresh_measurement_required") is not True, "FRESH_MEASUREMENT_NOT_REQUIRED")
    add_error(errors, freshness.get("transport_freshness_is_sensor_freshness") is not False, "TRANSPORT_SENSOR_FRESHNESS_CONFLATED")
    add_error(errors, freshness.get("stale_reuse") != "FORBIDDEN", "STALE_REUSE_ALLOWED")
    add_error(errors, freshness.get("synthetic_fill") != "FORBIDDEN", "SYNTHETIC_FILL_ALLOWED")
    add_error(errors, freshness.get("forward_fill") != "FORBIDDEN", "FORWARD_FILL_ALLOWED")
    add_error(errors, freshness.get("interpolation_of_raw_sensor_events") != "FORBIDDEN", "RAW_INTERPOLATION_ALLOWED")

    chronology = protocol.get("chronology_contract", {})
    add_error(errors, chronology.get("authority") != "VERIFIED_FRESH_MEASUREMENT_CHRONOLOGY", "CHRONOLOGY_AUTHORITY_INVALID")
    add_error(errors, chronology.get("native_scd40_timestamp_required") is not False, "NATIVE_TIMESTAMP_WRONGLY_REQUIRED")
    add_error(errors, chronology.get("host_side_chronology_allowed") is not True, "HOST_CHRONOLOGY_NOT_DECLARED")
    add_error(errors, chronology.get("transport_receipt_time_role") != "RECEIPT_CHRONOLOGY_ONLY", "RECEIPT_TIME_OVERCLAIMED")
    add_error(errors, chronology.get("cross_block_history") != "FORBIDDEN", "CHRONOLOGY_CROSS_BLOCK_ALLOWED")

    ground_truth = protocol.get("ground_truth_contract", {})
    add_error(errors, ground_truth.get("independent_ground_truth_required_for_c_c2") is not True, "INDEPENDENT_GT_NOT_REQUIRED")
    add_error(errors, ground_truth.get("derived_from_co2") is not False, "GT_DERIVED_FROM_CO2")
    add_error(errors, ground_truth.get("derived_from_co2_slope") is not False, "GT_DERIVED_FROM_SLOPE")
    add_error(errors, ground_truth.get("derived_from_model_output") is not False, "GT_DERIVED_FROM_MODEL")
    add_error(errors, ground_truth.get("derived_from_filename") is not False, "GT_DERIVED_FROM_FILENAME")
    add_error(errors, ground_truth.get("derived_from_threshold_crossing") is not False, "GT_DERIVED_FROM_THRESHOLD")

    scope = protocol.get("scope", {})
    for key, message in [
        ("c_b6_model_modified", "C_B6_MODEL_MODIFIED"),
        ("c_b6_scaler_modified", "C_B6_SCALER_MODIFIED"),
        ("c_b6_threshold_modified", "C_B6_THRESHOLD_MODIFIED"),
        ("c_b6_tflite_modified", "C_B6_TFLITE_MODIFIED"),
        ("team_repository_modified", "TEAM_REPOSITORY_MODIFIED"),
        ("team_firmware_modified", "TEAM_FIRMWARE_MODIFIED"),
        ("new_physical_measurement_performed", "NEW_PHYSICAL_MEASUREMENT_PERFORMED"),
    ]:
        add_error(errors, scope.get(key) is not False, message)

    authorization = protocol.get("authorization_state", {})
    tooling = protocol.get("team_acquisition_tooling_readiness", {})
    add_error(errors, tooling.get("overall") != "HOLD", "TOOLING_READINESS_MUST_REMAIN_HOLD")
    add_error(errors, tooling.get("blocker") != "OPERATOR_HANDOFF_BLOCKED_BY_ACQUISITION_TOOLING", "TOOLING_BLOCKER_NOT_EXPLICIT")
    add_error(errors, authorization.get("protocol_state") != "PROTOCOL_FROZEN", "PROTOCOL_AUTHORIZATION_STATE_INVALID")
    add_error(errors, authorization.get("operator_guide_state") != "HOLD_PENDING_ACQUISITION_TOOLING_CORRECTION", "OPERATOR_GUIDE_PREMATURELY_READY")
    add_error(errors, authorization.get("physical_acquisition_state") != "HOLD", "PHYSICAL_ACQUISITION_PREMATURELY_AUTHORIZED")
    add_error(errors, authorization.get("c_c2_state") != "NOT_STARTED", "C_C2_STATE_INVALID")
    add_error(errors, protocol.get("physical_acquisition_authorized") is not False, "PHYSICAL_ACQUISITION_AUTHORIZED_WITH_BLOCKER")
    add_error(errors, protocol.get("operator_handoff_ready") is not False, "OPERATOR_HANDOFF_READY_WITH_BLOCKER")

    add_error(errors, lock.get("candidate_id") != EXPECTED_CANDIDATE_ID, "LIVE_LOCK_CANDIDATE_MISMATCH")
    add_error(errors, lock.get("feature_order") != ["CO2", "CO2_slope"], "LIVE_LOCK_FEATURE_MISMATCH")
    add_error(errors, lock.get("status") != "C_B6_PASS_WITH_LIMITATIONS", "LIVE_LOCK_STATUS_MISMATCH")
    add_error(errors, lock.get("threshold") != 0.43, "LIVE_LOCK_THRESHOLD_MISMATCH")
    add_error(errors, lock.get("threshold_source") != "TRAIN_INTERNAL_ONLY", "LIVE_LOCK_THRESHOLD_SOURCE_MISMATCH")
    add_error(errors, lock.get("b5_threshold_inherited") is not False, "LIVE_LOCK_B5_INHERITED")
    add_error(errors, lock.get("locked_test_predictive_access") is not False, "LIVE_LOCK_TEST_ACCESS")
    add_error(errors, input_contract.get("candidate_id") != EXPECTED_CANDIDATE_ID, "LIVE_INPUT_CANDIDATE_MISMATCH")
    add_error(errors, input_contract.get("feature_order") != ["CO2", "CO2_slope"], "LIVE_INPUT_FEATURE_MISMATCH")
    add_error(errors, input_contract.get("humidity_included") is not False, "LIVE_INPUT_HUMIDITY_INCLUDED")
    add_error(errors, threshold_contract.get("threshold") != 0.43, "LIVE_THRESHOLD_MISMATCH")
    add_error(errors, threshold_contract.get("b5_threshold_inherited") is not False, "LIVE_THRESHOLD_B5_INHERITED")

    add_error(errors, historical.get("protocol_id") != "CO2_C_C1_MEASUREMENT_PROTOCOL_001", "HISTORICAL_C_C1_PROTOCOL_REWRITTEN")
    add_error(errors, historical.get("protocol_version") != "1.0.0", "HISTORICAL_C_C1_VERSION_CHANGED")

    add_error(errors, "C_C1R_BLOCKED" not in report, "REPORT_STATUS_MISSING")
    add_error(errors, "OPERATOR_HANDOFF_BLOCKED_BY_ACQUISITION_TOOLING" not in report, "REPORT_BLOCKER_MISSING")
    add_error(errors, "CO2 + Pi-derived CO2_slope" not in report, "REPORT_REDUCED_CONTRACT_MISSING")
    add_error(errors, "60 seconds" not in report, "REPORT_CADENCE_MISSING")
    add_error(errors, "HOLD_PENDING_ACQUISITION_TOOLING_CORRECTION" not in guide, "GUIDE_HOLD_STATUS_MISSING")
    add_error(errors, "AI용 필수 센서값: CO2" not in guide, "GUIDE_CO2_REQUIREMENT_MISSING")
    add_error(errors, "온도: AI 필수값 아님" not in guide, "GUIDE_TEMPERATURE_OPTIONAL_MISSING")
    add_error(errors, "습도: AI 필수값 아님" not in guide, "GUIDE_HUMIDITY_OPTIONAL_MISSING")
    add_error(errors, "STALE_REUSE = 금지" not in guide, "GUIDE_STALE_RULE_MISSING")

    add_error(errors, sha256(B6_LOCK_PATH) != EXPECTED_LOCK_SHA256, "B6_LOCK_SHA256_CHANGED")
    add_error(errors, target.get("candidate_lock_sha256") != EXPECTED_LOCK_SHA256, "PROTOCOL_LOCK_SHA256_MISMATCH")
    add_error(errors, target.get("candidate_lock_content_sha256") != EXPECTED_LOCK_CONTENT_SHA256, "PROTOCOL_LOCK_CONTENT_FINGERPRINT_MISMATCH")
    add_error(errors, target.get("scaler_fingerprint") != EXPECTED_SCALER_FINGERPRINT, "PROTOCOL_SCALER_FINGERPRINT_MISMATCH")
    add_error(errors, target.get("float_tflite_sha256") != EXPECTED_FLOAT_SHA256, "PROTOCOL_FLOAT_HASH_MISMATCH")
    add_error(errors, target.get("int8_tflite_sha256") != EXPECTED_INT8_SHA256, "PROTOCOL_INT8_HASH_MISMATCH")

    changed_b6 = working_tree_changed([
        "datasets/co2/manifests/c_b6_reduced_feature_candidate",
        "models/co2/candidates/c_b6",
    ])
    add_error(errors, bool(changed_b6), f"C_B6_WORKTREE_CHANGED:{','.join(changed_b6)}")

    checksum_lines = {
        line.strip()
        for line in CHECKSUM_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    checksum_targets = [
        PROTOCOL_PATH,
        VALIDATION_RESULT_PATH,
        REPORT_PATH,
        GUIDE_PATH,
        ROOT / "scripts/validate_co2_c_c1r_reduced_measurement_protocol.py",
        ROOT / "tests/test_co2_c_c1r_reduced_measurement_protocol.py",
    ]
    for path in checksum_targets:
        relative = path.relative_to(ROOT).as_posix()
        expected_line = f"{sha256(path)}  {relative}"
        add_error(errors, expected_line not in checksum_lines, f"CHECKSUM_MISMATCH:{relative}")

    return {
        "phase": "C-C1R",
        "protocol_id": protocol.get("protocol_id"),
        "protocol_version": protocol.get("protocol_version"),
        "status": "PASS" if not errors else "FAIL",
        "phase_result": protocol.get("phase_result"),
        "protocol_frozen": protocol.get("protocol_frozen"),
        "operator_guide_status": protocol.get("operator_guide_status"),
        "physical_acquisition_authorized": protocol.get("physical_acquisition_authorized"),
        "c_c2_started": protocol.get("scope", {}).get("c_c2_started"),
        "candidate_id": target.get("candidate_id"),
        "c_b6_candidate_status": target.get("candidate_status"),
        "errors": errors,
        "warnings": warnings,
    }


def main() -> int:
    result = validate()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
