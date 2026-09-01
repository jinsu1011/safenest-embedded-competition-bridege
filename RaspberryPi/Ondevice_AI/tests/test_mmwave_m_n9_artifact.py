"""Focused M-N9 artifact identity tests. No training. No live sensor. No Pi."""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.mmwave_m_n4_canonical import (  # noqa: E402
    CONTRACT_ID,
    SAMPLE_COUNT,
    accept_phase_events,
    apply_s1,
    contract_self_check,
    CanonicalContractError,
)

EXPECTED_SHA = "3b008af4be0facc4037c2afd3fe39292fb794208eb4370dbe6916b2d15aa38a4"
SOURCE_SHA = "390f3be3d75987a79a0e0438ba8a9d5e9e19dc97"
ARTIFACT = PROJECT_ROOT / "models/mmwave/m_n9/MMWAVE_M_N9_FULL_INT8_V1.tflite"
LOCK = PROJECT_ROOT / "config/mmwave/m_n9_full_int8_artifact_lock.json"
CONTRACT = PROJECT_ROOT / "config/mmwave/m_n4_canonical_input_dataset_contract.json"
MANIFEST = PROJECT_ROOT / "models/model_manifest.json"
HISTORICAL_CONTRACT = PROJECT_ROOT / "config/mmwave_input_contract.yaml"


class TestMmwaveMN9Artifact(unittest.TestCase):
    def test_int8_sha_and_size(self) -> None:
        self.assertTrue(ARTIFACT.is_file())
        self.assertEqual(ARTIFACT.stat().st_size, 11816)
        self.assertEqual(hashlib.sha256(ARTIFACT.read_bytes()).hexdigest(), EXPECTED_SHA)

    def test_lock_matches_bytes(self) -> None:
        lock = json.loads(LOCK.read_text(encoding="utf-8"))
        self.assertEqual(lock["artifact_id"], "MMWAVE_M_N9_FULL_INT8_V1")
        self.assertEqual(lock["artifact_sha256"], EXPECTED_SHA)
        self.assertEqual(lock["contract_id"], CONTRACT_ID)
        self.assertEqual(lock["input_contract"]["shape"], [1, 240, 1])
        self.assertEqual(lock["input_contract"]["dtype"], "int8")
        self.assertTrue(lock["presence_gate"]["PRESENCE_GATE_REQUIRED"])
        self.assertFalse(lock["DEVICE_VALIDATED"])
        self.assertFalse(lock["production_final_runtime"])

    def test_m_n4_contract_is_240_not_300(self) -> None:
        doc = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(doc["contract_id"], CONTRACT_ID)
        self.assertEqual(doc["resampling"]["sample_count"], SAMPLE_COUNT)
        self.assertEqual(doc["resampling"]["target_rate_hz"], 8.0)
        self.assertEqual(doc["resampling"]["input_shape"], [1, 240, 1])
        self.assertTrue(doc["scale"]["divide_only_no_centering"])
        self.assertFalse(doc["historical_b_input_inherited"])
        self.assertEqual(doc["timing"]["production_if_freshness_unavailable"], "WINDOW_UNAVAILABLE")
        self.assertFalse(doc["timing"]["legacy_row_timestamp_fallback_in_production"])

    def test_historical_300_sample_contract_preserved(self) -> None:
        text = HISTORICAL_CONTRACT.read_text(encoding="utf-8")
        self.assertIn("window_samples: 300", text)
        self.assertIn("sample_rate_hz: 10", text)

    def test_manifest_keeps_blocked_v0_1_0_and_adds_m_n9(self) -> None:
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        historical = manifest["models"]["mmwave"]
        self.assertEqual(historical["path"], "models/mmwave/mmwave_resp_int8_v0.1.0.tflite")
        self.assertIs(historical["deployment_allowed"], False)
        self.assertEqual(historical["block_reason"], "CLASS_COLLAPSE_ON_REPOSITORY_NPZ")

        locked = manifest["models"]["mmwave_m_n9"]
        self.assertEqual(locked["model_id"], "MMWAVE_M_N9_FULL_INT8_V1")
        self.assertEqual(locked["sha256"], EXPECTED_SHA)
        self.assertEqual(locked["path"], "models/mmwave/m_n9/MMWAVE_M_N9_FULL_INT8_V1.tflite")
        self.assertEqual(locked["input"]["shape"], [1, 240, 1])
        self.assertIs(locked["deployment_allowed"], False)
        self.assertTrue(locked["locked_for_next_runtime_wiring"])
        self.assertEqual(locked["source_sha"], SOURCE_SHA)
        self.assertTrue(locked["PRESENCE_GATE_REQUIRED"])

        pointer = manifest["mmwave_active_locked_artifact"]
        self.assertEqual(pointer["artifact_id"], "MMWAVE_M_N9_FULL_INT8_V1")
        self.assertEqual(pointer["runtime_default_key"], "mmwave")
        self.assertFalse(pointer["runtime_wired"])

    def test_m_n4_helpers_reject_production_without_freshness(self) -> None:
        self.assertEqual(contract_self_check(), [])
        zeros, mad, collapsed = apply_s1(np.zeros(240))
        self.assertTrue(collapsed)
        self.assertEqual(mad, 0.0)
        self.assertTrue(np.all(zeros == 0))
        t = np.arange(0, 30000, 100, dtype=np.float64)
        x = np.sin(2 * np.pi * 0.25 * t / 1000.0)
        with self.assertRaises(CanonicalContractError) as ctx:
            accept_phase_events(t, x, None, production=True, timestamps_are_seconds=False)
        self.assertEqual(str(ctx.exception), "PRODUCTION_FRESHNESS_UNAVAILABLE")

    def test_mac_tflite_load_and_zero_invoke_if_available(self) -> None:
        interpreter_mod = None
        try:
            import ai_edge_litert.interpreter as interpreter_mod  # type: ignore
        except ImportError:
            try:
                import tflite_runtime.interpreter as interpreter_mod  # type: ignore
            except ImportError:
                try:
                    import tensorflow.lite as interpreter_mod  # type: ignore
                except ImportError:
                    try:
                        import tensorflow as tf  # type: ignore

                        interpreter_mod = tf.lite
                    except ImportError:
                        self.skipTest("no TFLite interpreter on this Mac")

        interpreter = interpreter_mod.Interpreter(model_path=str(ARTIFACT))
        interpreter.allocate_tensors()
        inp = interpreter.get_input_details()[0]
        out = interpreter.get_output_details()[0]
        self.assertEqual(list(inp["shape"]), [1, 240, 1])
        self.assertEqual(np.dtype(inp["dtype"]), np.dtype(np.int8))
        self.assertEqual(list(out["shape"]), [1, 3])
        scale, zp = inp["quantization"]
        self.assertAlmostEqual(scale, 0.5623255372047424, places=6)
        self.assertEqual(zp, 4)
        interpreter.set_tensor(inp["index"], np.zeros((1, 240, 1), dtype=np.int8))
        interpreter.invoke()
        result = interpreter.get_tensor(out["index"])
        self.assertEqual(result.shape, (1, 3))
        self.assertEqual(result.dtype, np.int8)


if __name__ == "__main__":
    unittest.main()
