from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.validate_co2_c_c1r_reduced_measurement_protocol import (
    PROTOCOL_PATH,
    validate,
)


class Cc1rProtocolTest(unittest.TestCase):
    def test_current_contract_passes_with_handoff_hold(self) -> None:
        result = validate()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["phase_result"], "C_C1R_BLOCKED")
        self.assertFalse(result["physical_acquisition_authorized"])
        self.assertFalse(result["c_c2_started"])
        self.assertEqual(result["candidate_id"], "C_B6_REDUCED_CO2_SLOPE_CANDIDATE_001")

    def test_reduced_model_contract_excludes_temperature_and_humidity(self) -> None:
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        model = protocol["model_contract"]
        self.assertEqual(model["required_model_sensor_fields"], ["CO2"])
        self.assertEqual(model["required_derived_fields"], ["CO2_slope"])
        self.assertFalse(model["temperature_required_for_model"])
        self.assertFalse(model["humidity_required_for_model"])
        self.assertEqual(model["co2_slope_computed_by"], "Pi_or_downstream_postprocessing")

    def test_validator_rejects_contract_relaxations(self) -> None:
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        protocol["model_contract"]["temperature_required_for_model"] = True
        protocol["cadence_contract"]["effective_model_input_interval_sec"] = 61
        protocol["freshness_contract"]["stale_reuse"] = "ALLOWED"
        protocol["physical_acquisition_authorized"] = True

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "protocol.json"
            path.write_text(json.dumps(protocol), encoding="utf-8")
            result = validate(path)

        self.assertEqual(result["status"], "FAIL")
        self.assertIn("TEMPERATURE_REQUIRED_FOR_MODEL", result["errors"])
        self.assertIn("EFFECTIVE_CADENCE_NOT_60_SEC", result["errors"])
        self.assertIn("STALE_REUSE_ALLOWED", result["errors"])
        self.assertIn("PHYSICAL_ACQUISITION_AUTHORIZED_WITH_BLOCKER", result["errors"])

    def test_protocol_preserves_historical_c_c1_relation(self) -> None:
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        historical = protocol["predecessor_lineage"]["historical_c_c1"]
        self.assertEqual(historical["protocol_id"], "CO2_C_C1_MEASUREMENT_PROTOCOL_001")
        self.assertEqual(historical["feature_contract"], ["CO2", "Temperature", "Humidity", "CO2_slope"])
        self.assertFalse(historical["rewritten"])

    def test_protocol_requires_independent_ground_truth_and_raw_sealing(self) -> None:
        protocol = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
        ground_truth = protocol["ground_truth_contract"]
        raw = protocol["raw_preservation_contract"]
        self.assertTrue(ground_truth["independent_ground_truth_required_for_c_c2"])
        self.assertFalse(ground_truth["derived_from_co2"])
        self.assertFalse(ground_truth["derived_from_model_output"])
        self.assertIn("checksums.sha256", raw["bundle_files"])
        self.assertTrue(raw["append_only"])


if __name__ == "__main__":
    unittest.main()
