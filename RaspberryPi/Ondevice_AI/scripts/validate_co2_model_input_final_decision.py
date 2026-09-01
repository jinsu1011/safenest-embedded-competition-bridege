#!/usr/bin/env python3
"""Fail-closed validator for the CO2 pre-acquisition input decision audit."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
RESULT_REL = "datasets/co2/manifests/c_c1_model_input_decision/model_input_decision_result.json"
CHECKSUMS_REL = "datasets/co2/manifests/c_c1_model_input_decision/checksums.sha256"
REPORT_REL = "docs/reports/20260815_SafeNest_CO2_Pre_Acquisition_Model_Input_Decision_Audit_01.md"
AUDIT_REL = "scripts/audit_co2_model_input_final_decision.py"
VALIDATOR_REL = "scripts/validate_co2_model_input_final_decision.py"
TEST_REL = "tests/test_co2_model_input_final_decision.py"
C_C1_TECHNICAL_REL = "docs/reports/20260814_SafeNest_CO2_C_C1_SCD40_Measurement_Protocol_01.md"
C_C1_PROMPT_REL = "docs/prompts/20260814_SafeNest_CO2_C_C1_SCD40_Measurement_Operator_Prompt_01.md"
PROTOCOL_REL = "datasets/co2/manifests/c_c1_measurement_protocol/protocol.json"
ROADMAP_REL = "docs/20260810_ChatGPT_SafeNest_Multisensor_Parallel_Execution_Roadmap_01.md"

EXPECTED_DECISION = "ADOPT_REDUCED_FEATURE_DIRECTION"
EXPECTED_SEEDS = [20260810, 20260811, 20260812, 20260813, 20260814]
EXPECTED_A_FEATURES = ["CO2", "Temperature", "Humidity", "CO2_slope"]
EXPECTED_B_FEATURES = ["CO2", "CO2_slope"]
EXPECTED_BOOTSTRAP_REPLICATES = 2000
EXPECTED_BOOTSTRAP_SEED = 20260815


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def check_relative_path(value: Any, label: str, errors: list[str]) -> None:
    path = str(value)
    check(path and not path.startswith("/") and "\\" not in path, f"{label} is not portable", errors)


def validate_checksums(root: Path, errors: list[str]) -> None:
    path = root / CHECKSUMS_REL
    check(path.is_file(), f"missing checksum manifest: {CHECKSUMS_REL}", errors)
    if not path.is_file():
        return

    observed: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            digest, relative_path = line.split("  ", 1)
        except ValueError:
            errors.append(f"malformed checksum line {line_number}")
            continue
        check(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, f"invalid checksum digest on line {line_number}", errors)
        check_relative_path(relative_path, f"checksum path on line {line_number}", errors)
        check(relative_path != CHECKSUMS_REL, "decision checksum manifest must not hash itself", errors)
        target = root / relative_path
        check(target.is_file(), f"checksum target missing: {relative_path}", errors)
        if target.is_file():
            check(sha256_file(target) == digest, f"checksum mismatch: {relative_path}", errors)
        observed.add(relative_path)

    expected = {REPORT_REL, RESULT_REL, AUDIT_REL, VALIDATOR_REL, TEST_REL}
    check(observed == expected, "decision checksum coverage does not match the five decision artifacts", errors)


def validate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []
    result_path = root / RESULT_REL
    check(result_path.is_file(), f"missing decision result: {RESULT_REL}", errors)
    if not result_path.is_file():
        return {"status": "FAIL", "errors": errors}

    result = load_json(result_path)
    check(result.get("decision_profile_id") == "CO2_PRE_ACQUISITION_MODEL_INPUT_DECISION_AUDIT_001", "decision profile drift", errors)
    check(result.get("final_decision") == EXPECTED_DECISION, "final decision drift", errors)
    check(result.get("seed_list") == EXPECTED_SEEDS, "seed list drift", errors)
    check(result.get("arm_a_features") == EXPECTED_A_FEATURES, "arm A feature order drift", errors)
    check(result.get("arm_b_features") == EXPECTED_B_FEATURES, "arm B feature order drift", errors)

    interpretation = result.get("interpretation") or {}
    check(interpretation.get("four_feature_predictive_benefit_observed") is True, "four-feature predictive benefit was not recorded", errors)
    check(interpretation.get("reduced_feature_predictive_superiority_established") is False, "reduced-feature predictive superiority was overclaimed", errors)
    check(interpretation.get("occupied_recall_tradeoff_observed") is True, "occupied-recall tradeoff was not recorded", errors)
    check(interpretation.get("occupied_recall_comparison_threshold") == 0.58, "occupied-recall comparison threshold drift", errors)
    check(interpretation.get("occupied_recall_advantage_threshold_conditioned") is True, "threshold-conditioned qualification missing", errors)
    check(interpretation.get("threshold_origin") == "CURRENT_FOUR_FEATURE_B5_LINEAGE", "threshold origin drift", errors)
    check(interpretation.get("reduced_feature_threshold_not_finalized") is True, "reduced-feature threshold was incorrectly finalized", errors)
    check(interpretation.get("t_rh_zero_information_claim") is False, "T/RH zero-information claim was enabled", errors)

    decision_basis = result.get("decision_basis") or {}
    check(decision_basis.get("type") == "SYSTEM_CONTRACT_BURDEN_OF_PROOF", "decision basis type drift", errors)
    check(decision_basis.get("not_model_superiority_ranking") is True, "decision was incorrectly represented as model ranking", errors)
    check(decision_basis.get("original_system_direction") == "CO2_CENTRIC", "original system direction drift", errors)
    check(decision_basis.get("mandatory_trh_fields_justification_not_met") is True, "T/RH burden-of-proof result missing", errors)

    locked = result.get("locked_test_access") or {}
    for key in ("feature_rows_decoded", "target_rows_decoded", "predictive_metrics", "selection_usage", "model_selection_usage"):
        check(locked.get(key) == 0, f"LOCKED_TEST access drift: {key}", errors)
    check(locked.get("sealed") is True, "LOCKED_TEST is not sealed", errors)

    contract = result.get("fixed_training_contract") or {}
    check(contract.get("slope_profile") == "ENDPOINT_H150", "slope profile drift", errors)
    check(contract.get("causality") == "PAST_ONLY", "causality drift", errors)
    check(contract.get("max_internal_gap_seconds") == 90.0, "gap contract drift", errors)
    check(contract.get("threshold") == 0.58, "threshold drift", errors)
    check(contract.get("scaler_fit_population") == "ORIGINAL_TRAIN_ONLY", "scaler fit population drift", errors)
    check(contract.get("validation_population_only_for_decision") is True, "validation-only decision boundary drift", errors)
    check(contract.get("feature_search") is False, "feature search was enabled", errors)
    check(contract.get("hyperparameter_search") is False, "hyperparameter search was enabled", errors)
    check(contract.get("resplitting") is False, "resplitting was enabled", errors)

    bootstrap = result.get("bootstrap") or {}
    check(bootstrap.get("seed") == EXPECTED_BOOTSTRAP_SEED, "bootstrap seed drift", errors)
    check(bootstrap.get("replicates") == EXPECTED_BOOTSTRAP_REPLICATES, "bootstrap replicate count drift", errors)
    check(bootstrap.get("validation_population_count") == 2662, "bootstrap population drift", errors)
    check(bootstrap.get("paired_validation_rows") is True, "bootstrap pairing contract missing", errors)

    wins = (result.get("aggregate_results") or {}).get("seed_win_table") or {}
    expected_direction = {
        "accuracy": ("HIGHER_IS_BETTER", 5, 0),
        "macro_f1": ("HIGHER_IS_BETTER", 5, 0),
        "precision_occupied": ("HIGHER_IS_BETTER", 5, 0),
        "recall_occupied": ("HIGHER_IS_BETTER", 0, 5),
        "pr_auc_average_precision": ("HIGHER_IS_BETTER", 5, 0),
        "roc_auc": ("HIGHER_IS_BETTER", 5, 0),
        "brier_score": ("LOWER_IS_BETTER", 5, 0),
        "log_loss": ("LOWER_IS_BETTER", 5, 0),
    }
    for metric, (direction, a_better, b_better) in expected_direction.items():
        row = wins.get(metric) or {}
        check(row.get("direction") == direction, f"win direction drift: {metric}", errors)
        check(row.get("a_better") == a_better, f"A directional count drift: {metric}", errors)
        check(row.get("b_better") == b_better, f"B directional count drift: {metric}", errors)
        check(row.get("ties") == 0 and row.get("seed_count") == 5, f"tie/seed count drift: {metric}", errors)

    checks = (result.get("decision_logic") or {}).get("checks") or {}
    check(checks.get("occupied_recall_not_lost_in_more_than_1_of_5") is False, "occupied-recall decision check unexpectedly passes", errors)
    check(checks.get("paired_occupied_recall_lower_bound_nonnegative") is False, "occupied-recall bootstrap check unexpectedly passes", errors)
    for key in (
        "macro_f1_a_wins_at_least_4_of_5",
        "accuracy_a_wins_at_least_4_of_5",
        "occupied_precision_a_wins_at_least_4_of_5",
        "paired_macro_f1_lower_bound_above_zero",
        "paired_accuracy_lower_bound_above_zero",
        "paired_occupied_precision_lower_bound_above_zero",
        "pr_auc_a_wins_or_ties_in_at_least_4_of_5",
        "roc_auc_a_wins_or_ties_in_at_least_4_of_5",
        "brier_a_wins_or_ties_in_at_least_4_of_5",
        "log_loss_a_wins_or_ties_in_at_least_4_of_5",
    ):
        check(checks.get(key) is True, f"expected decision check failed: {key}", errors)

    b5 = result.get("b5") or {}
    check(b5.get("modified") is False, "B5 modified flag drift", errors)
    check(b5.get("model_artifact_modified") is False, "B5 model artifact modified flag drift", errors)
    check(b5.get("scaler_artifact_modified") is False, "B5 scaler artifact modified flag drift", errors)
    check(b5.get("feature_order") == EXPECTED_A_FEATURES, "B5 feature order in result drift", errors)

    status = result.get("status_boundary") or {}
    check(status.get("physical_acquisition_status") == "HOLD_PENDING_REDUCED_FEATURE_CANDIDATE_LOCK", "physical acquisition status drift", errors)
    check(status.get("operator_handoff_status") == "HOLD", "operator handoff status drift", errors)
    check(status.get("c_c2_started") is False, "C-C2 status drift", errors)
    check(status.get("new_physical_measurement") is False, "physical measurement status drift", errors)

    next_phase = result.get("next_phase") or {}
    check(next_phase.get("phase_id") == "C-B6", "next model phase ID drift", errors)
    check(next_phase.get("title") == "Reduced-Feature Candidate Development and Lock", "next model phase title drift", errors)
    check(next_phase.get("authorization_required") is True, "C-B6 authorization boundary missing", errors)
    check(next_phase.get("physical_acquisition_before_lock") is False, "physical acquisition was allowed before C-B6 lock", errors)
    check(next_phase.get("c_c2_before_lock") is False, "C-C2 was allowed before C-B6 lock", errors)
    check(result.get("recommended_next_phase") == "C-B6_REDUCED_FEATURE_CANDIDATE_DEVELOPMENT_AND_LOCK_BEFORE_PROTOCOL_REVISION", "recommended next phase drift", errors)

    protocol_path = root / PROTOCOL_REL
    check(protocol_path.is_file(), f"missing C-C1 protocol: {PROTOCOL_REL}", errors)
    if protocol_path.is_file():
        protocol = load_json(protocol_path)
        check(protocol.get("protocol_id") == "CO2_C_C1_MEASUREMENT_PROTOCOL_001", "C-C1 protocol identity drift", errors)
        check(protocol.get("protocol_version") == "1.0.0", "C-C1 protocol version drift", errors)
        check([entry.get("name") for entry in protocol.get("required_features", [])] == EXPECTED_A_FEATURES, "historical C-C1 feature fields changed", errors)
        post = protocol.get("post_c_c1_model_input_decision") or {}
        check(post.get("decision") == EXPECTED_DECISION, "C-C1 post-decision value missing", errors)
        check(post.get("current_protocol_semantics") == "HISTORICAL_FOUR_FEATURE_B5_COMPATIBILITY_CONTRACT", "C-C1 historical semantics drift", errors)
        check(post.get("physical_acquisition_status") == "HOLD_PENDING_REDUCED_FEATURE_CANDIDATE_LOCK", "C-C1 physical hold missing", errors)
        check(post.get("operator_handoff_status") == "HOLD", "C-C1 operator hold missing", errors)
        check((post.get("next_model_phase") or {}).get("phase_id") == "C-B6", "C-C1 next model phase drift", errors)
        check(post.get("b5_threshold_0_58_inheritance_to_reduced_model") == "FORBIDDEN", "B5 threshold inheritance policy drift", errors)
        check(post.get("b5_modified") is False, "C-C1 B5 modification flag drift", errors)

    report_path = root / REPORT_REL
    roadmap_path = root / ROADMAP_REL
    for path, label in ((report_path, "decision report"), (roadmap_path, "master roadmap")):
        check(path.is_file(), f"missing {label}", errors)
    if report_path.is_file():
        report = report_path.read_text(encoding="utf-8")
        for phrase in (
            "Document Version: `01`",
            "Author: `Codex` (CO₂ Pre-Acquisition Decision Audit Agent)",
            "Execution Date: `2026-08-15`",
            "Phase: `C-C — Pre-Acquisition Model-Input Decision Audit`",
            "Status: `COMPLETE_WITH_HOLD`",
            EXPECTED_DECISION,
            "FOUR_FEATURE_PREDICTIVE_BENEFIT_OBSERVED",
            "REDUCED_FEATURE_PREDICTIVE_SUPERIORITY",
            "THRESHOLD_CONDITIONED",
            "HOLD_PENDING_REDUCED_FEATURE_CANDIDATE_LOCK",
            "LOCKED_TEST",
            "Brier score",
            "lower-is-better",
            "no approved effect-size or equivalence margin",
        ):
            check(phrase.lower() in report.lower(), f"decision report missing phrase: {phrase}", errors)
        check("??" not in report, "decision report contains placeholder values", errors)

    for path, expected_header in (
        (
            root / C_C1_TECHNICAL_REL,
            (
                "Document Version: `02`",
                "Author: `Codex` (CO₂ Measurement Protocol Agent)",
                "Execution Date: `2026-08-15`",
                "Phase: `C-C1 — Historical Four-Feature Measurement Protocol and Operator Handoff`",
                "Status: `HISTORICAL_PROTOCOL_WITH_CURRENT_HOLD`",
            ),
        ),
        (
            root / C_C1_PROMPT_REL,
            (
                "Document Version: `02`",
                "Author: `Codex` (CO₂ Measurement Protocol Agent)",
                "Execution Date: `2026-08-15`",
                "Phase: `C-C1 — Historical Four-Feature Measurement Protocol and Operator Handoff`",
                "Status: `HISTORICAL_PROMPT_WITH_CURRENT_HOLD`",
            ),
        ),
    ):
        check(path.is_file(), f"missing provenance-header artifact: {path}", errors)
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            for phrase in expected_header:
                check(phrase in content, f"document provenance header missing: {path}: {phrase}", errors)
    if roadmap_path.is_file():
        roadmap = roadmap_path.read_text(encoding="utf-8")
        for phrase in (
            EXPECTED_DECISION,
            "C-B6",
            "Reduced-Feature Candidate Development and Lock",
            "FOUR_FEATURE_PREDICTIVE_BENEFIT_OBSERVED",
            "THRESHOLD_CONDITIONED",
            "B5_THRESHOLD_0_58_INHERITANCE_TO_REDUCED_MODEL = FORBIDDEN",
            "physical acquisition",
            "HOLD",
            "model_input_decision_result.json",
        ):
            check(phrase in roadmap, f"roadmap missing final decision alignment: {phrase}", errors)

    validate_checksums(root, errors)
    return {
        "status": "PASS" if not errors else "FAIL",
        "decision": result.get("final_decision"),
        "seed_count": len(result.get("seed_list", [])),
        "locked_test_predictive_metrics": locked.get("predictive_metrics"),
        "physical_acquisition_status": status.get("physical_acquisition_status"),
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    result = validate(args.root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
