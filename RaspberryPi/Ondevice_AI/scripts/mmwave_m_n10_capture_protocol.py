#!/usr/bin/env python3
"""M-N10 capture-protocol helpers.

Locks subject-partition arithmetic and M-N11 authorization checks.
Does not capture sensors, does not run FLOAT/INT8 inference, and must not
inspect reserved-subject predictions.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "config/mmwave/m_n10_capture_protocol_lock.json"
PARTITION_PATH = ROOT / "datasets/mmwave/manifests/m_n10_subject_partition.json"
CAPTURE_MANIFEST_PATH = ROOT / "datasets/mmwave/manifests/m_n10_capture_manifest.json"
PROTOCOL_ID = "MMWAVE_M_N10_CAPTURE_PROTOCOL_V1"
PARTITION_NAMESPACE = "MMWAVE_M_N10_SUBJECT_PARTITION_V1"
PARTITION_SEED = 20260818
MIN_NEW_SUBJECTS = 6
MIN_RESERVED_SUBJECTS = 4
DEV_ROLE = "M_N10_DEVELOPMENT_REFERENCE"
RESERVED_ROLE = "M_N11_FORMAL_VALIDATION_RESERVED"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def assignment_key(subject_id: str) -> str:
    return sha256_text(f"{PARTITION_NAMESPACE}:{PARTITION_SEED}:{subject_id}")


def split_counts(n_subjects: int) -> tuple[int, int]:
    """Approximately 1/3 DEV, 2/3 RESERVED. When N>=6, RESERVED >= 4."""
    if n_subjects <= 0:
        return 0, 0
    n_dev = int(round(n_subjects / 3.0))
    n_reserved = n_subjects - n_dev
    if n_subjects >= MIN_NEW_SUBJECTS and n_reserved < MIN_RESERVED_SUBJECTS:
        n_reserved = MIN_RESERVED_SUBJECTS
        n_dev = n_subjects - n_reserved
    if n_dev < 1 and n_subjects >= 2:
        n_dev = 1
        n_reserved = n_subjects - 1
    return n_dev, n_reserved


def assign_subject_roles(subject_ids: list[str]) -> dict[str, Any]:
    unique = sorted(set(subject_ids))
    if len(unique) != len(subject_ids):
        raise ValueError("DUPLICATE_SUBJECT_ID")
    n_dev, n_reserved = split_counts(len(unique))
    ordered = sorted(unique, key=lambda sid: (assignment_key(sid), sid))
    dev = ordered[:n_dev]
    reserved = ordered[n_dev:]
    overlap = sorted(set(dev) & set(reserved))
    if overlap:
        raise ValueError("SUBJECT_OVERLAP")
    if len(dev) + len(reserved) != len(unique):
        raise ValueError("SUBJECT_COUNT_MISMATCH")
    return {
        "rule_id": PARTITION_NAMESPACE,
        "protocol_id": PROTOCOL_ID,
        "status": "ASSIGNED" if unique else "RULE_LOCKED_NO_SUBJECTS_ASSIGNED",
        "split_unit": "SUBJECT",
        "namespace": PARTITION_NAMESPACE,
        "seed": PARTITION_SEED,
        "physical_subject_overlap_allowed": False,
        "assignment_after_predictions_forbidden": True,
        "subjects_assigned": unique,
        DEV_ROLE: dev,
        RESERVED_ROLE: reserved,
        "overlap": overlap,
        "n_dev": len(dev),
        "n_reserved": len(reserved),
        "assignment_keys": {sid: assignment_key(sid) for sid in unique},
    }


def m_n11_authorized(capture: dict[str, Any], partition: dict[str, Any]) -> tuple[bool, list[str]]:
    missing: list[str] = []
    if int(capture.get("new_physical_subjects") or 0) < MIN_NEW_SUBJECTS:
        missing.append("new_physical_subjects < 6")
    if int(partition.get("n_reserved") or 0) < MIN_RESERVED_SUBJECTS:
        missing.append("m_n11_reserved_physical_subjects < 4")
    if partition.get("overlap"):
        missing.append("dev_reserved_overlap != 0")
    if not capture.get("independent_respiratory_reference_available"):
        missing.append("independent_respiratory_reference_available == false")
    if not capture.get("reference_alignment_verified"):
        missing.append("reference_alignment_verified == false")
    if not capture.get("mr60_raw_sha_locked"):
        missing.append("raw_mr60_lineage_locked == false")
    if not capture.get("reference_raw_sha_locked"):
        missing.append("raw_reference_lineage_locked == false")
    if int(capture.get("reserved_model_inference_count") or 0) != 0:
        missing.append("reserved_model_inference_count != 0")
    if capture.get("reserved_float_inference") or capture.get("reserved_int8_inference"):
        missing.append("reserved_model_inference_performed")
    if capture.get("status") != "CAPTURE_COMPLETE":
        missing.append("capture_not_complete")
    return (not missing), missing


def refuse_reserved_inference(role: str) -> None:
    if role == RESERVED_ROLE:
        raise RuntimeError("M_N11_RESERVED_INFERENCE_FORBIDDEN_IN_M_N10")


def load_protocol() -> dict[str, Any]:
    return json.loads(PROTOCOL_PATH.read_text())


def protocol_self_check() -> list[str]:
    errors: list[str] = []
    doc = load_protocol()
    if doc.get("protocol_id") != PROTOCOL_ID:
        errors.append("PROTOCOL_ID")
    if doc.get("status") != "LOCKED_BEFORE_HUMAN_CAPTURE":
        errors.append("STATUS")
    if doc.get("contract_id") != "MMWAVE_MR60_COMPAT_INPUT_DATASET_V1":
        errors.append("CONTRACT")
    if doc.get("label_profile_id") != "MMWAVE_LABEL_MAPPING_PROFILE_001":
        errors.append("LABEL_PROFILE")
    if not doc.get("presence_gate_required"):
        errors.append("PRESENCE_GATE")
    if doc["source_int8"]["sha256"] != "3b008af4be0facc4037c2afd3fe39292fb794208eb4370dbe6916b2d15aa38a4":
        errors.append("INT8_SHA")
    if doc["independent_respiratory_reference"].get("new_rr_thresholds_invented"):
        errors.append("RR_THRESHOLDS_INVENTED")
    if doc["m_n11_reserved_access"].get("reserved_model_inference_count") != 0:
        errors.append("RESERVED_INFERENCE")
    return errors


if __name__ == "__main__":
    errors = protocol_self_check()
    capture = json.loads(CAPTURE_MANIFEST_PATH.read_text())
    partition = json.loads(PARTITION_PATH.read_text())
    ok, missing = m_n11_authorized(capture, partition)
    print(
        json.dumps(
            {
                "protocol_self_check": errors or "PASS",
                "M_N11_AUTHORIZED": ok,
                "missing": missing,
                "capture_status": capture.get("status"),
            },
            indent=2,
        )
    )
    raise SystemExit(0 if not errors else 1)
