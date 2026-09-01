#!/usr/bin/env python3
"""Fail-closed validator for the SafeNest CO2 C-B6 candidate lock."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


ROOT = Path(__file__).resolve().parent.parent
PHASE_ID = "C-B6"
CANDIDATE_ID = "C_B6_REDUCED_CO2_SLOPE_CANDIDATE_001"
FEATURE_ORDER = ["CO2", "CO2_slope"]
SLOPE_PROFILE = "CO2_SLOPE_FEATURE_PROFILE_001"
TRAIN_COUNT = 8140
VALIDATION_COUNT = 2662
LOCKED_TEST_COUNT = 9749
TRAIN_FINGERPRINT = "492ca1f67e44b4a2018b743ec0fc3d20b418f7823d5f2643d8c90b0d39de8fab"
VALIDATION_FINGERPRINT = "19321e57fe72f6482b3c7b5d3714d21e9c13b753173ceb56ea694524ac6529ef"
LOCKED_TEST_FINGERPRINT = "0bac8dc1affae1de48ea68f01e866508ea19f31e194a7c0dccbf617e529344e7"
HISTORICAL_B5_THRESHOLD = 0.58

ARTIFACT_REL = "datasets/co2/manifests/c_b6_reduced_feature_candidate"
CANDIDATE_REL = "models/co2/candidates/c_b6"
RESULT_REL = f"{ARTIFACT_REL}/c_b6_result.json"
LOCK_REL = f"{ARTIFACT_REL}/candidate_lock.json"
CHECKSUMS_REL = f"{ARTIFACT_REL}/checksums.sha256"
REPORT_REL = "docs/reports/20260815_SafeNest_CO2_C_B6_Reduced_Feature_Candidate_Development_and_Lock_01.md"
B5_LOCK_REL = "datasets/co2/manifests/c_b5_robustness_final_lock/final_candidate_lock.json"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def stable_sha256(payload: Any) -> str:
    blob = json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(condition: bool, message: str, errors: List[str]) -> None:
    if not condition:
        errors.append(message)


def portable_path(value: Any) -> bool:
    text = str(value)
    return bool(text) and not text.startswith("/") and "\\" not in text and not text.startswith("~")


def validate_checksums(root: Path, errors: List[str]) -> None:
    path = root / CHECKSUMS_REL
    check(path.is_file(), "missing C-B6 checksum manifest", errors)
    if not path.is_file():
        return
    seen = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            digest, rel = line.split("  ", 1)
        except ValueError:
            errors.append(f"malformed checksum line {line_number}")
            continue
        check(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, f"invalid checksum digest line {line_number}", errors)
        check(portable_path(rel), f"non-portable checksum path: {rel}", errors)
        check(rel != CHECKSUMS_REL, "C-B6 checksum manifest hashes itself", errors)
        target = root / rel
        check(target.is_file(), f"missing checksum target: {rel}", errors)
        if target.is_file():
            check(file_sha256(target) == digest, f"checksum mismatch: {rel}", errors)
        seen.add(rel)
    required = {
        RESULT_REL,
        LOCK_REL,
        REPORT_REL,
        "scripts/audit_co2_c_b6_candidate.py",
        "scripts/validate_co2_c_b6_candidate.py",
        "tests/test_co2_c_b6_candidate.py",
    }
    check(required.issubset(seen), "C-B6 checksum coverage is incomplete", errors)


def validate_b5_immutability(root: Path, result: Mapping[str, Any], errors: List[str]) -> None:
    lock_path = root / B5_LOCK_REL
    check(lock_path.is_file(), "historical B5 lock is missing", errors)
    if not lock_path.is_file():
        return
    b5_lock = load_json(lock_path)
    check(b5_lock.get("final_lock_profile_id") == "CO2_B5_FINAL_OFFLINE_CANDIDATE_LOCK_001", "B5 lock profile drift", errors)
    check(b5_lock.get("final_lock_sha256") == "a020d462e0d359e0c9faa9bb680387119f095cb102243d7e6c223d76a801b627", "B5 lock content identity drift", errors)
    evidence = result.get("b5", {}).get("immutability", {})
    check(result.get("b5", {}).get("modified") is False, "B5 modified flag is not false", errors)
    check(evidence.get("modified") is False, "B5 immutability evidence is not false", errors)
    check(file_sha256(lock_path) == evidence.get("final_lock_file_sha256"), "B5 final lock file changed", errors)
    selected = evidence.get("selected_frozen_artifact_hashes") or {}
    for rel, expected in selected.items():
        target = root / rel
        check(target.is_file(), f"B5 selected artifact missing: {rel}", errors)
        if target.is_file():
            check(file_sha256(target) == expected, f"B5 selected artifact mutated: {rel}", errors)
    check("models/co2/candidates/c_b5" not in str(result.get("reference_model", {}).get("path", "")), "C-B6 reference points into B5", errors)


def validate(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    errors: List[str] = []
    result_path = root / RESULT_REL
    check(result_path.is_file(), f"missing result: {RESULT_REL}", errors)
    if not result_path.is_file():
        return {"status": "FAIL", "errors": errors}
    result = load_json(result_path)
    check(result.get("phase_id") == PHASE_ID, "phase ID drift", errors)
    check(result.get("candidate_id") == CANDIDATE_ID, "candidate ID drift", errors)
    check(result.get("status") in {"C_B6_LOCKED_FOR_DEVICE_DOMAIN_VALIDATION", "C_B6_PASS_WITH_LIMITATIONS"}, "invalid C-B6 status", errors)
    check(result.get("features") == FEATURE_ORDER, "feature order drift", errors)
    check(not set(result.get("features", [])) & {"Temperature", "Humidity", "Light"}, "forbidden feature in reduced candidate", errors)

    slope = result.get("slope_profile") or {}
    check(slope.get("profile_id") == SLOPE_PROFILE, "slope profile drift", errors)
    check(slope.get("method") == "ENDPOINT_DIFFERENCE", "slope method drift", errors)
    check(slope.get("history_seconds") == 150.0, "slope history drift", errors)
    check(slope.get("max_internal_gap_seconds") == 90.0, "slope gap policy drift", errors)
    check(slope.get("causality") == "PAST_ONLY", "slope causality drift", errors)

    dataset = result.get("dataset") or {}
    for key, expected in (("train_rows", TRAIN_COUNT), ("validation_rows", VALIDATION_COUNT), ("locked_test_rows", LOCKED_TEST_COUNT), ("train_fingerprint", TRAIN_FINGERPRINT), ("validation_fingerprint", VALIDATION_FINGERPRINT), ("locked_test_membership_fingerprint", LOCKED_TEST_FINGERPRINT)):
        check(dataset.get(key) == expected, f"dataset lineage drift: {key}", errors)
    check(dataset.get("random_row_split") is False, "random row split was enabled", errors)
    check(dataset.get("synthetic_fixture_used") is False, "synthetic fixture used as real source", errors)

    scaler = result.get("scaler") or {}
    check(scaler.get("feature_order") == FEATURE_ORDER, "scaler feature order drift", errors)
    check(scaler.get("fit_source") == "TRAIN_ONLY", "scaler fit source is not TRAIN_ONLY", errors)
    check(len(scaler.get("mean", [])) == 2 and len(scaler.get("scale", [])) == 2, "scaler dimension drift", errors)
    scaler_path = root / str(scaler.get("path", ""))
    check(scaler_path.is_file(), "new scaler artifact missing", errors)
    if scaler_path.is_file():
        scaler_artifact = load_json(scaler_path)
        fp = scaler_artifact.get("fingerprint")
        payload = {key: value for key, value in scaler_artifact.items() if key != "fingerprint"}
        check(fp == stable_sha256(payload), "new scaler fingerprint mismatch", errors)
        check(scaler_artifact.get("feature_order") == FEATURE_ORDER, "scaler artifact feature order drift", errors)
        check(scaler_artifact.get("fit_population") == "ORIGINAL_NATURALLY_DISTRIBUTED_TRAIN_ONLY", "scaler artifact population drift", errors)
        check(scaler_artifact.get("validation_fit_rows") == 0 and scaler_artifact.get("locked_test_fit_rows") == 0, "scaler leakage counters are nonzero", errors)
        check(fp == scaler.get("fingerprint"), "result scaler fingerprint mismatch", errors)

    training = result.get("training_contract") or {}
    check(training.get("model_family") == "LINEAR_LOGISTIC", "model family drift", errors)
    check(training.get("imbalance_strategy") == "BALANCED_RANDOM_OVERSAMPLE", "imbalance policy drift", errors)
    check(training.get("feature_search") is False and training.get("hyperparameter_search") is False and training.get("resplit") is False, "C-B6 reopened selection/search", errors)

    threshold = result.get("threshold") or {}
    check(isinstance(threshold.get("value"), (int, float)) and 0.05 <= float(threshold.get("value")) <= 0.95, "invalid final threshold", errors)
    check(threshold.get("source") == "TRAIN_INTERNAL_ONLY", "threshold source is not TRAIN_INTERNAL_ONLY", errors)
    check(threshold.get("b5_threshold_inherited") is False, "B5 threshold was inherited", errors)
    if threshold.get("value") == HISTORICAL_B5_THRESHOLD:
        check(threshold.get("coincidental_match_to_b5") is True, "0.58 was not qualified as a coincidental internal result", errors)
    policy_path = root / str(threshold.get("policy_path", ""))
    result_path_threshold = root / str(threshold.get("result_path", ""))
    check(policy_path.is_file() and result_path_threshold.is_file(), "threshold policy/result missing", errors)
    if policy_path.is_file() and result_path_threshold.is_file():
        policy = load_json(policy_path)
        threshold_result = load_json(result_path_threshold)
        check(policy.get("status") == "PREDECLARED_BEFORE_THRESHOLD_SELECTION", "threshold policy was not predeclared", errors)
        check(policy.get("source") == "TRAIN_INTERNAL_ONLY" and policy.get("threshold_source") == "TRAIN_INTERNAL_ONLY", "threshold policy source drift", errors)
        check(policy.get("outer_validation_rows_used") == 0 and policy.get("locked_test_rows_used") == 0, "threshold policy leakage counters are nonzero", errors)
        check(policy.get("historical_b5_threshold") == HISTORICAL_B5_THRESHOLD and policy.get("b5_threshold_inheritance") == "FORBIDDEN", "B5 threshold policy drift", errors)
        check((policy.get("objective") or {}).get("minimum_occupied_recall") == 0.90, "threshold recall floor drift", errors)
        check(threshold_result.get("selected_threshold") == threshold.get("value"), "selected threshold mismatch", errors)
        check(threshold_result.get("threshold_source") == "TRAIN_INTERNAL_ONLY" and threshold_result.get("b5_threshold_inherited") is False, "threshold result provenance drift", errors)
        check(threshold_result.get("oof_population") == "TRAIN" and threshold_result.get("oof_rows") == TRAIN_COUNT, "OOF population drift", errors)
        check(threshold_result.get("validation_rows_used") == 0 and threshold_result.get("locked_test_rows_used") == 0, "threshold result leakage counters are nonzero", errors)

    locked = result.get("locked_test") or {}
    for key in ("feature_rows_decoded", "target_rows_decoded", "predictive_metrics", "threshold_selection", "model_selection", "hyperparameter_selection"):
        check(locked.get(key) == 0, f"LOCKED_TEST access drift: {key}", errors)
    check(locked.get("predictive_access") is False, "LOCKED_TEST predictive access is not false", errors)

    tflite = result.get("tflite") or {}
    for key in ("float_path", "int8_path", "float_sha256", "int8_sha256"):
        check(key in tflite, f"missing TFLite identity: {key}", errors)
    for label, contract, expected_dtype in (("float", tflite.get("float_contract") or {}, "float32"), ("int8", tflite.get("int8_contract") or {}, "int8")):
        check(contract.get("input_shape") == [1, 2] and contract.get("output_shape") == [1, 1], f"{label} TFLite shape drift", errors)
        check(contract.get("input_dtype") == expected_dtype and contract.get("output_dtype") == expected_dtype, f"{label} TFLite dtype drift", errors)
        path = root / str(tflite.get(f"{label}_path", ""))
        check(path.is_file(), f"{label} TFLite artifact missing", errors)
        if path.is_file():
            check(file_sha256(path) == tflite.get(f"{label}_sha256"), f"{label} TFLite hash mismatch", errors)
    int8_contract = tflite.get("int8_contract") or {}
    check(int8_contract.get("full_integer_ops") is True, "INT8 model is not full integer", errors)
    check((int8_contract.get("input_quantization") or {}).get("scale", 0) > 0, "INT8 input quantization missing", errors)
    check((int8_contract.get("output_quantization") or {}).get("scale", 0) > 0, "INT8 output quantization missing", errors)

    quant = result.get("quantization") or {}
    check((quant.get("gate") or {}).get("status") == "PASS", "INT8 equivalence gate failed", errors)
    check(quant.get("blocking_issue") is False, "blocking quantization issue recorded", errors)
    saturation = quant.get("saturation") or {}
    for population in ("train", "validation"):
        row = saturation.get(population) or {}
        check(row.get("feature_order") == FEATURE_ORDER, f"{population} saturation feature order drift", errors)
        check(set((row.get("per_feature") or {}).keys()) == set(FEATURE_ORDER), f"{population} saturation diagnostics incomplete", errors)

    metrics = result.get("validation_metrics") or {}
    check(metrics.get("population") == "VALIDATION" and metrics.get("population_count") == VALIDATION_COUNT, "validation population drift", errors)
    check(metrics.get("threshold_frozen_before_evaluation") is True, "validation threshold was not frozen first", errors)
    for name in ("reference_float", "float_tflite", "int8_tflite"):
        row = metrics.get(name) or {}
        for key in ("accuracy", "balanced_accuracy", "macro_f1", "precision_occupied", "recall_occupied", "f1_occupied", "pr_auc_average_precision", "roc_auc", "brier_score", "log_loss"):
            value = row.get(key)
            check(isinstance(value, (int, float)) and math.isfinite(float(value)), f"invalid validation metric {name}.{key}", errors)

    determinism_path = root / f"{ARTIFACT_REL}/determinism_report.json"
    check(determinism_path.is_file(), "determinism report missing", errors)
    if determinism_path.is_file():
        determinism = load_json(determinism_path)
        check(determinism.get("data_pipeline_determinism") == "PASS" and determinism.get("threshold_determinism") == "PASS", "data/threshold determinism failed", errors)
        check(determinism.get("float_tflite_bytes_identical_on_repeat") is True and determinism.get("int8_tflite_bytes_identical_on_repeat") is True, "TFLite byte determinism failed", errors)

    lock_path = root / LOCK_REL
    check(lock_path.is_file(), "C-B6 lock missing", errors)
    if lock_path.is_file():
        lock = load_json(lock_path)
        lock_hash = lock.get("lock_sha256")
        check(lock_hash == stable_sha256({key: value for key, value in lock.items() if key != "lock_sha256"}), "C-B6 lock content hash mismatch", errors)
        check(file_sha256(lock_path) == (result.get("lock") or {}).get("sha256"), "result/lock file hash mismatch", errors)
        check(lock.get("candidate_id") == CANDIDATE_ID and lock.get("feature_order") == FEATURE_ORDER, "C-B6 lock identity drift", errors)
        check(lock.get("threshold_source") == "TRAIN_INTERNAL_ONLY" and lock.get("b5_threshold_inherited") is False, "C-B6 lock threshold provenance drift", errors)
        check(lock.get("locked_test_predictive_access") is False and lock.get("historical_b5_modified") is False, "C-B6 lock boundary drift", errors)
        for artifact in lock.get("artifacts", []):
            rel = artifact.get("path")
            check(portable_path(rel), f"non-portable C-B6 lock path: {rel}", errors)
            target = root / str(rel)
            check(target.is_file(), f"missing C-B6 lock artifact: {rel}", errors)
            if target.is_file():
                check(file_sha256(target) == artifact.get("sha256"), f"C-B6 lock artifact hash mismatch: {rel}", errors)
                check(target.stat().st_size == artifact.get("byte_size"), f"C-B6 lock artifact size mismatch: {rel}", errors)
        check(LOCK_REL not in {str(item.get("path")) for item in lock.get("artifacts", [])}, "C-B6 lock hashes itself", errors)

    next_phase = result.get("next_phase") or {}
    check(next_phase.get("phase_id") == "C-C1R", "next phase drift", errors)
    check(next_phase.get("authorization_required") is True, "next-phase authorization boundary missing", errors)
    check(next_phase.get("physical_acquisition_before_protocol_revision") is False, "physical acquisition allowed before C-C1R", errors)
    check((result.get("physical_acquisition") or {}).get("started") is False, "physical acquisition started", errors)
    check((result.get("c_c2") or {}).get("started") is False, "C-C2 started", errors)
    check((result.get("c_d") or {}).get("authorized") is False, "C-D authorized", errors)

    validate_b5_immutability(root, result, errors)
    validate_checksums(root, errors)
    report_path = root / REPORT_REL
    check(report_path.is_file(), "C-B6 report missing", errors)
    if report_path.is_file():
        report = report_path.read_text(encoding="utf-8")
        for phrase in ("Document Version: `01`", "Author: `Codex` (CO₂ C-B6 Offline Candidate Agent)", "Phase: `C-B6", "C-B6 OFFLINE VALIDATION != SCD40 DEVICE-DOMAIN VALIDATION", CANDIDATE_ID, "TRAIN_INTERNAL_ONLY", "C-C1R", "NEW_PHYSICAL_MEASUREMENT: NO"):
            check(phrase in report, f"report missing phrase: {phrase}", errors)
        check("Commit: NO" not in report and "Push: NO" not in report and "PR: NO" not in report, "stale lifecycle claim in durable report", errors)
    return {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "candidate_id": result.get("candidate_id"),
        "phase": result.get("phase_id"),
        "candidate_status": result.get("status"),
        "threshold": (result.get("threshold") or {}).get("value"),
        "locked_test_predictive_access": (result.get("locked_test") or {}).get("predictive_access"),
        "b5_modified": (result.get("b5") or {}).get("modified"),
        "physical_acquisition": (result.get("physical_acquisition") or {}).get("status"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = validate(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
