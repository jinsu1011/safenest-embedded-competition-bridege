#!/usr/bin/env python3
"""Focused M-N10 protocol-lock checks. No sensor capture. No reserved inference."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.mmwave_m_n10_capture_protocol import (
    DEV_ROLE,
    MIN_NEW_SUBJECTS,
    MIN_RESERVED_SUBJECTS,
    PROTOCOL_ID,
    RESERVED_ROLE,
    assign_subject_roles,
    m_n11_authorized,
    protocol_self_check,
    refuse_reserved_inference,
    split_counts,
)

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "config/mmwave/m_n10_capture_protocol_lock.json"
PARTITION = ROOT / "datasets/mmwave/manifests/m_n10_subject_partition.json"
CAPTURE = ROOT / "datasets/mmwave/manifests/m_n10_capture_manifest.json"
INT8 = ROOT / "models/mmwave/m_n9/MMWAVE_M_N9_FULL_INT8_V1.tflite"
SCRIPT = ROOT / "scripts/mmwave_m_n10_capture_protocol.py"


class TestMmwaveMN10CaptureProtocol(unittest.TestCase):
    def test_protocol_lock_identity(self) -> None:
        self.assertEqual(protocol_self_check(), [])
        doc = json.loads(LOCK.read_text())
        self.assertEqual(doc["protocol_id"], PROTOCOL_ID)
        self.assertEqual(doc["status"], "LOCKED_BEFORE_HUMAN_CAPTURE")
        self.assertEqual(doc["subjects"]["minimum_new_subjects"], MIN_NEW_SUBJECTS)
        self.assertEqual(doc["subjects"]["minimum_m_n11_reserved_subjects"], MIN_RESERVED_SUBJECTS)
        self.assertTrue(doc["presence_gate_required"])
        self.assertFalse(doc["empty_treated_as_apnea_gt"])
        self.assertFalse(doc["independent_respiratory_reference"]["new_rr_thresholds_invented"])
        self.assertEqual(doc["label_profile_id"], "MMWAVE_LABEL_MAPPING_PROFILE_001")
        self.assertEqual(
            doc["source_int8"]["sha256"],
            "3b008af4be0facc4037c2afd3fe39292fb794208eb4370dbe6916b2d15aa38a4",
        )
        self.assertTrue(INT8.is_file())
        self.assertEqual(doc["m_n11_reserved_access"]["reserved_model_inference_count"], 0)
        self.assertFalse(doc["formal_model_accuracy_computed"])

    def test_partition_examples(self) -> None:
        self.assertEqual(split_counts(6), (2, 4))
        self.assertEqual(split_counts(8), (3, 5))
        self.assertEqual(split_counts(9), (3, 6))
        ids = [f"MN10-S{i:03d}" for i in range(1, 9)]
        assigned = assign_subject_roles(ids)
        self.assertEqual(assigned["n_dev"] + assigned["n_reserved"], 8)
        self.assertGreaterEqual(assigned["n_reserved"], 4)
        self.assertEqual(assigned["overlap"], [])
        self.assertEqual(len(set(assigned[DEV_ROLE]) & set(assigned[RESERVED_ROLE])), 0)

    def test_no_subjects_yet_does_not_authorize_m_n11(self) -> None:
        capture = json.loads(CAPTURE.read_text())
        partition = json.loads(PARTITION.read_text())
        self.assertEqual(capture["status"], "CAPTURE_NOT_PERFORMED")
        self.assertEqual(partition["status"], "RULE_LOCKED_NO_SUBJECTS_ASSIGNED")
        ok, missing = m_n11_authorized(capture, partition)
        self.assertFalse(ok)
        self.assertFalse(capture["M_N11_AUTHORIZED"])
        self.assertIn("independent_respiratory_reference_available == false", missing)
        self.assertEqual(capture["reserved_model_inference_count"], 0)

    def test_reserved_inference_forbidden(self) -> None:
        with self.assertRaises(RuntimeError):
            refuse_reserved_inference(RESERVED_ROLE)
        text = SCRIPT.read_text()
        self.assertNotIn("tf.keras", text)
        self.assertNotIn("Interpreter", text)
        self.assertNotIn("predict(", text)
        self.assertNotIn("NEW_MODEL_HELDOUT_TEST", text)


if __name__ == "__main__":
    unittest.main()
