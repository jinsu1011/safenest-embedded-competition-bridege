#!/usr/bin/env python3
"""Validate C-C1T acquisition tooling before physical collection."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from capture_co2_c_c1t_session import (
    CAPTURE_SCRIPT_RELPATH,
    ROOT,
    load_context,
    validate_session_bundle,
    write_json,
)


CONTRACT_RELPATH = "datasets/co2/manifests/c_c1t_acquisition_tooling/capture_contract.json"
RESULT_RELPATH = "datasets/co2/manifests/c_c1t_acquisition_tooling/precollection_result.json"
REQUIRED_TEAM_PAYLOAD_FIELDS = [
    "co2_measurement_event_id",
    "co2_measurement_monotonic_ms",
    "co2_measurement_event_valid",
]


def _failure(errors: list[str], message: str) -> None:
    errors.append(message)


def validate_capture_contract(
    contract: dict[str, Any], context: dict[str, Any], root: Path
) -> list[str]:
    errors: list[str] = []
    if contract.get("contract_version") != "1.0":
        _failure(errors, "capture contract version is not 1.0")
    if contract.get("phase") != "C-C1T":
        _failure(errors, "capture contract phase is not C-C1T")
    identity = contract.get("protocol_identity")
    if not isinstance(identity, dict):
        _failure(errors, "protocol_identity is missing")
    else:
        for key, expected in (
            ("protocol_id", context["protocol_id"]),
            ("protocol_version", context["protocol_version"]),
            ("candidate_id", context["candidate_id"]),
            ("candidate_lock_sha256", context["candidate_lock_sha256"]),
        ):
            if identity.get(key) != expected:
                _failure(errors, f"protocol identity mismatch: {key}")
    cadence = contract.get("effective_cadence_contract")
    if not isinstance(cadence, dict):
        _failure(errors, "effective_cadence_contract is missing")
    else:
        if cadence.get("effective_model_input_interval_sec") != 60:
            _failure(errors, "effective model-input interval is not 60 seconds")
        if cadence.get("normal_co2_export_interval_sec") != 60:
            _failure(errors, "normal CO2 export interval is not 60 seconds")
        if cadence.get("native_sensor_cadence_separate") is not True:
            _failure(errors, "native sensor cadence is not explicitly separate")
        if cadence.get("stale_reuse") != "FORBIDDEN":
            _failure(errors, "stale reuse is not forbidden")
        if cadence.get("synthetic_fill") != "FORBIDDEN":
            _failure(errors, "synthetic fill is not forbidden")
    capture = contract.get("standalone_capture_tool")
    if not isinstance(capture, dict):
        _failure(errors, "standalone_capture_tool is missing")
    else:
        script_path = root / str(capture.get("path", ""))
        if capture.get("path") != CAPTURE_SCRIPT_RELPATH or not script_path.is_file():
            _failure(errors, "standalone capture script path is invalid")
        if capture.get("raw_layer_before_preprocessing") is not True:
            _failure(errors, "capture tool does not declare raw-before-preprocessing")
        if capture.get("model_inference") is not False:
            _failure(errors, "capture tool must not perform model inference")
    producer = contract.get("team_producer_observability")
    if not isinstance(producer, dict):
        _failure(errors, "team_producer_observability is missing")
    else:
        for field in REQUIRED_TEAM_PAYLOAD_FIELDS:
            if field not in producer.get("required_payload_fields", []):
                _failure(errors, f"required producer payload field missing: {field}")
        if producer.get("transport_freshness_is_sensor_freshness") is not False:
            _failure(errors, "producer contract conflates transport and sensor freshness")
        if producer.get("event_id_changes_only_after_successful_read") is not True:
            _failure(errors, "producer event identity semantics are not explicit")
    team = contract.get("team_change")
    if not isinstance(team, dict):
        _failure(errors, "team_change is missing")
    else:
        if team.get("producer_change_required") is not True:
            _failure(errors, "team producer change is not recorded as required")
        if not team.get("feature_branch_commit"):
            _failure(errors, "team feature branch commit is missing")
        if not isinstance(team.get("pr_number"), int):
            _failure(errors, "team PR number is missing")
        if team.get("pr_state") not in {"OPEN", "MERGED"}:
            _failure(errors, "team PR state is invalid")
        if team.get("deployed_to_team_main") is not True and team.get("pr_state") == "MERGED":
            _failure(errors, "a merged team PR must declare deployment state")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--contract", type=Path, default=ROOT / CONTRACT_RELPATH)
    parser.add_argument("--output", type=Path, default=ROOT / RESULT_RELPATH)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    context = load_context()
    contract = json.loads(args.contract.read_text(encoding="utf-8"))
    contract_errors = validate_capture_contract(contract, context, ROOT)
    bundle_result = validate_session_bundle(args.bundle_dir, context)
    team = contract.get("team_change", {})
    team_deployed = team.get("deployed_to_team_main") is True
    team_merged = team.get("pr_state") == "MERGED"
    tooling_pass = not contract_errors
    dry_run_pass = bundle_result.get("status") == "PASS"
    if tooling_pass and dry_run_pass and team_merged and team_deployed:
        status = "C_C1T_ACQUISITION_TOOLING_READY"
        operator_handoff = "READY"
        physical_acquisition = "AUTHORIZED_PENDING_EXPLICIT_COLLECTION_AUTHORIZATION"
        validation_status = "PASS"
    elif tooling_pass and dry_run_pass:
        status = "C_C1T_BLOCKED"
        operator_handoff = "HOLD_PENDING_TEAM_PRODUCER_PR_MERGE_AND_DEPLOYMENT"
        physical_acquisition = "HOLD"
        validation_status = "PASS_WITH_DEPLOYMENT_BLOCKER"
    else:
        status = "C_C1T_BLOCKED"
        operator_handoff = "HOLD_PENDING_TOOLING_CORRECTION"
        physical_acquisition = "HOLD"
        validation_status = "FAIL"

    result: dict[str, Any] = {
        "result_version": "1.0",
        "phase": "C-C1T",
        "result_date": "2026-08-15",
        "agent": "Codex (CO2 C-C1T Acquisition Tooling Readiness Agent)",
        "status": status,
        "validation_status": validation_status,
        "operator_handoff": operator_handoff,
        "physical_acquisition": physical_acquisition,
        "team_producer_change_required": True,
        "team_producer_change_performed_on_feature_branch": bool(
            team.get("feature_branch_commit")
        ),
        "team_producer_change_deployed_to_team_main": team_deployed,
        "team_producer_change": {
            "team_main_base_sha": team.get("team_main_base_sha"),
            "feature_branch": team.get("feature_branch"),
            "feature_branch_commit": team.get("feature_branch_commit"),
            "pr_number": team.get("pr_number"),
            "pr_state": team.get("pr_state"),
            "pr_url": team.get("pr_url"),
        },
        "protocol_identity": {
            "protocol_id": context["protocol_id"],
            "protocol_version": context["protocol_version"],
            "candidate_id": context["candidate_id"],
            "candidate_lock_sha256": context["candidate_lock_sha256"],
        },
        "effective_model_input_cadence_sec": 60,
        "native_sensor_cadence_separate": True,
        "capture_capabilities": {
            "live_pi_health_capture": True,
            "fixture_dry_run": True,
            "raw_payload_preservation": True,
            "transport_vs_sensor_freshness_separation": True,
            "retransmission_detection_by_event_id": True,
            "failure_and_missing_row_preservation": True,
            "independent_ground_truth_event_log": True,
            "final_sha256_bundle": True,
            "model_inference": False,
            "slope_computation": False,
        },
        "contract_validation": {
            "status": "PASS" if tooling_pass else "FAIL",
            "errors": contract_errors,
        },
        "dry_run_validation": bundle_result,
        "physical_measurement_performed": False,
        "c_c2_started": False,
        "c_d_authorized": False,
        "blocker": (
            "TEAM_PRODUCER_OBSERVABILITY_PR_NOT_MERGED_OR_DEPLOYED"
            if tooling_pass and dry_run_pass and not (team_merged and team_deployed)
            else None
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.output, result)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if tooling_pass and dry_run_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
