#!/usr/bin/env python3
"""Fail-closed validator for the frozen CO2 C-C1 measurement contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
MANIFEST_REL = "datasets/co2/manifests/c_c1_measurement_protocol/protocol.json"
RESULT_REL = "datasets/co2/manifests/c_c1_measurement_protocol/validation_result.json"
CHECKSUMS_REL = "datasets/co2/manifests/c_c1_measurement_protocol/checksums.sha256"
TECHNICAL_REL = "docs/reports/20260814_SafeNest_CO2_C_C1_SCD40_Measurement_Protocol_01.md"
PROMPT_REL = "docs/prompts/20260814_SafeNest_CO2_C_C1_SCD40_Measurement_Operator_Prompt_01.md"
VALIDATOR_REL = "scripts/validate_co2_c_c1_measurement_protocol.py"

EXPECTED_PROTOCOL_ID = "CO2_C_C1_MEASUREMENT_PROTOCOL_001"
EXPECTED_PROTOCOL_VERSION = "1.0.0"
EXPECTED_B5_FEATURES = ["CO2", "Temperature", "Humidity", "CO2_slope"]
EXPECTED_MODEL_SHA256 = "bb2ed28533bca75d4fa3d06348e017c506df47d7c34b29574b77f70b6b386816"
EXPECTED_SCALER_FINGERPRINT = "d0cf83558fb0de9dcdc97f0d94781a5a475a6f68e8d818121aee929030e5dc89"
EXPECTED_FINAL_LOCK_SHA256 = "a020d462e0d359e0c9faa9bb680387119f095cb102243d7e6c223d76a801b627"
EXPECTED_CANDIDATE_PROFILE_ID = "CO2_B5_FINAL_OFFLINE_UCI_CANDIDATE_001"
EXPECTED_CANDIDATE_METADATA_SHA256 = "695c475201be2c09b4661757bce8b5102fd04626de72d4e70fcde17b3abf3376"
EXPECTED_C0_MAIN_SHA = "0625603f319b18cd6ad86b33dcca5ce2147ac2af"
EXPECTED_C0_CLASSIFICATION = "B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE"
EXPECTED_EFFECTIVE_CADENCE_SECONDS = 60.0
EXPECTED_NORMAL_EXPORT_CADENCE_SECONDS = 60.0


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
    check(path and not path.startswith("/") and "\\" not in path, f"{label} is not a portable repository-relative path", errors)


def validate_checksums(root: Path, manifest: dict[str, Any], errors: list[str]) -> dict[str, str]:
    checksum_path = root / CHECKSUMS_REL
    check(checksum_path.is_file(), "missing C-C1 checksums.sha256", errors)
    if not checksum_path.is_file():
        return {}

    observed: dict[str, str] = {}
    for line_number, line in enumerate(checksum_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            digest, relative_path = line.split("  ", 1)
        except ValueError:
            errors.append(f"malformed checksum line {line_number}")
            continue
        check(re.fullmatch(r"[0-9a-f]{64}", digest) is not None, f"invalid checksum digest on line {line_number}", errors)
        check_relative_path(relative_path, f"checksum path on line {line_number}", errors)
        if relative_path == CHECKSUMS_REL:
            errors.append("checksums.sha256 must not hash itself")
        path = root / relative_path
        check(path.is_file(), f"checksum target missing: {relative_path}", errors)
        if path.is_file():
            actual = sha256_file(path)
            check(actual == digest, f"checksum mismatch: {relative_path}", errors)
        observed[relative_path] = digest

    required = {
        TECHNICAL_REL,
        MANIFEST_REL,
        PROMPT_REL,
        VALIDATOR_REL,
    }
    check(set(observed) == required, "C-C1 checksum coverage does not match the four frozen protocol artifacts", errors)
    return observed


def validate(root: Path) -> dict[str, Any]:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []
    manifest_path = root / MANIFEST_REL
    check(manifest_path.is_file(), f"missing manifest: {MANIFEST_REL}", errors)
    if errors:
        return result_payload(errors, warnings)

    manifest = load_json(manifest_path)
    check(manifest.get("manifest_version") == "1.0", "manifest_version drift", errors)
    check(manifest.get("phase") == "C-C1", "phase must be C-C1", errors)
    check(manifest.get("protocol_id") == EXPECTED_PROTOCOL_ID, "protocol_id drift", errors)
    check(manifest.get("protocol_version") == EXPECTED_PROTOCOL_VERSION, "protocol_version drift", errors)
    check(manifest.get("protocol_status") == "FROZEN_FOR_EXTERNAL_ACQUISITION_WITH_PRECOLLECTION_COMPLIANCE_GATE", "protocol_status drift", errors)
    check(manifest.get("c_c1_protocol_frozen") is True, "C_C1_PROTOCOL_FROZEN is not true", errors)
    check(re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("creation_commit", ""))) is not None, "creation_commit is not a full Git SHA", errors)

    scope = manifest.get("scope") or {}
    for key in ("data_collection_in_this_phase", "new_raw_payload_in_this_phase", "model_evaluation_in_this_phase", "model_development_in_this_phase", "c_c2_started", "c_d_authorized"):
        check(scope.get(key) is False, f"scope authorization drift: {key}", errors)

    predecessor = manifest.get("predecessor_c_c0_evidence") or {}
    check(predecessor.get("status") == "MERGED_ON_CURRENT_ORIGIN_MAIN", "C-C0 predecessor is not marked merged", errors)
    check(predecessor.get("standalone_origin_main_sha") == EXPECTED_C0_MAIN_SHA, "C-C0 predecessor main SHA drift", errors)
    check(predecessor.get("c_c0_outcome") == EXPECTED_C0_CLASSIFICATION, "C-C0 classification drift", errors)
    for key in ("english_report", "korean_report"):
        reference = predecessor.get(key) or {}
        relative_path = str(reference.get("path", ""))
        check_relative_path(relative_path, f"C-C0 {key} path", errors)
        path = root / relative_path
        check(path.is_file(), f"missing C-C0 predecessor report: {relative_path}", errors)
        if path.is_file():
            check(sha256_file(path) == reference.get("sha256"), f"C-C0 predecessor report hash drift: {relative_path}", errors)
            check(EXPECTED_C0_CLASSIFICATION in path.read_text(encoding="utf-8"), f"C-C0 classification missing from {relative_path}", errors)

    team_reference = manifest.get("team_acquisition_reference") or {}
    check(re.fullmatch(r"[0-9a-f]{40}", str(team_reference.get("team_origin_main_sha", ""))) is not None, "team origin SHA missing or malformed", errors)
    check(team_reference.get("legacy_path_c1_status") == "NOT_C_C1_COMPLIANT_WITHOUT_PROTOCOL_ADAPTER", "legacy C1 compliance boundary drift", errors)
    check(bool(team_reference.get("precollection_rule")), "team precollection rule missing", errors)

    b5 = manifest.get("frozen_b5_reference") or {}
    check(b5.get("candidate_profile_id") == EXPECTED_CANDIDATE_PROFILE_ID, "B5 candidate profile drift", errors)
    check(b5.get("candidate_status") == "FINAL_OFFLINE_UCI_CANDIDATE_LOCKED", "B5 candidate status drift", errors)
    check(b5.get("device_domain_validation_status") == "NOT_YET_COMPLETE", "B5 device-domain status overclaimed", errors)
    check(b5.get("feature_order") == EXPECTED_B5_FEATURES, "B5 feature order drift", errors)
    check(b5.get("slope_profile") == "ENDPOINT_H150", "B5 slope profile drift", errors)
    check(b5.get("threshold") == 0.58, "B5 threshold drift", errors)
    check(b5.get("model_sha256") == EXPECTED_MODEL_SHA256, "B5 model hash in manifest drift", errors)
    check(b5.get("scaler_fingerprint") == EXPECTED_SCALER_FINGERPRINT, "B5 scaler fingerprint in manifest drift", errors)
    check(b5.get("final_lock_sha256") == EXPECTED_FINAL_LOCK_SHA256, "B5 final lock hash in manifest drift", errors)
    check(b5.get("candidate_metadata_sha256") == EXPECTED_CANDIDATE_METADATA_SHA256, "B5 metadata hash in manifest drift", errors)
    for key in ("model_path", "scaler_path", "candidate_metadata_path", "final_lock_path"):
        check_relative_path(b5.get(key), f"B5 {key}", errors)

    metadata_path = root / str(b5.get("candidate_metadata_path"))
    lock_path = root / str(b5.get("final_lock_path"))
    model_path = root / str(b5.get("model_path"))
    scaler_path = root / str(b5.get("scaler_path"))
    for path, label in (
        (metadata_path, "B5 candidate metadata"),
        (lock_path, "B5 final lock"),
        (model_path, "B5 model"),
        (scaler_path, "B5 scaler"),
    ):
        check(path.is_file(), f"missing {label}: {path}", errors)
    if metadata_path.is_file():
        metadata = load_json(metadata_path)
        check(sha256_file(metadata_path) == EXPECTED_CANDIDATE_METADATA_SHA256, "B5 candidate metadata file hash drift", errors)
        check(metadata.get("candidate_profile_id") == EXPECTED_CANDIDATE_PROFILE_ID, "live B5 candidate profile drift", errors)
        check(metadata.get("feature_order") == EXPECTED_B5_FEATURES, "live B5 feature order drift", errors)
        check(metadata.get("slope_profile") == "ENDPOINT_H150", "live B5 slope profile drift", errors)
        check(metadata.get("threshold") == 0.58, "live B5 threshold drift", errors)
        check(metadata.get("device_domain_validation_status") == "NOT_YET_COMPLETE", "live B5 device status drift", errors)
        check((metadata.get("scaler_identity") or {}).get("fingerprint") == EXPECTED_SCALER_FINGERPRINT, "live B5 scaler fingerprint drift", errors)
    if lock_path.is_file():
        lock = load_json(lock_path)
        check(lock.get("final_lock_sha256") == EXPECTED_FINAL_LOCK_SHA256, "live B5 final lock identity drift", errors)
        check(lock.get("closure_status") == "PASS", "live B5 closure status is not PASS", errors)
        check(sha256_file(lock_path) == "1030816b298652783b8ccd78cdae330511145db7b1205a980d5a8bb431bde855", "live B5 final lock file hash drift", errors)
    if model_path.is_file():
        check(sha256_file(model_path) == EXPECTED_MODEL_SHA256, "live B5 model file hash drift", errors)
    if scaler_path.is_file():
        check(sha256_file(scaler_path) == "732c8d4b57cd27e097aabab12b2fcfb67ed38392afe638e3f7be3a3eb5ad954a", "live B5 scaler file hash drift", errors)

    features = manifest.get("required_features") or []
    check([entry.get("name") for entry in features] == EXPECTED_B5_FEATURES, "required feature registry drift", errors)
    for entry in features:
        check(entry.get("required") is True, f"feature is not required: {entry.get('name')}", errors)
        check(entry.get("unit"), f"feature unit missing: {entry.get('name')}", errors)
        check(entry.get("source"), f"feature source missing: {entry.get('name')}", errors)
        check(entry.get("formal_c2_blocker_if_missing") is True, f"feature missing is not a C-C2 blocker: {entry.get('name')}", errors)

    field_contract = manifest.get("field_contract") or []
    field_names = {entry.get("field") for entry in field_contract}
    required_field_names = {
        "session_id",
        "measurement_event_id",
        "fresh_read_sequence",
        "sensor_event_monotonic_ms",
        "data_ready",
        "sensor_read_status",
        "co2_ppm",
        "temperature_c",
        "relative_humidity_pct",
        "per_feature_valid",
        "raw_sensor_payload",
        "esp_device_id",
        "esp_uptime_ms",
        "telemetry_sequence",
        "pi_receive_timestamp_utc",
        "pi_receive_monotonic_ns",
        "transport_connected",
        "transport_fresh",
        "transport_age_seconds",
        "transport_status",
        "logger_timestamp_utc",
        "logger_monotonic_ns",
        "logger_row_index",
        "ground_truth_ref",
        "ground_truth_label",
        "ground_truth_source",
        "ground_truth_event_timestamp_utc",
        "measurement_mode",
        "configured_measurement_interval_ms",
        "effective_model_input_cadence_sec",
        "normal_co2_export_cadence_sec",
        "asc_enabled",
        "temperature_offset_c",
        "altitude_compensation_m",
        "ambient_pressure_pa",
        "frc_history",
        "power_cycle_state",
        "failure_event",
        "deviation_event",
    }
    check(required_field_names.issubset(field_names), "field contract is missing required protocol fields", errors)
    for entry in field_contract:
        for key in ("field", "status", "type", "source", "capture_timing", "allowed_missing_state", "reason", "validation_rule"):
            check(entry.get(key) not in (None, ""), f"field contract entry missing {key}: {entry.get('field')}", errors)

    event_contract = manifest.get("measurement_event_contract") or {}
    event_definition = event_contract.get("fresh_event_definition") or []
    for phrase in ("data-ready status is true", "readMeasurement returns success", "same read call", "fresh_read_sequence increments exactly once", "sensor_event_monotonic_ms"):
        check(any(phrase.lower() in str(item).lower() for item in event_definition), f"fresh-event contract missing: {phrase}", errors)
    check(event_contract.get("unsupported_assumption_prohibited"), "freshness assumption prohibition missing", errors)
    check(event_contract.get("event_coherence_rule"), "event coherence rule missing", errors)

    cadence = manifest.get("effective_model_input_cadence") or {}
    check(cadence.get("nominal_interval_sec") == EXPECTED_EFFECTIVE_CADENCE_SECONDS, "effective model-input cadence is not nominally 60 seconds", errors)
    check(cadence.get("role") == "SAFENEST_MODEL_INPUT_AND_NORMAL_EXPORT_CADENCE", "effective cadence role drift", errors)
    check(cadence.get("native_sensor_measurement_cadence_is_separate") is True, "native SCD40 cadence is not explicitly separate", errors)
    native_contract = str(cadence.get("native_sensor_measurement_cadence_contract", ""))
    check("configured_measurement_interval_ms" in native_contract and "60000 ms native SCD40 measurement interval" in native_contract, "native-vs-downstream cadence distinction is incomplete", errors)
    check(cadence.get("requires_verified_fresh_scd40_event") is True, "effective cadence does not require a verified fresh SCD40 event", errors)
    check(cadence.get("stale_reuse_for_schedule_compliance") == "FORBIDDEN", "stale reuse is not forbidden for cadence compliance", errors)
    check(cadence.get("required_coherent_fields") == ["CO2", "Temperature", "Humidity"], "effective cadence coherent feature registry drift", errors)
    check(cadence.get("chronology_basis") == "VERIFIED_FRESH_MEASUREMENT_CHRONOLOGY", "effective cadence chronology basis drift", errors)

    normal_export = cadence.get("normal_export") or {}
    check(normal_export.get("nominal_interval_sec") == EXPECTED_NORMAL_EXPORT_CADENCE_SECONDS, "normal CO2 export cadence is not nominally 60 seconds", errors)
    check(normal_export.get("role") == "SAFENEST_NORMAL_CO2_EXPORT_CADENCE", "normal export cadence role drift", errors)
    check(normal_export.get("same_event_as_model_input") is True, "normal export is not bound to the model-input event", errors)
    check(normal_export.get("valid_record_requires_same_fresh_event") is True, "normal export lacks same-fresh-event requirement", errors)
    check(normal_export.get("missing_fresh_event_policy") == "PRESERVE_MISSING_OR_FAILURE; DO_NOT_EMIT_VALID_NORMAL_RECORD", "normal export missing-event policy drift", errors)
    check("do not edit timestamps" in str(normal_export.get("timestamp_policy", "")).lower(), "normal export timestamp preservation rule missing", errors)

    failure_observability = cadence.get("failure_observability") or {}
    check(failure_observability.get("independent_of_normal_valid_record") is True, "failure observability is coupled to normal valid export", errors)
    check(failure_observability.get("preserve_when_observed") is True, "failure evidence preservation rule missing", errors)
    check(failure_observability.get("must_wait_for_next_normal_export") is False, "failure evidence incorrectly waits for normal export", errors)

    missed_sample = cadence.get("one_missed_sample_consequence") or {}
    example = missed_sample.get("example_chronology") or []
    check([item.get("time_sec") for item in example] == [0.0, 60.0, 120.0, 180.0], "one-missed-sample chronology example drift", errors)
    check([item.get("status") for item in example] == ["VALID", "VALID", "MISSING_OR_INVALID", "VALID"], "one-missed-sample status example drift", errors)
    check(missed_sample.get("resulting_valid_event_gap_sec") == 120.0, "one-missed-sample valid-event gap is not approximately 120 seconds", errors)
    check(missed_sample.get("gap_exceeds_h150_max_internal_gap") is True, "one-missed-sample gap does not exceed H150 gap limit", errors)
    check(missed_sample.get("h150_history_reset") is True, "one-missed-sample H150 reset consequence missing", errors)
    check(missed_sample.get("slope_status_until_rebuilt") == "FEATURE_UNAVAILABLE_GAP_RESTART", "one-missed-sample slope-unavailable status drift", errors)
    check(missed_sample.get("gap_rule_relaxation_allowed") is False, "H150 gap rule was relaxed for 60-second cadence", errors)
    check("120 seconds" in str(missed_sample.get("statement", "")) and "90-second" in str(missed_sample.get("statement", "")), "one-missed-sample consequence statement incomplete", errors)

    configuration = manifest.get("configuration_metadata_contract") or {}
    check(configuration.get("effective_model_input_cadence_sec") == EXPECTED_EFFECTIVE_CADENCE_SECONDS, "configuration metadata effective cadence drift", errors)
    check(configuration.get("normal_co2_export_cadence_sec") == EXPECTED_NORMAL_EXPORT_CADENCE_SECONDS, "configuration metadata normal export cadence drift", errors)

    freshness = manifest.get("freshness_contract") or {}
    check(freshness.get("logger_poll_event_distinct") is True, "logger poll is not separated", errors)
    check(freshness.get("transport_packet_event_distinct") is True, "transport packet is not separated", errors)
    check(freshness.get("fresh_scd40_measurement_event_distinct") is True, "fresh sensor event is not separated", errors)
    check(freshness.get("transport_freshness_is_not_sensor_freshness") is True, "transport/sensor freshness distinction missing", errors)
    h150 = freshness.get("h150_contract") or {}
    for key, expected in (("profile", "ENDPOINT_H150"), ("method", "ENDPOINT_DIFFERENCE"), ("history_duration_seconds", 150.0), ("causality", "PAST_ONLY"), ("max_internal_gap_seconds", 90.0)):
        check(h150.get(key) == expected, f"H150 contract drift: {key}", errors)
    for key in ("interpolation_allowed", "future_samples_allowed", "centered_window_allowed"):
        check(h150.get(key) is False, f"H150 forbidden behavior not blocked: {key}", errors)

    timestamps = manifest.get("timestamp_contract") or {}
    clock_fields = {entry.get("field") for entry in timestamps.get("required_clocks") or []}
    check({"sensor_event_monotonic_ms", "logger_monotonic_ns", "logger_timestamp_utc", "pi_receive_timestamp_utc", "ground_truth_event_timestamp_utc"}.issubset(clock_fields), "timestamp contract is incomplete", errors)
    check(timestamps.get("no_stronger_sync_claim") is True, "timestamp synchronization overclaim guard missing", errors)

    sessions = manifest.get("session_contract") or {}
    check(sessions.get("session_id_immutable") is True, "session ID is not immutable", errors)
    check(set(sessions.get("allowed_scenarios") or []) == {"VACANT_STABLE", "OCCUPIED_STABLE", "VACANT_TO_OCCUPIED", "OCCUPIED_TO_VACANT"}, "session scenario registry drift", errors)
    completion = sessions.get("scenario_completion_rules") or {}
    check(set(completion) == set(sessions.get("allowed_scenarios") or []), "scenario completion rules incomplete", errors)
    check(sessions.get("history_crossing_sessions_allowed") is False, "session history crossing not blocked", errors)

    gt = manifest.get("ground_truth_contract") or {}
    check(set(gt.get("labels") or []) == {"VACANT", "OCCUPIED"}, "ground-truth labels drift", errors)
    check(set(gt.get("prohibited_sources") or []) >= {"CO2", "CO2_slope", "B5 prediction", "B5 probability"}, "ground-truth independence prohibition incomplete", errors)
    check("CONFIRMED_OPERATOR_CONTROLLED" in (gt.get("valid_statuses") or []), "confirmed ground-truth status missing", errors)
    check(gt.get("formal_metrics_rule"), "formal ground-truth metrics rule missing", errors)

    failures = manifest.get("failure_state_contract") or {}
    required_failures = {"SENSOR_READ_FAILED", "SENSOR_DATA_NOT_READY", "SENSOR_INVALID", "TRANSPORT_DISCONNECTED", "TRANSPORT_STALE", "LOGGER_ERROR", "DEVICE_RESTART", "SESSION_INTERRUPTED", "GROUND_TRUTH_MISSING", "CONFIGURATION_UNKNOWN", "PROTOCOL_DEVIATION"}
    check(required_failures.issubset(set(failures.get("required_statuses") or [])), "failure-state registry incomplete", errors)
    check("never forward-fill" in str(failures.get("row_policy", "")).lower(), "fail-closed row policy missing", errors)

    raw_contract = manifest.get("raw_immutability_contract") or {}
    check(raw_contract.get("checksum_algorithm") == "SHA-256", "checksum algorithm drift", errors)
    check(raw_contract.get("canonical_raw_format") == "JSONL one event per line, UTF-8, newline-delimited, no post-capture edits", "raw format contract drift", errors)
    check(len(raw_contract.get("capture_finalization_order") or []) >= 6, "raw finalization sequence is incomplete", errors)
    check("checksums.sha256" in (raw_contract.get("required_handoff_files") or []), "checksum handoff file missing", errors)

    compliance = manifest.get("protocol_compliance_classification") or {}
    expected_statuses = {"PROTOCOL_COMPLIANT", "PROTOCOL_COMPLIANT_WITH_LIMITATIONS", "PROTOCOL_NONCOMPLIANT", "PROTOCOL_STATUS_UNKNOWN"}
    check(expected_statuses.issubset(set(compliance.get("statuses") or [])), "protocol compliance statuses incomplete", errors)
    check(compliance.get("blocking_violations"), "protocol blocking violations missing", errors)
    check("Preserve" in str(compliance.get("noncompliant_data_policy", "")), "noncompliant preservation policy missing", errors)

    c2 = manifest.get("c_c2_intake_requirements") or {}
    check(c2.get("formal_validation_status_before_c2") == "NO", "C-C2 pre-metric status drift", errors)
    check(c2.get("metrics_authorized_in_c1") is False, "C-C1 metric authorization drift", errors)
    check(c2.get("b5_inference_authorized_in_c1") is False, "C-C1 B5 authorization drift", errors)

    handoff = manifest.get("operator_handoff") or {}
    for key, expected in (("technical_protocol_path", TECHNICAL_REL), ("operator_prompt_path", PROMPT_REL), ("validator_path", VALIDATOR_REL), ("validation_result_path", RESULT_REL), ("checksums_path", CHECKSUMS_REL)):
        check(handoff.get(key) == expected, f"operator handoff path drift: {key}", errors)
        if key != "validation_result_path" and key != "checksums_path":
            check((root / expected).is_file(), f"missing handoff artifact: {expected}", errors)
    check(handoff.get("physical_collection_performed_in_c1") is False, "physical collection was not explicitly blocked", errors)
    check((manifest.get("validation") or {}).get("validator_result_status") == "PASS", "manifest validator result status is not PASS", errors)

    technical_path = root / TECHNICAL_REL
    prompt_path = root / PROMPT_REL
    if technical_path.is_file():
        technical_text = technical_path.read_text(encoding="utf-8")
        check(EXPECTED_PROTOCOL_ID in technical_text, "technical protocol does not contain protocol ID", errors)
        check("C_C1_PROTOCOL_FROZEN: YES" in technical_text, "technical protocol does not contain frozen exit gate", errors)
        check("B5 inference" in technical_text or "B5 inference" in technical_text.lower(), "technical protocol missing B5 boundary", errors)
        check("Effective SafeNest model-input cadence" in technical_text, "technical protocol missing effective cadence section", errors)
        check("SAFENEST_EFFECTIVE_MODEL_INPUT_CADENCE: 60 seconds nominal" in technical_text, "technical protocol missing 60-second model-input cadence", errors)
        check("SAFENEST_NORMAL_CO2_EXPORT_CADENCE: 60 seconds nominal" in technical_text, "technical protocol missing 60-second normal export cadence", errors)
        check("SCD40_NATIVE_MEASUREMENT_CADENCE: configured/observed separately" in technical_text, "technical protocol does not separate native SCD40 cadence", errors)
        check("120 > 90" in technical_text, "technical protocol missing one-missed-sample H150 consequence", errors)
    if prompt_path.is_file():
        prompt_text = prompt_path.read_text(encoding="utf-8")
        check(EXPECTED_PROTOCOL_ID in prompt_text, "operator prompt does not contain protocol ID", errors)
        check("Do not use the legacy capture script unchanged." in prompt_text, "operator prompt does not block legacy capture reuse", errors)
        check("run b5" in prompt_text.lower(), "operator prompt does not block B5", errors)
        check("checksums.sha256" in prompt_text, "operator prompt missing checksum finalization", errors)
        check("effective SafeNest model-input cadence: 60 seconds nominal" in prompt_text, "operator prompt missing 60-second model-input cadence", errors)
        check("normal SafeNest CO2 export cadence: 60 seconds nominal" in prompt_text, "operator prompt missing 60-second normal export cadence", errors)
        check("Do not reuse an old cached measurement merely to satisfy the 60-second schedule." in prompt_text, "operator prompt missing stale-reuse prohibition", errors)
        check("same verified fresh SCD40 measurement event" in prompt_text, "operator prompt missing same-fresh-event rule", errors)
        check("approximately 120-second gap" in prompt_text, "operator prompt missing one-missed-sample consequence", errors)

    validate_checksums(root, manifest, errors)

    non_authorizations = manifest.get("non_authorizations") or {}
    for key, value in non_authorizations.items():
        if key in {"physical_measurement", "new_raw_payload", "b5_inference", "formal_metrics", "model_retraining", "scaler_refit", "threshold_change", "c_c2_start", "c_d_start"}:
            check(value is False, f"non-authorization drift: {key}", errors)

    return result_payload(errors, warnings)


def result_payload(errors: list[str], warnings: list[str]) -> dict[str, Any]:
    return {
        "validator_id": "CO2_C_C1_MEASUREMENT_PROTOCOL_VALIDATOR_001",
        "protocol_id": EXPECTED_PROTOCOL_ID,
        "protocol_version": EXPECTED_PROTOCOL_VERSION,
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "c_c1_protocol_frozen": True,
        "physical_collection_performed": False,
        "b5_inference_performed": False,
        "formal_device_domain_validation": "NO",
        "model_modified": False,
        "scaler_refit": False,
        "threshold_changed": False,
        "c_c2_started": False,
        "c_d_started": False,
        "validated_artifacts": [
            MANIFEST_REL,
            TECHNICAL_REL,
            PROMPT_REL,
            VALIDATOR_REL,
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--write-result", action="store_true")
    args = parser.parse_args()
    result = validate(args.root.resolve())
    if args.write_result:
        output = args.root.resolve() / RESULT_REL
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
