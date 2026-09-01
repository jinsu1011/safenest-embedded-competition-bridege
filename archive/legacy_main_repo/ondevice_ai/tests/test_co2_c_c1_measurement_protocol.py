"""Focused tests for the frozen CO2 C-C1 measurement contract."""

from __future__ import annotations

from pathlib import Path

from scripts.validate_co2_c_c1_measurement_protocol import (
    EXPECTED_B5_FEATURES,
    MANIFEST_REL,
    validate,
)


ROOT = Path(__file__).resolve().parent.parent


def test_c_c1_protocol_validator_passes() -> None:
    result = validate(ROOT)
    assert result["status"] == "PASS", result["errors"]
    assert result["c_c1_protocol_frozen"] is True
    assert result["physical_collection_performed"] is False
    assert result["b5_inference_performed"] is False
    assert result["formal_device_domain_validation"] == "NO"


def test_manifest_keeps_all_four_frozen_features() -> None:
    import json

    manifest = json.loads((ROOT / MANIFEST_REL).read_text(encoding="utf-8"))
    assert [entry["name"] for entry in manifest["required_features"]] == EXPECTED_B5_FEATURES
    assert manifest["frozen_b5_reference"]["feature_order"] == EXPECTED_B5_FEATURES
    assert manifest["frozen_b5_reference"]["slope_profile"] == "ENDPOINT_H150"


def test_manifest_separates_transport_and_sensor_freshness() -> None:
    import json

    manifest = json.loads((ROOT / MANIFEST_REL).read_text(encoding="utf-8"))
    freshness = manifest["freshness_contract"]
    assert freshness["logger_poll_event_distinct"] is True
    assert freshness["transport_packet_event_distinct"] is True
    assert freshness["fresh_scd40_measurement_event_distinct"] is True
    assert freshness["transport_freshness_is_not_sensor_freshness"] is True


def test_manifest_freezes_downstream_cadence_without_rewriting_native_sensor_timing() -> None:
    import json

    manifest = json.loads((ROOT / MANIFEST_REL).read_text(encoding="utf-8"))
    cadence = manifest["effective_model_input_cadence"]
    assert cadence["nominal_interval_sec"] == 60.0
    assert cadence["native_sensor_measurement_cadence_is_separate"] is True
    assert cadence["requires_verified_fresh_scd40_event"] is True
    assert cadence["stale_reuse_for_schedule_compliance"] == "FORBIDDEN"
    assert cadence["required_coherent_fields"] == ["CO2", "Temperature", "Humidity"]
    assert cadence["normal_export"]["nominal_interval_sec"] == 60.0
    assert cadence["normal_export"]["same_event_as_model_input"] is True
    missed = cadence["one_missed_sample_consequence"]
    assert missed["resulting_valid_event_gap_sec"] == 120.0
    assert missed["h150_history_reset"] is True
    assert missed["gap_rule_relaxation_allowed"] is False


def test_manifest_preserves_fail_closed_and_independent_ground_truth() -> None:
    import json

    manifest = json.loads((ROOT / MANIFEST_REL).read_text(encoding="utf-8"))
    failures = set(manifest["failure_state_contract"]["required_statuses"])
    assert {"SENSOR_READ_FAILED", "SENSOR_DATA_NOT_READY", "TRANSPORT_STALE", "SESSION_INTERRUPTED"} <= failures
    ground_truth = manifest["ground_truth_contract"]
    assert set(ground_truth["labels"]) == {"VACANT", "OCCUPIED"}
    assert {"CO2", "CO2_slope", "B5 prediction", "B5 probability"} <= set(ground_truth["prohibited_sources"])
