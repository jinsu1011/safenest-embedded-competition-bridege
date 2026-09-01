"""Canonical-path checks for the M-N9 mmWave INT8 overlay.

Selector matches yuname121/integration main. Live adapter is still
inference/mmwave_interpreter.py until a later runtime-wiring PR.
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from paths import MODEL_MANIFEST, ONDEVICE_AI_ROOT, REPOSITORY_ROOT  # noqa: E402

EXPECTED_SHA = "3b008af4be0facc4037c2afd3fe39292fb794208eb4370dbe6916b2d15aa38a4"
SOURCE_SHA = "390f3be3d75987a79a0e0438ba8a9d5e9e19dc97"
BASE_ONDEVICE_SHA = "4129753e64e0f18a3491e5b6cc0454b0d36f1610"
INTEGRATION_MAIN = "66b52312fc8e3350773909b6be9cd90fc2051150"


class TestMmwaveMN9TeamImport(unittest.TestCase):
    def test_artifact_is_under_canonical_ondevice_ai_root(self) -> None:
        artifact = ONDEVICE_AI_ROOT / "models/mmwave/m_n9/MMWAVE_M_N9_FULL_INT8_V1.tflite"
        self.assertTrue(artifact.is_file())
        self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(), EXPECTED_SHA)
        self.assertFalse((REPOSITORY_ROOT / "ondevice_ai").exists())

    def test_component_sources_keeps_ondevice_base_sha(self) -> None:
        payload = json.loads((REPOSITORY_ROOT / "COMPONENT_SOURCES.json").read_text(encoding="utf-8"))
        component = payload["components"]["ondevice_ai"]
        self.assertEqual(component["upstream_commit"], BASE_ONDEVICE_SHA)
        self.assertEqual(component["integration_path"], "RaspberryPi/Ondevice_AI")
        overlay = component["overlays"][0]
        self.assertEqual(overlay["name"], "mmwave_m_n9_full_int8")
        self.assertEqual(overlay["upstream_commit"], SOURCE_SHA)
        self.assertFalse(overlay["runtime_promoted"])
        self.assertEqual(payload["upstream_repositories"]["integration"]["head_commit"], INTEGRATION_MAIN)
        self.assertIs(payload["model_promotion_policy"]["automatic_promotion_performed"], False)

    def test_team_handoff_report_exists(self) -> None:
        handoff = (
            ONDEVICE_AI_ROOT
            / "docs/reports/20260818_SafeNest_mmWave_M-N9_Team_Import_Handoff_KO_01.md"
        )
        self.assertTrue(handoff.is_file())
        text = handoff.read_text(encoding="utf-8")
        self.assertIn("MMWAVE_M_N9_FULL_INT8_V1", text)
        self.assertIn(EXPECTED_SHA, text)
        self.assertIn("DEVICE_VALIDATED = NO", text)
        self.assertIn("PRESENCE_GATE_REQUIRED = YES", text)

    def test_manifest_selector_is_b23_and_mn9_is_legacy(self) -> None:
        manifest = json.loads(MODEL_MANIFEST.read_text(encoding="utf-8"))
        active = manifest["models"]["mmwave"]
        self.assertEqual(active["model_id"], "M-PV2_FAMILY_B_TRACE_TCN_BREATHING_RR_QUALITY")
        self.assertEqual(active["runtime_role"], "ACTIVE_B23_PROTOTYPE")
        self.assertTrue(active["active_runtime_selector"])
        self.assertTrue(active["HISTORICAL_B_NOT_ACTIVE"])
        self.assertFalse(active["DEVICE_VALIDATED"])
        self.assertEqual(active["sha256"], "8f7de6f50d6ff62ff9b0ebfaed0b1fccd8d194c7e33781bc5b93366fae251a2c")
        legacy = manifest["models"]["mmwave_m_n9"]
        self.assertEqual(legacy["model_id"], "MMWAVE_M_N9_FULL_INT8_V1")
        self.assertEqual(legacy["runtime_role"], "LEGACY_M_N9_NONACTIVE")
        self.assertFalse(legacy["deployment_allowed"])
        runtime = (RUNTIME_ROOT / "ai" / "runtime.py").read_text(encoding="utf-8")
        self.assertIn("mmwave_m_n9_interpreter.py", runtime)
        pipeline = (RUNTIME_ROOT / "ai" / "pipeline.py").read_text(encoding="utf-8")
        self.assertIn("B23TeamRuntime", pipeline)
        self.assertNotIn("MR60CanonicalWindowBuilder", pipeline)


if __name__ == "__main__":
    unittest.main()
