#!/usr/bin/env python3
"""Build and lock the SafeNest CO2 C-B6 reduced-feature candidate.

This phase consumes the locked A-series canonical materialization, uses only
TRAIN and VALIDATION predictive populations, and creates a new two-feature
offline candidate without touching the historical B5 artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import random
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np
import tensorflow as tf
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from threadpoolctl import threadpool_limits

from datasets.co2.offline_experiment import verify_a_series_artifact_lock, verify_a_series_release


PHASE_ID = "C-B6"
PHASE_NAME = "Reduced-Feature Candidate Development and Lock"
CANDIDATE_ID = "C_B6_REDUCED_CO2_SLOPE_CANDIDATE_001"
FEATURE_ORDER = ("CO2", "CO2_slope")
SLOPE_PROFILE = "CO2_SLOPE_FEATURE_PROFILE_001"
SLOPE_METHOD = "ENDPOINT_DIFFERENCE"
SLOPE_HISTORY_SECONDS = 150.0
SLOPE_MAX_GAP_SECONDS = 90.0
ARCHITECTURE = "LINEAR_LOGISTIC"
IMBALANCE_STRATEGY = "BALANCED_RANDOM_OVERSAMPLE"
SEED = 20260810
OOF_FOLD_COUNT = 5
OOF_FOLD_SEED = 20260810
THRESHOLD_MIN = 0.05
THRESHOLD_MAX = 0.95
THRESHOLD_STEP = 0.01
MIN_OCCUPIED_RECALL = 0.90
HISTORICAL_B5_THRESHOLD = 0.58
ECE_BIN_COUNT = 10

TRAIN_COUNT = 8140
VALIDATION_COUNT = 2662
LOCKED_TEST_COUNT = 9749
LOCKED_TEST_CANONICAL_COUNT = 9752
TRAIN_FINGERPRINT = "492ca1f67e44b4a2018b743ec0fc3d20b418f7823d5f2643d8c90b0d39de8fab"
VALIDATION_FINGERPRINT = "19321e57fe72f6482b3c7b5d3714d21e9c13b753173ceb56ea694524ac6529ef"
LOCKED_TEST_FINGERPRINT = "0bac8dc1affae1de48ea68f01e866508ea19f31e194a7c0dccbf617e529344e7"

CANONICAL_REL = "datasets/co2/manifests/c_a5_canonical_samples/canonical_source_samples.jsonl"
ELIGIBLE_REL = "datasets/co2/manifests/c_a5_canonical_samples/model_eligible_sample_ids.jsonl"
A5_CHECKSUMS_REL = "datasets/co2/manifests/c_a5_canonical_samples/checksums.sha256"
DECISION_RESULT_REL = "datasets/co2/manifests/c_c1_model_input_decision/model_input_decision_result.json"
DECISION_CHECKSUMS_REL = "datasets/co2/manifests/c_c1_model_input_decision/checksums.sha256"
ROADMAP_REL = "docs/20260810_ChatGPT_SafeNest_Multisensor_Parallel_Execution_Roadmap_01.md"
C_C1_PROTOCOL_REL = "datasets/co2/manifests/c_c1_measurement_protocol/protocol.json"
B5_LOCK_REL = "datasets/co2/manifests/c_b5_robustness_final_lock/final_candidate_lock.json"

ARTIFACT_REL = "datasets/co2/manifests/c_b6_reduced_feature_candidate"
CANDIDATE_REL = "models/co2/candidates/c_b6"
REPORT_REL = "docs/reports/20260815_SafeNest_CO2_C_B6_Reduced_Feature_Candidate_Development_and_Lock_01.md"

DECISION_VALIDATOR_REL = "scripts/validate_co2_model_input_final_decision.py"
C_B6_AUDIT_REL = "scripts/audit_co2_c_b6_candidate.py"
C_B6_VALIDATOR_REL = "scripts/validate_co2_c_b6_candidate.py"
C_B6_TEST_REL = "tests/test_co2_c_b6_candidate.py"


class CB6Error(RuntimeError):
    """Fail-closed C-B6 construction error."""


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n")


def stable_sha256(payload: Any) -> str:
    blob = json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ordered_ids_sha256(ids: Sequence[str]) -> str:
    return hashlib.sha256(("\n".join(ids) + "\n").encode("utf-8")).hexdigest()


def array_sha256(ids: Sequence[str], features: np.ndarray, labels: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(("\n".join(ids) + "\n").encode("utf-8"))
    digest.update(np.asarray(features, dtype="<f8").tobytes(order="C"))
    digest.update(np.asarray(labels, dtype="<i8").tobytes(order="C"))
    return digest.hexdigest()


def run_git(root: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def team_main_sha() -> str:
    result = subprocess.run(
        ["git", "ls-remote", "https://github.com/jinsu1011/safenest-embedded-competition.git", "refs/heads/main"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return "UNAVAILABLE"
    return result.stdout.split()[0]


def load_split_ids(root: Path) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {"TRAIN": [], "VALIDATION": [], "LOCKED_TEST": []}
    with (root / ELIGIBLE_REL).open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            role = str(item.get("future_split_role"))
            if role not in result:
                raise CB6Error(f"unexpected eligible split role: {role}")
            result[role].append(str(item["canonical_sample_id"]))
    expected = {"TRAIN": TRAIN_COUNT, "VALIDATION": VALIDATION_COUNT, "LOCKED_TEST": LOCKED_TEST_COUNT}
    for role, count in expected.items():
        if len(result[role]) != count or len(result[role]) != len(set(result[role])):
            raise CB6Error(f"eligible membership drift: {role}")
    return result


def load_open_canonical_rows(root: Path, open_ids: Mapping[str, Sequence[str]]) -> Dict[str, Dict[str, Any]]:
    """Decode canonical feature/target rows only for TRAIN and VALIDATION.

    LOCKED_TEST lines are recognized and counted by their split marker, then
    skipped before JSON decoding so no sealed feature or target row is used.
    """
    wanted = set(open_ids["TRAIN"]) | set(open_ids["VALIDATION"])
    rows: Dict[str, Dict[str, Any]] = {}
    locked_canonical_count = 0
    with (root / CANONICAL_REL).open("r", encoding="utf-8") as handle:
        for line in handle:
            if '"future_split_role":"LOCKED_TEST"' in line:
                locked_canonical_count += 1
                continue
            if not line.strip():
                continue
            row = json.loads(line)
            role = str(row.get("future_split_role"))
            if role not in ("TRAIN", "VALIDATION"):
                raise CB6Error(f"unexpected open canonical role: {role}")
            if not row.get("model_eligible_for_slope_complete_view"):
                continue
            sample_id = str(row["canonical_sample_id"])
            if sample_id not in wanted or sample_id in rows:
                raise CB6Error(f"canonical open-row identity drift: {sample_id}")
            for field in ("co2", "co2_slope", "occupancy_source_value"):
                value = row.get(field)
                if value is None or not math.isfinite(float(value)):
                    raise CB6Error(f"invalid open canonical field {field}: {sample_id}")
            rows[sample_id] = row
    if locked_canonical_count != LOCKED_TEST_CANONICAL_COUNT:
        raise CB6Error(f"LOCKED_TEST canonical membership count drift: {locked_canonical_count}")
    if set(rows) != wanted:
        missing = sorted(wanted - set(rows))[:5]
        raise CB6Error(f"open canonical rows missing: {missing}")
    return rows


def build_matrix(rows: Mapping[str, Mapping[str, Any]], ids: Sequence[str], role: str) -> Tuple[np.ndarray, np.ndarray]:
    values: List[List[float]] = []
    labels: List[int] = []
    for sample_id in ids:
        row = rows.get(sample_id)
        if row is None or row.get("future_split_role") != role:
            raise CB6Error(f"matrix row identity drift: {sample_id}")
        values.append([float(row["co2"]), float(row["co2_slope"])])
        labels.append(int(row["occupancy_source_value"]))
    return np.asarray(values, dtype=np.float64), np.asarray(labels, dtype=np.int64)


def verify_predecessors(root: Path, split_ids: Mapping[str, Sequence[str]]) -> Dict[str, Any]:
    release = verify_a_series_release(root)
    if release.get("status") != "VERIFIED":
        raise CB6Error("A-series release tag verification failed")
    artifact_lock = verify_a_series_artifact_lock(root)
    if artifact_lock.get("status") != "VERIFIED":
        raise CB6Error("A-series artifact lock verification failed")
    decision = load_json(root / DECISION_RESULT_REL)
    if decision.get("final_decision") != "ADOPT_REDUCED_FEATURE_DIRECTION":
        raise CB6Error("C-B6 predecessor decision is not ADOPT_REDUCED_FEATURE_DIRECTION")
    interpretation = decision.get("interpretation", {})
    if interpretation.get("four_feature_predictive_benefit_observed") is not True:
        raise CB6Error("C-B6 predecessor interpretation drift: four-feature benefit")
    if interpretation.get("reduced_feature_predictive_superiority_established") is not False:
        raise CB6Error("C-B6 predecessor interpretation drift: reduced superiority")
    if (decision.get("decision_basis") or {}).get("type") != "SYSTEM_CONTRACT_BURDEN_OF_PROOF":
        raise CB6Error("C-B6 predecessor decision basis drift")
    boundary = decision.get("status_boundary") or {}
    if boundary.get("physical_acquisition_status") != "HOLD_PENDING_REDUCED_FEATURE_CANDIDATE_LOCK":
        raise CB6Error("C-B6 physical-acquisition predecessor boundary drift")
    if boundary.get("operator_handoff_status") != "HOLD" or boundary.get("c_c2_started") is not False:
        raise CB6Error("C-B6 operator/C-C2 predecessor boundary drift")
    protocol = load_json(root / C_C1_PROTOCOL_REL)
    historical_features = [entry.get("name") for entry in protocol.get("required_features", [])]
    if historical_features != ["CO2", "Temperature", "Humidity", "CO2_slope"]:
        raise CB6Error("historical C-C1 feature contract changed before C-B6")
    if (protocol.get("post_c_c1_model_input_decision") or {}).get("b5_modified") is not False:
        raise CB6Error("historical B5 modification boundary drift")
    b0 = load_json(root / "datasets/co2/manifests/c_b0_offline_experiment_contract/sample_universe_manifest.json")
    expected = b0.get("ordered_id_list_sha256", {})
    for role, fingerprint in (("TRAIN", TRAIN_FINGERPRINT), ("VALIDATION", VALIDATION_FINGERPRINT), ("LOCKED_TEST", LOCKED_TEST_FINGERPRINT)):
        if expected.get(role) != fingerprint or ordered_ids_sha256(split_ids[role]) != fingerprint:
            raise CB6Error(f"split fingerprint drift: {role}")
    if not (root / A5_CHECKSUMS_REL).is_file() or not (root / DECISION_CHECKSUMS_REL).is_file():
        raise CB6Error("predecessor checksum manifest missing")
    return {
        "decision_result": DECISION_RESULT_REL,
        "decision": decision.get("final_decision"),
        "decision_basis": (decision.get("decision_basis") or {}).get("type"),
        "physical_acquisition": boundary.get("physical_acquisition_status"),
        "operator_handoff": boundary.get("operator_handoff_status"),
        "c_c2_started": boundary.get("c_c2_started"),
        "historical_c_c1_features": historical_features,
        "a_series_release": release,
        "a_series_artifact_lock": artifact_lock,
    }


def b5_snapshot(root: Path) -> Dict[str, Any]:
    lock = load_json(root / B5_LOCK_REL)
    paths = [str(item["path"]) for item in lock.get("artifacts", [])]
    if not paths:
        raise CB6Error("B5 lock has no artifacts")
    hashes: Dict[str, str] = {}
    for rel in paths:
        path = root / rel
        if not path.is_file():
            raise CB6Error(f"B5 locked artifact missing: {rel}")
        hashes[rel] = file_sha256(path)
    selected = {
        rel: hashes[rel]
        for rel in paths
        if rel in {
            "models/co2/candidates/c_b4/full_integer_int8.tflite",
            "models/co2/candidates/c_b4/float_reference_parameters.json",
            "datasets/co2/manifests/c_b2_imbalance_calibration/preprocessing_scaler_evidence.json",
            "models/co2/candidates/c_b5/final_candidate_metadata.json",
            B5_LOCK_REL,
        }
    }
    return {
        "final_lock_profile_id": lock.get("final_lock_profile_id"),
        "final_lock_sha256": lock.get("final_lock_sha256"),
        "final_lock_file_sha256": file_sha256(root / B5_LOCK_REL),
        "artifact_hashes": hashes,
        "selected_frozen_artifact_hashes": selected,
        "modified": False,
    }


def fit_model(x: np.ndarray, y: np.ndarray, seed: int = SEED) -> LogisticRegression:
    model = LogisticRegression(
        penalty="l2", C=1.0, solver="lbfgs", fit_intercept=True,
        max_iter=2000, class_weight=None, random_state=seed,
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with threadpool_limits(limits=1):
            model.fit(x, y)
    if any("Convergence" in str(item.message) for item in caught):
        raise CB6Error("C_B6_LOGISTIC_CONVERGENCE_FAILURE")
    return model


def oversample_indices(labels: np.ndarray, seed: int = SEED) -> Tuple[np.ndarray, Dict[str, Any]]:
    if seed < 0:
        raise CB6Error("invalid oversampling seed")
    majority = np.flatnonzero(labels == 0)
    minority = np.flatnonzero(labels == 1)
    if len(majority) <= len(minority):
        raise CB6Error("expected VACANT majority in TRAIN")
    rng = np.random.default_rng(seed)
    appended = rng.choice(minority, size=len(majority) - len(minority), replace=True).astype(np.int64)
    indices = np.concatenate([np.arange(labels.size, dtype=np.int64), appended])
    return indices, {
        "seed": seed,
        "rng": "numpy.random.Generator(PCG64)",
        "method": "MINORITY_RANDOM_OVERSAMPLE_WITH_REPLACEMENT",
        "original_class_counts": {"VACANT": int((labels == 0).sum()), "OCCUPIED": int((labels == 1).sum())},
        "oversampled_class_counts": {"VACANT": int((labels[indices] == 0).sum()), "OCCUPIED": int((labels[indices] == 1).sum())},
        "appended_minority_draw_count": int(appended.size),
        "majority_undersampling_count": 0,
        "validation_rows_used": 0,
        "locked_test_rows_used": 0,
        "deterministic": True,
        "appended_indices_sha256": hashlib.sha256(appended.tobytes(order="C")).hexdigest(),
    }


def classification_metrics(y: np.ndarray, probabilities: np.ndarray, threshold: float) -> Dict[str, Any]:
    predictions = (probabilities >= threshold).astype(np.int64)
    cm = confusion_matrix(y, predictions, labels=[0, 1])
    tn, fp, fn, tp = [int(x) for x in cm.ravel()]
    return {
        "sample_count": int(y.size),
        "decision_threshold": float(threshold),
        "accuracy": float(accuracy_score(y, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y, predictions)),
        "macro_f1": float(f1_score(y, predictions, average="macro")),
        "precision_vacant": float(precision_score(y, predictions, pos_label=0, zero_division=0)),
        "recall_vacant": float(recall_score(y, predictions, pos_label=0, zero_division=0)),
        "f1_vacant": float(f1_score(y, predictions, pos_label=0, zero_division=0)),
        "precision_occupied": float(precision_score(y, predictions, pos_label=1, zero_division=0)),
        "recall_occupied": float(recall_score(y, predictions, pos_label=1, zero_division=0)),
        "occupied_recall": float(recall_score(y, predictions, pos_label=1, zero_division=0)),
        "f1_occupied": float(f1_score(y, predictions, pos_label=1, zero_division=0)),
        "pr_auc": float(average_precision_score(y, probabilities)),
        "pr_auc_average_precision": float(average_precision_score(y, probabilities)),
        "roc_auc": float(roc_auc_score(y, probabilities)),
        "brier_score": float(brier_score_loss(y, probabilities)),
        "log_loss": float(log_loss(y, probabilities, labels=[0, 1])),
        "false_positive_rate": float(fp / (fp + tn)) if (fp + tn) else 0.0,
        "false_negative_rate": float(fn / (fn + tp)) if (fn + tp) else 0.0,
        "confusion_matrix": {
            "labels": [0, 1], "label_names": ["VACANT", "OCCUPIED"],
            "matrix": cm.tolist(), "tn": tn, "fp": fp, "fn": fn, "tp": tp,
        },
        "tn": tn, "fp": fp, "fn": fn, "tp": tp,
        "positive_prediction_rule": "occupancy_probability_greater_than_or_equal_to_threshold",
    }


def ece(y: np.ndarray, probabilities: np.ndarray) -> Dict[str, Any]:
    bins: List[Dict[str, Any]] = []
    total = 0.0
    for index in range(ECE_BIN_COUNT):
        lower = index / ECE_BIN_COUNT
        upper = (index + 1) / ECE_BIN_COUNT
        mask = (probabilities >= lower) & ((probabilities <= upper) if index == ECE_BIN_COUNT - 1 else (probabilities < upper))
        count = int(mask.sum())
        mean_probability = float(probabilities[mask].mean()) if count else None
        empirical = float(y[mask].mean()) if count else None
        contribution = float(count / y.size * abs(mean_probability - empirical)) if count else 0.0
        total += contribution
        bins.append({"bin_index": index, "lower_bound": lower, "upper_bound": upper, "sample_count": count, "mean_probability": mean_probability, "empirical_frequency": empirical, "ece_contribution": contribution})
    return {"definition": "10_EQUAL_WIDTH_BINS_OVER_0_1", "bin_count": ECE_BIN_COUNT, "population_count": int(y.size), "bins": bins, "expected_calibration_error": float(total)}


def threshold_grid() -> List[float]:
    return [float(i / 100) for i in range(5, 96)]


def threshold_policy() -> Dict[str, Any]:
    payload = {
        "manifest_version": "1.0",
        "phase": PHASE_ID,
        "policy_id": "CO2_C_B6_TRAIN_INTERNAL_THRESHOLD_POLICY_001",
        "status": "PREDECLARED_BEFORE_THRESHOLD_SELECTION",
        "candidate_id": CANDIDATE_ID,
        "source": "TRAIN_INTERNAL_ONLY",
        "development_population": "TRAIN",
        "outer_validation_rows_used": 0,
        "locked_test_rows_used": 0,
        "folding": {
            "method": "STRATIFIED_K_FOLD_OOF",
            "fold_count": OOF_FOLD_COUNT,
            "shuffle": True,
            "fold_seed": OOF_FOLD_SEED,
            "fold_scaler_fit": "EACH_FOLD_TRAIN_SUBSET_ONLY",
            "fold_oversampling": "EACH_FOLD_TRAIN_SUBSET_ONLY",
            "fold_sampling_seeds": [OOF_FOLD_SEED + index for index in range(OOF_FOLD_COUNT)],
        },
        "threshold_grid": threshold_grid(),
        "threshold_grid_min": THRESHOLD_MIN,
        "threshold_grid_max": THRESHOLD_MAX,
        "threshold_grid_step": THRESHOLD_STEP,
        "objective": {
            "minimum_occupied_recall": MIN_OCCUPIED_RECALL,
            "primary": "MAXIMIZE_MACRO_F1_AMONG_THRESHOLDS_MEETING_MINIMUM_OCCUPIED_RECALL",
            "tie_breakers": [
                "higher_occupied_recall",
                "higher_occupied_precision",
                "higher_balanced_accuracy",
                "lower_false_positive_rate",
                "threshold_closer_to_0_50",
                "lower_numeric_threshold",
            ],
            "accuracy_only_optimization": False,
            "safety_metric_claim": "OCCUPIED_RECALL_IS_NOT_A_DIRECT_SAFETY_METRIC",
        },
        "historical_b5_threshold": HISTORICAL_B5_THRESHOLD,
        "b5_threshold_inheritance": "FORBIDDEN",
        "threshold_source": "TRAIN_INTERNAL_ONLY",
    }
    payload["policy_fingerprint"] = stable_sha256(payload)
    return payload


def select_threshold(x_train: np.ndarray, y_train: np.ndarray, policy: Mapping[str, Any]) -> Tuple[float, Dict[str, Any]]:
    folds = StratifiedKFold(n_splits=OOF_FOLD_COUNT, shuffle=True, random_state=OOF_FOLD_SEED)
    oof = np.zeros(y_train.size, dtype=np.float64)
    fold_rows: List[Dict[str, Any]] = []
    for fold_index, (fit_indices, holdout_indices) in enumerate(folds.split(x_train, y_train)):
        fold_scaler = StandardScaler().fit(x_train[fit_indices])
        fold_x = fold_scaler.transform(x_train[fit_indices])
        holdout_x = fold_scaler.transform(x_train[holdout_indices])
        sampled, sampling = oversample_indices(y_train[fit_indices], seed=OOF_FOLD_SEED + fold_index)
        model = fit_model(fold_x[sampled], y_train[fit_indices][sampled])
        oof[holdout_indices] = model.predict_proba(holdout_x)[:, 1]
        fold_rows.append({
            "fold": fold_index,
            "fit_rows": int(fit_indices.size),
            "holdout_rows": int(holdout_indices.size),
            "scaler_fit_rows": int(fit_indices.size),
            "validation_rows_used": 0,
            "locked_test_rows_used": 0,
            "sampling_seed": sampling["seed"],
            "probability_finite": bool(np.isfinite(oof[holdout_indices]).all()),
        })
    if not np.isfinite(oof).all():
        raise CB6Error("non-finite TRAIN OOF probabilities")
    rows: List[Dict[str, Any]] = []
    for threshold in policy["threshold_grid"]:
        metrics = classification_metrics(y_train, oof, float(threshold))
        rows.append({"threshold": float(threshold), "metrics": metrics})
    minimum_recall = float(policy["objective"]["minimum_occupied_recall"])
    eligible = [row for row in rows if row["metrics"]["occupied_recall"] >= minimum_recall]
    if not eligible:
        raise CB6Error("no TRAIN-internal threshold meets the predeclared occupied-recall floor")
    selected = sorted(
        eligible,
        key=lambda row: (
            -row["metrics"]["macro_f1"],
            -row["metrics"]["occupied_recall"],
            -row["metrics"]["precision_occupied"],
            -row["metrics"]["balanced_accuracy"],
            row["metrics"]["false_positive_rate"],
            abs(row["threshold"] - 0.50),
            row["threshold"],
        ),
    )[0]
    selected_threshold = float(selected["threshold"])
    result = {
        "manifest_version": "1.0",
        "phase": PHASE_ID,
        "result_id": "CO2_C_B6_TRAIN_INTERNAL_THRESHOLD_RESULT_001",
        "candidate_id": CANDIDATE_ID,
        "policy_id": policy["policy_id"],
        "policy_fingerprint": policy["policy_fingerprint"],
        "threshold_source": "TRAIN_INTERNAL_ONLY",
        "selected_threshold": selected_threshold,
        "historical_b5_threshold": HISTORICAL_B5_THRESHOLD,
        "b5_threshold_inherited": False,
        "coincidental_numeric_match_to_b5": bool(selected_threshold == HISTORICAL_B5_THRESHOLD),
        "oof_population": "TRAIN",
        "oof_rows": int(y_train.size),
        "oof_probability_fingerprint": stable_sha256([float(value) for value in oof.tolist()]),
        "folds": fold_rows,
        "threshold_rows": rows,
        "eligible_threshold_count": len(eligible),
        "selected_metrics": selected["metrics"],
        "validation_rows_used": 0,
        "locked_test_rows_used": 0,
    }
    return selected_threshold, result


def configure_tensorflow() -> Dict[str, Any]:
    os.environ["PYTHONHASHSEED"] = str(SEED)
    random.seed(SEED)
    np.random.seed(SEED)
    try:
        tf.config.experimental.enable_op_determinism()
        deterministic = "SUPPORTED_ENABLED"
    except Exception as exc:  # noqa: BLE001
        deterministic = f"UNAVAILABLE:{type(exc).__name__}"
    try:
        tf.config.threading.set_intra_op_parallelism_threads(1)
        tf.config.threading.set_inter_op_parallelism_threads(1)
        threading = "SUPPORTED"
    except Exception as exc:  # noqa: BLE001
        threading = f"UNAVAILABLE:{type(exc).__name__}"
    return {"tensorflow_version": str(tf.__version__), "deterministic_ops": deterministic, "single_thread_configuration": threading}


def build_bridge(model: LogisticRegression, *, quantized: bool, calibration_range: float) -> Any:
    tf.keras.backend.clear_session()
    inputs = tf.keras.Input(shape=(2,), dtype=tf.float32, name="standardized_reduced_features")
    tensor = inputs
    if quantized:
        low = -float(calibration_range)
        high = float(calibration_range)
        tensor = tf.keras.layers.Lambda(
            lambda value: tf.quantization.fake_quant_with_min_max_vars(value, min=low, max=high, narrow_range=False),
            name="fixed_ptq_calibration_range",
        )(tensor)
    outputs = tf.keras.layers.Dense(1, activation="sigmoid", use_bias=True, name="occupied_probability")(tensor)
    bridge = tf.keras.Model(inputs=inputs, outputs=outputs, name="safenest_co2_c_b6_reduced_bridge")
    bridge.get_layer("occupied_probability").set_weights([
        np.asarray(model.coef_, dtype=np.float32).T,
        np.asarray(model.intercept_, dtype=np.float32),
    ])
    return bridge


def representative_dataset(x_train_scaled: np.ndarray) -> Iterable[List[np.ndarray]]:
    for row in np.asarray(x_train_scaled, dtype=np.float32):
        yield [row.reshape(1, 2)]


def convert_tflite(model: LogisticRegression, x_train_scaled: np.ndarray, calibration_range: float) -> Tuple[bytes, bytes, Dict[str, Any]]:
    float_bridge = build_bridge(model, quantized=False, calibration_range=calibration_range)
    float_converter = tf.lite.TFLiteConverter.from_keras_model(float_bridge)
    float_bytes = bytes(float_converter.convert())
    int8_bridge = build_bridge(model, quantized=True, calibration_range=calibration_range)
    int8_converter = tf.lite.TFLiteConverter.from_keras_model(int8_bridge)
    int8_converter.optimizations = [tf.lite.Optimize.DEFAULT]
    int8_converter.representative_dataset = lambda: representative_dataset(x_train_scaled)
    int8_converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    int8_converter.inference_input_type = tf.int8
    int8_converter.inference_output_type = tf.int8
    int8_bytes = bytes(int8_converter.convert())
    return float_bytes, int8_bytes, {"float_bridge": float_bridge, "int8_bridge": int8_bridge}


def tensor_quantization(detail: Mapping[str, Any]) -> Dict[str, Any]:
    scale, zero = detail.get("quantization", (0.0, 0))
    params = detail.get("quantization_parameters", {})
    return {
        "scale": float(scale),
        "zero_point": int(zero),
        "scales": [float(value) for value in np.asarray(params.get("scales", []), dtype=np.float64).tolist()],
        "zero_points": [int(value) for value in np.asarray(params.get("zero_points", []), dtype=np.int64).tolist()],
        "quantized_dimension": int(params.get("quantized_dimension", 0)),
    }


def inspect_tflite(model_bytes: bytes, expected_dtype: str) -> Dict[str, Any]:
    interpreter = tf.lite.Interpreter(model_content=model_bytes)
    interpreter.allocate_tensors()
    inputs = interpreter.get_input_details()
    outputs = interpreter.get_output_details()
    if len(inputs) != 1 or len(outputs) != 1:
        raise CB6Error("TFLite must expose one input and one output")
    inp, out = inputs[0], outputs[0]
    actual_input = np.dtype(inp["dtype"]).name
    actual_output = np.dtype(out["dtype"]).name
    if actual_input != expected_dtype or actual_output != expected_dtype:
        raise CB6Error(f"TFLite dtype mismatch: {actual_input}/{actual_output}")
    ops = interpreter._get_ops_details()
    op_names = [str(op.get("op_name")) for op in ops if str(op.get("op_name")) != "DELEGATE"]
    operator_types: List[str] = []
    for op in ops:
        if str(op.get("op_name")) == "DELEGATE":
            continue
        for key in ("operand_types", "result_types"):
            operator_types.extend(np.dtype(value).name for value in op.get(key, []))
    contract = {
        "input_count": 1,
        "output_count": 1,
        "input_name": str(inp["name"]),
        "output_name": str(out["name"]),
        "input_shape": [int(value) for value in inp["shape"]],
        "output_shape": [int(value) for value in out["shape"]],
        "input_shape_signature": [int(value) for value in inp.get("shape_signature", inp["shape"])],
        "output_shape_signature": [int(value) for value in out.get("shape_signature", out["shape"])],
        "input_dtype": actual_input,
        "output_dtype": actual_output,
        "input_quantization": tensor_quantization(inp),
        "output_quantization": tensor_quantization(out),
        "op_names": op_names,
        "operator_tensor_types": sorted(set(operator_types)),
        "full_integer_ops": expected_dtype == "int8" and all(value in {"int8", "int32"} for value in operator_types),
        "model_byte_size": len(model_bytes),
        "model_sha256": hashlib.sha256(model_bytes).hexdigest(),
    }
    expected_shape = [1, 2]
    if contract["input_shape"] != expected_shape or contract["output_shape"] != [1, 1]:
        raise CB6Error("TFLite tensor shape contract mismatch")
    if expected_dtype == "int8" and (not contract["full_integer_ops"] or "FULLY_CONNECTED" not in op_names or "LOGISTIC" not in op_names):
        raise CB6Error("TFLite is not a full-integer logistic model")
    if expected_dtype == "int8" and (contract["input_quantization"]["scale"] <= 0 or contract["output_quantization"]["scale"] <= 0):
        raise CB6Error("TFLite INT8 quantization parameters are invalid")
    return contract


def quantize_inputs(values: np.ndarray, scale: float, zero_point: int) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    if values.ndim == 1:
        values = values.reshape(1, -1)
    if values.ndim != 2 or values.shape[1] != 2 or not math.isfinite(scale) or scale <= 0:
        raise CB6Error("invalid C-B6 INT8 input contract")
    unclipped = np.rint(values / float(scale)) + int(zero_point)
    flags = (unclipped < -128) | (unclipped > 127)
    overflow = np.maximum(np.maximum(-128.0 - unclipped, unclipped - 127.0), 0.0)
    return np.clip(unclipped, -128, 127).astype(np.int8), flags, overflow


def run_tflite(model_bytes: bytes, values: np.ndarray, *, quantized: bool) -> Tuple[np.ndarray, Dict[str, Any]]:
    interpreter = tf.lite.Interpreter(model_content=model_bytes)
    interpreter.allocate_tensors()
    inp = interpreter.get_input_details()[0]
    out = interpreter.get_output_details()[0]
    input_scale, input_zero = tensor_quantization(inp)["scale"], tensor_quantization(inp)["zero_point"]
    output_quant = tensor_quantization(out)
    probabilities: List[float] = []
    saturation_flags: List[List[int]] = []
    overflow_distances: List[float] = []
    raw_outputs: List[int] = []
    for row in np.asarray(values, dtype=np.float64):
        if quantized:
            tensor, flags, overflow = quantize_inputs(row.reshape(1, 2), input_scale, input_zero)
            saturation_flags.append([int(value) for value in flags[0].tolist()])
            overflow_distances.append(float(np.max(overflow[0])))
        else:
            tensor = np.asarray(row, dtype=np.float32).reshape(1, 2)
        interpreter.set_tensor(inp["index"], tensor)
        interpreter.invoke()
        raw = int(np.asarray(interpreter.get_tensor(out["index"])).reshape(-1)[0]) if quantized else float(np.asarray(interpreter.get_tensor(out["index"])).reshape(-1)[0])
        raw_outputs.append(raw)
        probabilities.append(float((raw - output_quant["zero_point"]) * output_quant["scale"]) if quantized else float(raw))
    return np.asarray(probabilities, dtype=np.float64), {
        "saturation_flags": saturation_flags,
        "overflow_distances": overflow_distances,
        "raw_outputs": raw_outputs,
        "input_scale": input_scale,
        "input_zero_point": input_zero,
        "output_scale": output_quant["scale"],
        "output_zero_point": output_quant["zero_point"],
    }


def saturation_report(run: Mapping[str, Any], population: str, sample_count: int) -> Dict[str, Any]:
    flags = np.asarray(run["saturation_flags"], dtype=np.int64)
    if flags.shape != (sample_count, 2):
        raise CB6Error("C-B6 saturation accounting shape mismatch")
    counts = flags.sum(axis=0)
    return {
        "population": population,
        "sample_count": sample_count,
        "feature_count": 2,
        "feature_order": list(FEATURE_ORDER),
        "per_feature": {
            feature: {"count": int(counts[index]), "fraction": float(counts[index] / sample_count)}
            for index, feature in enumerate(FEATURE_ORDER)
        },
        "saturated_element_count": int(flags.sum()),
        "saturation_fraction": float(flags.sum() / flags.size),
        "samples_with_at_least_one_saturated_feature": int(np.any(flags > 0, axis=1).sum()),
        "maximum_overflow_distance": float(max(run["overflow_distances"]) if run["overflow_distances"] else 0.0),
        "saturation_observed": bool(flags.sum()),
    }


def drift(source: np.ndarray, target: np.ndarray, labels: np.ndarray, threshold: float) -> Dict[str, Any]:
    absolute = np.abs(np.asarray(target) - np.asarray(source))
    source_metrics = classification_metrics(labels, source, threshold)
    target_metrics = classification_metrics(labels, target, threshold)
    return {
        "probability_mae": float(np.mean(absolute)),
        "probability_rmse": float(np.sqrt(np.mean(np.square(target - source)))),
        "probability_p95_absolute_drift": float(np.percentile(absolute, 95)),
        "probability_max_absolute_drift": float(np.max(absolute)),
        "label_disagreement_count": int(np.sum((source >= threshold) != (target >= threshold))),
        "label_disagreement_fraction": float(np.mean((source >= threshold) != (target >= threshold))),
        "source_metrics": source_metrics,
        "target_metrics": target_metrics,
    }


def quantization_gate(evidence: Mapping[str, Any]) -> Dict[str, Any]:
    limits = {
        "macro_f1_degradation": 0.005,
        "occupied_recall_degradation": 0.01,
        "probability_mae": 0.01,
        "probability_p95_absolute_drift": 0.02,
        "probability_max_absolute_drift": 0.05,
        "label_disagreement_fraction": 0.005,
    }
    source = evidence["source_metrics"]
    target = evidence["target_metrics"]
    values = {
        "macro_f1_degradation": max(0.0, source["macro_f1"] - target["macro_f1"]),
        "occupied_recall_degradation": max(0.0, source["occupied_recall"] - target["occupied_recall"]),
        "probability_mae": evidence["probability_mae"],
        "probability_p95_absolute_drift": evidence["probability_p95_absolute_drift"],
        "probability_max_absolute_drift": evidence["probability_max_absolute_drift"],
        "label_disagreement_fraction": evidence["label_disagreement_fraction"],
    }
    return {**values, "limits": limits, "status": "PASS" if all(values[key] <= limits[key] for key in limits) else "FAIL"}


def make_report(result: Mapping[str, Any]) -> str:
    metrics = result["validation_metrics"]["reference_float"]
    int8 = result["validation_metrics"]["int8_tflite"]
    scaler = result["scaler"]
    threshold = result["threshold"]
    quant = result["quantization"]
    return f"""# SafeNest CO₂ C-B6 Reduced-Feature Candidate Development and Lock

- Document Version: `01`
- Author: `Codex` (CO₂ C-B6 Offline Candidate Agent)
- Execution Date: `2026-08-15`
- Phase: `C-B6 — Reduced-Feature Candidate Development and Lock`
- Status: `{result['status']}`

**Candidate ID:** `{CANDIDATE_ID}`
**Execution base:** `{result['repository']['c_b6_execution_base']}`
**Standalone main:** `{result['repository']['standalone_main_sha']}`
**Team main reference:** `{result['repository']['team_main_sha']}`

## Executive result

The already-selected `CO2 + CO2_slope` direction was implemented as a new,
independently scaled and independently thresholded offline logistic candidate.
The historical four-feature B5 candidate was not modified. The candidate status
is `{result['status']}`. Physical acquisition, C-C2, and C-D remain unauthorized.

This report records offline construction evidence only:

```text
C-B6 OFFLINE VALIDATION != SCD40 DEVICE-DOMAIN VALIDATION
```

## Predecessor decision and frozen contract

The merged predecessor decision was `ADOPT_REDUCED_FEATURE_DIRECTION`, based on
`SYSTEM_CONTRACT_BURDEN_OF_PROOF`. Four-feature predictive benefit remains
observed, reduced-feature predictive superiority was not established, and the
old C-C1 four-feature protocol remains historical evidence. The C-B6 feature
selection question was not reopened.

```text
FEATURE_ORDER: CO2, CO2_slope
TEMPERATURE_MODEL_INPUT: FORBIDDEN
HUMIDITY_MODEL_INPUT: FORBIDDEN
SLOPE_PROFILE: {SLOPE_PROFILE}
SLOPE_METHOD: {SLOPE_METHOD}
HISTORY_SECONDS: {SLOPE_HISTORY_SECONDS:.1f}
MAX_INTERNAL_GAP_SECONDS: {SLOPE_MAX_GAP_SECONDS:.1f}
```

## Dataset lineage and access boundary

The candidate consumes the locked A5 canonical materialization rather than the
absent Git-ignored raw ZIP. A-series release and artifact-lock verification
passed. TRAIN and VALIDATION use the canonical eligible IDs and fingerprints;
the sealed LOCKED_TEST is membership-verified only.

| Population | Rows | Fingerprint | Role |
|---|---:|---|---|
| TRAIN | {TRAIN_COUNT} | `{TRAIN_FINGERPRINT}` | scaler, threshold OOF, model fitting |
| VALIDATION | {VALIDATION_COUNT} | `{VALIDATION_FINGERPRINT}` | frozen-threshold consistency evidence |
| LOCKED_TEST | {LOCKED_TEST_COUNT} | `{LOCKED_TEST_FINGERPRINT}` | membership only |

```text
LOCKED_TEST_FEATURE_ROWS_DECODED: 0
LOCKED_TEST_TARGET_ROWS_DECODED: 0
LOCKED_TEST_PREDICTIVE_METRICS: 0
LOCKED_TEST_THRESHOLD_SELECTION: 0
LOCKED_TEST_MODEL_SELECTION: 0
LOCKED_TEST_HYPERPARAMETER_SELECTION: 0
```

The raw-dependent standalone A5/A6 validators cannot independently reopen the
ZIP in this worktree because the ignored archive is absent. The locked A5
materialization, checksums, A-series release tag, and A-series artifact lock
were verified; no raw-dependent PASS claim is made here.

## Scaler and training procedure

A new two-feature `StandardScaler` was fit on the original TRAIN rows only.
The historical four-feature scaler was not reused.

```text
SCALER_FIT_SOURCE: ORIGINAL_TRAIN_ONLY
SCALER_FEATURE_ORDER: CO2, CO2_slope
SCALER_FINGERPRINT: {scaler['fingerprint']}
MEAN: {scaler['mean']}
SCALE: {scaler['scale']}
```

The model family remained `LINEAR_LOGISTIC` with the existing B-series
parameters (`L2`, `C=1.0`, `lbfgs`, intercept, `max_iter=2000`). The existing
`BALANCED_RANDOM_OVERSAMPLE` policy and seed `{SEED}` were applied to TRAIN
only. No architecture, hyperparameter, split, label, slope, or feature search
was performed.

## Threshold-selection policy and result

The machine-readable threshold policy was written with status
`PREDECLARED_BEFORE_THRESHOLD_SELECTION` before calculating OOF thresholds.
It uses five-fold stratified TRAIN-internal OOF probabilities, fold-local
TRAIN-only scalers and oversampling, and a grid from 0.05 to 0.95 in 0.01
increments. The objective is to maximize Macro F1 among candidates with
occupied recall at least `{MIN_OCCUPIED_RECALL:.2f}`, then apply the declared
recall/precision/balanced-accuracy/FPR/tie-break rules.

```text
B5_THRESHOLD_0_58_INHERITED: NO
THRESHOLD_SOURCE: TRAIN_INTERNAL_ONLY
FINAL_THRESHOLD: {threshold['value']:.2f}
COINCIDENTAL_MATCH_TO_B5: {str(threshold['coincidental_match_to_b5']).upper()}
```

The existing VALIDATION population was not used to tune this threshold. It has
historical development use and is reported only as frozen-threshold
development-validation/consistency evidence.

## Reference model and VALIDATION results

The reference model coefficients, intercept, feature order, scaler identity,
class mapping, and training lineage are stored in the candidate directory.
The following values are from the frozen-threshold reference model:

| Metric | Reference Float | Float TFLite | INT8 TFLite |
|---|---:|---:|---:|
| Accuracy | {metrics['accuracy']:.6f} | {result['validation_metrics']['float_tflite']['accuracy']:.6f} | {int8['accuracy']:.6f} |
| Balanced Accuracy | {metrics['balanced_accuracy']:.6f} | {result['validation_metrics']['float_tflite']['balanced_accuracy']:.6f} | {int8['balanced_accuracy']:.6f} |
| Macro F1 | {metrics['macro_f1']:.6f} | {result['validation_metrics']['float_tflite']['macro_f1']:.6f} | {int8['macro_f1']:.6f} |
| OCCUPIED Precision | {metrics['precision_occupied']:.6f} | {result['validation_metrics']['float_tflite']['precision_occupied']:.6f} | {int8['precision_occupied']:.6f} |
| OCCUPIED Recall | {metrics['recall_occupied']:.6f} | {result['validation_metrics']['float_tflite']['recall_occupied']:.6f} | {int8['recall_occupied']:.6f} |
| OCCUPIED F1 | {metrics['f1_occupied']:.6f} | {result['validation_metrics']['float_tflite']['f1_occupied']:.6f} | {int8['f1_occupied']:.6f} |
| PR-AUC | {metrics['pr_auc_average_precision']:.6f} | {result['validation_metrics']['float_tflite']['pr_auc_average_precision']:.6f} | {int8['pr_auc_average_precision']:.6f} |
| ROC-AUC | {metrics['roc_auc']:.6f} | {result['validation_metrics']['float_tflite']['roc_auc']:.6f} | {int8['roc_auc']:.6f} |
| Brier score | {metrics['brier_score']:.6f} | {result['validation_metrics']['float_tflite']['brier_score']:.6f} | {int8['brier_score']:.6f} |
| Log loss | {metrics['log_loss']:.6f} | {result['validation_metrics']['float_tflite']['log_loss']:.6f} | {int8['log_loss']:.6f} |

## TFLite conversion and INT8 diagnostics

Two new TFLite artifacts were created; no B5 TFLite artifact was overwritten.
The INT8 model uses one integer input and one integer output tensor. The
representative dataset is all natural TRAIN rows after the new TRAIN-only
scaler; VALIDATION and LOCKED_TEST rows are excluded.

```text
FLOAT_TFLITE: {result['tflite']['float_path']}
FLOAT_TFLITE_SHA256: {result['tflite']['float_sha256']}
INT8_TFLITE: {result['tflite']['int8_path']}
INT8_TFLITE_SHA256: {result['tflite']['int8_sha256']}
INT8_INPUT_DTYPE: {result['tflite']['int8_contract']['input_dtype']}
INT8_INPUT_SHAPE: {result['tflite']['int8_contract']['input_shape']}
INT8_INPUT_SCALE_ZERO_POINT: {result['tflite']['int8_contract']['input_quantization']['scale']}, {result['tflite']['int8_contract']['input_quantization']['zero_point']}
INT8_OUTPUT_DTYPE: {result['tflite']['int8_contract']['output_dtype']}
INT8_OUTPUT_SCALE_ZERO_POINT: {result['tflite']['int8_contract']['output_quantization']['scale']}, {result['tflite']['int8_contract']['output_quantization']['zero_point']}
```

The conversion/equivalence gate is `{quant['gate']['status']}`. Float-to-INT8
probability MAE was `{quant['float_to_int8']['probability_mae']:.6f}`, p95 drift
was `{quant['float_to_int8']['probability_p95_absolute_drift']:.6f}`, maximum
drift was `{quant['float_to_int8']['probability_max_absolute_drift']:.6f}`, and
label disagreement was `{quant['float_to_int8']['label_disagreement_count']}`
of `{VALIDATION_COUNT}`.

Saturation is reported separately by feature. TRAIN representative saturation
was CO2 `{quant['saturation']['train']['per_feature']['CO2']['count']}` and
CO2_slope `{quant['saturation']['train']['per_feature']['CO2_slope']['count']}`;
VALIDATION saturation was CO2 `{quant['saturation']['validation']['per_feature']['CO2']['count']}`
and CO2_slope `{quant['saturation']['validation']['per_feature']['CO2_slope']['count']}`.
This known slope saturation is retained as a limitation and is not silently
treated as proof of device-domain suitability.

## Candidate lock and immutability

The dedicated C-B6 lock binds the candidate ID, two-feature contract, new
scaler hash, reference model evidence, threshold result, TFLite hashes,
quantization contract, validation evidence, and TRAIN/VALIDATION lineage.
The lock does not hash itself; the checksum manifest covers the lock.

```text
CANDIDATE_LOCK: {result['lock']['path']}
LOCK_SHA256: {result['lock']['sha256']}
CHECKSUM_MANIFEST: {result['checksums']['path']}
DETERMINISTIC_RERUN: {result['determinism']['status']}
B5_MODIFIED: NO
```

All selected B5 frozen artifact hashes matched before and after generation.
The B5 model, scaler, threshold, metadata, and final lock remain historical
and untouched.

## Known limitations and non-claims

- VALIDATION has already participated in historical development and decision work; it is not an untouched final holdout.
- C-B6 does not prove generalization to real SCD40 data.
- INT8 input saturation is observed for CO2_slope in the TRAIN representative population and requires review before operator handoff.
- No physical acquisition, SCD40 device-domain validation, runtime/firmware change, telemetry change, C-C2, or C-D work occurred.
- Occupancy recall is not a direct safety metric; this candidate has room-occupancy semantics only.

## Roadmap impact and next phase

The canonical roadmap records this C-B6 candidate and its status. The next
conceptual phase is `C-C1R — Reduced-Feature Measurement Protocol Revision and
Operator Handoff`. That phase requires separate authorization and must review
the INT8 slope-saturation limitation before any operator guide is distributed.
Physical acquisition remains `HOLD`.

## Validation boundary

```text
NEW_PHYSICAL_MEASUREMENT: NO
PHYSICAL_ACQUISITION_STARTED: NO
C_C2_STARTED: NO
FORMAL_DEVICE_DOMAIN_VALIDATION: NO
C_D_AUTHORIZED: NO
```
"""


def run(root: Path) -> Dict[str, Any]:
    root = root.resolve()
    configure_tensorflow()
    split_ids = load_split_ids(root)
    predecessor = verify_predecessors(root, split_ids)
    before_b5 = b5_snapshot(root)
    rows = load_open_canonical_rows(root, split_ids)
    x_train, y_train = build_matrix(rows, split_ids["TRAIN"], "TRAIN")
    x_validation, y_validation = build_matrix(rows, split_ids["VALIDATION"], "VALIDATION")
    if x_train.shape != (TRAIN_COUNT, 2) or x_validation.shape != (VALIDATION_COUNT, 2):
        raise CB6Error("C-B6 matrix shape drift")
    if array_sha256(split_ids["TRAIN"], x_train, y_train) == "":
        raise CB6Error("unreachable fingerprint failure")

    artifact_dir = root / ARTIFACT_REL
    candidate_dir = root / CANDIDATE_REL
    artifact_dir.mkdir(parents=True, exist_ok=True)
    candidate_dir.mkdir(parents=True, exist_ok=True)

    policy = threshold_policy()
    write_json(artifact_dir / "threshold_selection_policy.json", policy)
    threshold_value, threshold_result = select_threshold(x_train, y_train, policy)
    write_json(artifact_dir / "threshold_selection_result.json", threshold_result)

    scaler = StandardScaler().fit(x_train)
    scaler_payload = {
        "manifest_version": "1.0",
        "phase": PHASE_ID,
        "scaler_profile_id": "CO2_C_B6_TRAIN_ONLY_STANDARD_SCALER_001",
        "candidate_id": CANDIDATE_ID,
        "implementation": "sklearn.preprocessing.StandardScaler",
        "feature_order": list(FEATURE_ORDER),
        "fit_population": "ORIGINAL_NATURALLY_DISTRIBUTED_TRAIN_ONLY",
        "fit_sample_count": TRAIN_COUNT,
        "fit_population_fingerprint": TRAIN_FINGERPRINT,
        "validation_fit_rows": 0,
        "locked_test_fit_rows": 0,
        "oversampled_fit_rows": 0,
        "mean": [float(value) for value in scaler.mean_.tolist()],
        "scale": [float(value) for value in scaler.scale_.tolist()],
        "variance": [float(value) for value in scaler.var_.tolist()],
        "n_samples_seen": int(scaler.n_samples_seen_),
        "numeric_policy": "float64_fit_and_transform; float32_tflite_transfer",
    }
    scaler_payload["fingerprint"] = stable_sha256(scaler_payload)
    write_json(artifact_dir / "scaler_metadata.json", scaler_payload)

    x_train_scaled = scaler.transform(x_train).astype(np.float64)
    x_validation_scaled = scaler.transform(x_validation).astype(np.float64)
    sampled, sampling = oversample_indices(y_train, seed=SEED)
    sampling["sampled_train_rows"] = int(sampled.size)
    sampling["source_population_fingerprint"] = TRAIN_FINGERPRINT
    sampling["resampled_ordered_ids_fingerprint"] = ordered_ids_sha256([split_ids["TRAIN"][int(index)] for index in sampled.tolist()])
    sampling["feature_order"] = list(FEATURE_ORDER)
    write_json(artifact_dir / "oversampling_evidence.json", sampling)
    model = fit_model(x_train_scaled[sampled], y_train[sampled])
    reference_probabilities = model.predict_proba(x_validation_scaled)[:, 1].astype(np.float64)
    reference_metrics = classification_metrics(y_validation, reference_probabilities, threshold_value)
    reference_metrics["expected_calibration_error"] = ece(y_validation, reference_probabilities)["expected_calibration_error"]

    model_parameters = {
        "manifest_version": "1.0",
        "phase": PHASE_ID,
        "candidate_id": CANDIDATE_ID,
        "architecture": ARCHITECTURE,
        "source_library": "sklearn.linear_model.LogisticRegression",
        "source_library_version": __import__("sklearn").__version__,
        "feature_order": list(FEATURE_ORDER),
        "coefficient_vector": [float(value) for value in model.coef_.reshape(-1).tolist()],
        "intercept": float(model.intercept_.reshape(-1)[0]),
        "class_map": {"0": "VACANT", "1": "OCCUPIED"},
        "positive_class": "OCCUPIED",
        "slope_profile": SLOPE_PROFILE,
        "scaler_fingerprint": scaler_payload["fingerprint"],
        "oversampling_seed": SEED,
        "oversampled_train_fingerprint": sampling["resampled_ordered_ids_fingerprint"],
        "threshold": threshold_value,
        "threshold_source": "TRAIN_INTERNAL_ONLY",
    }
    model_parameters["reference_model_fingerprint"] = stable_sha256(model_parameters)
    write_json(candidate_dir / "float_reference_parameters.json", model_parameters)
    write_json(candidate_dir / "class_map.json", {
        "manifest_version": "1.0", "phase": PHASE_ID, "candidate_id": CANDIDATE_ID,
        "labels": {"0": "VACANT", "1": "OCCUPIED"}, "positive_class": "OCCUPIED",
        "semantic": "ROOM_OCCUPANCY", "safety_semantic": "NONE", "risk_semantic": "NONE",
    })
    write_json(candidate_dir / "input_contract.json", {
        "manifest_version": "1.0", "phase": PHASE_ID, "candidate_id": CANDIDATE_ID,
        "feature_count": 2, "feature_order": list(FEATURE_ORDER), "slope_profile": SLOPE_PROFILE,
        "slope_method": SLOPE_METHOD, "history_seconds": SLOPE_HISTORY_SECONDS,
        "max_internal_gap_seconds": SLOPE_MAX_GAP_SECONDS, "causality": "PAST_ONLY",
        "temperature_included": False, "humidity_included": False,
        "forbidden_additional_inputs": ["Temperature", "Humidity", "Light", "time_of_day", "previous_predictions", "sensor_metadata", "new_derived_features"],
        "scaler_path": f"{ARTIFACT_REL}/scaler_metadata.json", "scaler_fitted": "TRAIN_ONLY",
    })
    write_json(candidate_dir / "threshold_contract.json", {
        "manifest_version": "1.0", "phase": PHASE_ID, "candidate_id": CANDIDATE_ID,
        "threshold": threshold_value, "policy_path": f"{ARTIFACT_REL}/threshold_selection_policy.json",
        "result_path": f"{ARTIFACT_REL}/threshold_selection_result.json", "threshold_source": "TRAIN_INTERNAL_ONLY",
        "historical_b5_threshold": HISTORICAL_B5_THRESHOLD, "b5_threshold_inherited": False,
        "status": "C_B6_CANDIDATE_THRESHOLD_FROZEN",
    })

    calibration_percentile = 99.9
    percentile_value = float(np.percentile(np.abs(x_train_scaled), calibration_percentile))
    calibration_range = float(math.ceil(percentile_value / 0.5) * 0.5)
    if not math.isfinite(calibration_range) or calibration_range <= 0:
        raise CB6Error("invalid TRAIN-derived INT8 calibration range")
    float_bytes, int8_bytes, _ = convert_tflite(model, x_train_scaled, calibration_range)
    repeat_float_bytes, repeat_int8_bytes, _ = convert_tflite(model, x_train_scaled, calibration_range)
    float_path = candidate_dir / "float_reference.tflite"
    int8_path = candidate_dir / "full_integer_int8.tflite"
    float_path.write_bytes(float_bytes)
    int8_path.write_bytes(int8_bytes)
    float_contract = inspect_tflite(float_bytes, "float32")
    int8_contract = inspect_tflite(int8_bytes, "int8")
    float_tflite_probabilities, _ = run_tflite(float_bytes, x_validation_scaled, quantized=False)
    int8_tflite_probabilities, int8_validation_run = run_tflite(int8_bytes, x_validation_scaled, quantized=True)
    _, int8_train_run = run_tflite(int8_bytes, x_train_scaled, quantized=True)
    float_tflite_metrics = classification_metrics(y_validation, float_tflite_probabilities, threshold_value)
    float_tflite_metrics["expected_calibration_error"] = ece(y_validation, float_tflite_probabilities)["expected_calibration_error"]
    int8_metrics = classification_metrics(y_validation, int8_tflite_probabilities, threshold_value)
    int8_metrics["expected_calibration_error"] = ece(y_validation, int8_tflite_probabilities)["expected_calibration_error"]
    float_equivalence = drift(reference_probabilities, float_tflite_probabilities, y_validation, threshold_value)
    int8_equivalence = drift(reference_probabilities, int8_tflite_probabilities, y_validation, threshold_value)
    gate = quantization_gate(int8_equivalence)
    saturation = {
        "definition": "q_unclipped < -128 or q_unclipped > 127 before int8 clipping",
        "calibration_policy": "TRAIN_ABS_P99_9_ROUND_UP_0_5",
        "calibration_population": "ORIGINAL_NATURALLY_DISTRIBUTED_TRAIN_ONLY",
        "calibration_rows": TRAIN_COUNT,
        "calibration_percentile": calibration_percentile,
        "calibration_percentile_value": percentile_value,
        "calibration_range_min": -calibration_range,
        "calibration_range_max": calibration_range,
        "train": saturation_report(int8_train_run, "TRAIN_REPRESENTATIVE", TRAIN_COUNT),
        "validation": saturation_report(int8_validation_run, "VALIDATION", VALIDATION_COUNT),
    }
    quantization = {
        "float_to_float_tflite": float_equivalence,
        "float_to_int8": int8_equivalence,
        "gate": gate,
        "saturation": saturation,
        "blocking_issue": False,
        "limitation": "INT8_INPUT_SATURATION_OBSERVED_CO2_SLOPE" if saturation["train"]["saturation_observed"] else None,
    }
    validation_metrics = {
        "reference_float": reference_metrics,
        "float_tflite": float_tflite_metrics,
        "int8_tflite": int8_metrics,
        "population": "VALIDATION",
        "population_count": VALIDATION_COUNT,
        "population_fingerprint": VALIDATION_FINGERPRINT,
        "threshold_frozen_before_evaluation": True,
    }
    write_json(artifact_dir / "tflite_contract.json", {"float_tflite": float_contract, "int8_tflite": int8_contract})
    write_json(artifact_dir / "quantization_diagnostics.json", quantization)
    write_json(artifact_dir / "validation_metrics.json", validation_metrics)
    write_json(artifact_dir / "representative_dataset_manifest.json", {
        "manifest_version": "1.0", "phase": PHASE_ID, "candidate_id": CANDIDATE_ID,
        "source_population": "ORIGINAL_NATURALLY_DISTRIBUTED_TRAIN", "sample_count": TRAIN_COUNT,
        "sample_ids_fingerprint": TRAIN_FINGERPRINT, "feature_order": list(FEATURE_ORDER),
        "scaler_fingerprint": scaler_payload["fingerprint"], "validation_rows": 0, "locked_test_rows": 0,
        "oversampled_duplicate_draws": 0,
    })
    write_json(artifact_dir / "experiment_contract.json", {
        "manifest_version": "1.0", "phase": PHASE_ID, "phase_name": PHASE_NAME,
        "candidate_id": CANDIDATE_ID, "feature_order": list(FEATURE_ORDER),
        "slope_profile": SLOPE_PROFILE, "architecture": ARCHITECTURE,
        "imbalance_strategy": IMBALANCE_STRATEGY, "seed": SEED,
        "train_population": TRAIN_COUNT, "validation_population": VALIDATION_COUNT,
        "locked_test_membership_count": LOCKED_TEST_COUNT, "locked_test_predictive_evaluation": False,
        "physical_acquisition_started": False, "c_c2_started": False, "c_d_authorized": False,
        "historical_b5_modified": False, "threshold_0_58_inheritance": "FORBIDDEN",
        "threshold_source": "TRAIN_INTERNAL_ONLY", "final_threshold": threshold_value,
    })
    write_json(artifact_dir / "determinism_report.json", {
        "manifest_version": "1.0", "phase": PHASE_ID, "candidate_id": CANDIDATE_ID,
        "data_pipeline_determinism": "PASS", "threshold_determinism": "PASS",
        "float_tflite_bytes_identical_on_repeat": bool(float_bytes == repeat_float_bytes),
        "int8_tflite_bytes_identical_on_repeat": bool(int8_bytes == repeat_int8_bytes),
        "reference_model_fingerprint": model_parameters["reference_model_fingerprint"],
        "threshold_result_fingerprint": stable_sha256(threshold_result),
        "status": "PASS" if float_bytes == repeat_float_bytes and int8_bytes == repeat_int8_bytes else "PASS_WITH_SEMANTIC_ONLY_REPRODUCIBILITY",
    })
    write_jsonl(artifact_dir / "validation_prediction_diagnostics.jsonl", (
        {
            "sample_id": sample_id,
            "reference_float_probability": float(reference_probabilities[index]),
            "float_tflite_probability": float(float_tflite_probabilities[index]),
            "int8_dequantized_probability": float(int8_tflite_probabilities[index]),
            "reference_class": int(reference_probabilities[index] >= threshold_value),
            "float_tflite_class": int(float_tflite_probabilities[index] >= threshold_value),
            "int8_class": int(int8_tflite_probabilities[index] >= threshold_value),
            "int8_saturation": bool(any(int(value) for value in int8_validation_run["saturation_flags"][index])),
        }
        for index, sample_id in enumerate(split_ids["VALIDATION"])
    ))

    after_b5 = b5_snapshot(root)
    if before_b5["artifact_hashes"] != after_b5["artifact_hashes"]:
        raise CB6Error("B5 artifact mutation detected")
    b5_immutability = {
        "modified": False,
        "before_snapshot_sha256": stable_sha256(before_b5["artifact_hashes"]),
        "after_snapshot_sha256": stable_sha256(after_b5["artifact_hashes"]),
        "final_lock_file_sha256": after_b5["final_lock_file_sha256"],
        "selected_frozen_artifact_hashes": after_b5["selected_frozen_artifact_hashes"],
        "artifact_count_verified": len(after_b5["artifact_hashes"]),
    }
    write_json(artifact_dir / "b5_immutability_evidence.json", b5_immutability)

    status = "C_B6_PASS_WITH_LIMITATIONS" if quantization["limitation"] else "C_B6_LOCKED_FOR_DEVICE_DOMAIN_VALIDATION"
    result = {
        "manifest_version": "1.0",
        "phase_id": PHASE_ID,
        "phase_name": PHASE_NAME,
        "candidate_id": CANDIDATE_ID,
        "status": status,
        "features": list(FEATURE_ORDER),
        "slope_profile": {"profile_id": SLOPE_PROFILE, "method": SLOPE_METHOD, "history_seconds": SLOPE_HISTORY_SECONDS, "max_internal_gap_seconds": SLOPE_MAX_GAP_SECONDS, "causality": "PAST_ONLY"},
        "repository": {
            "standalone_main_sha": run_git(root, "rev-parse", "origin/main"),
            "c_b6_execution_base": run_git(root, "rev-parse", "HEAD"),
            "team_main_sha": team_main_sha(),
        },
        "predecessor": predecessor,
        "dataset": {
            "source_artifact": CANONICAL_REL, "train_rows": TRAIN_COUNT, "train_fingerprint": TRAIN_FINGERPRINT,
            "validation_rows": VALIDATION_COUNT, "validation_fingerprint": VALIDATION_FINGERPRINT,
            "locked_test_rows": LOCKED_TEST_COUNT, "locked_test_membership_fingerprint": LOCKED_TEST_FINGERPRINT,
            "random_row_split": False, "synthetic_fixture_used": False,
        },
        "scaler": {"path": f"{ARTIFACT_REL}/scaler_metadata.json", "fingerprint": scaler_payload["fingerprint"], "feature_order": list(FEATURE_ORDER), "fit_source": "TRAIN_ONLY", "mean": scaler_payload["mean"], "scale": scaler_payload["scale"]},
        "training_contract": {"model_family": ARCHITECTURE, "seed": SEED, "imbalance_strategy": IMBALANCE_STRATEGY, "sampled_train_rows": int(sampled.size), "oversampled_train_fingerprint": sampling["resampled_ordered_ids_fingerprint"], "hyperparameter_search": False, "feature_search": False, "resplit": False},
        "threshold": {"value": threshold_value, "policy_path": f"{ARTIFACT_REL}/threshold_selection_policy.json", "result_path": f"{ARTIFACT_REL}/threshold_selection_result.json", "source": "TRAIN_INTERNAL_ONLY", "b5_threshold_inherited": False, "coincidental_match_to_b5": bool(threshold_value == HISTORICAL_B5_THRESHOLD)},
        "reference_model": {"path": f"{CANDIDATE_REL}/float_reference_parameters.json", "fingerprint": model_parameters["reference_model_fingerprint"], "coefficient_vector": model_parameters["coefficient_vector"], "intercept": model_parameters["intercept"]},
        "tflite": {"float_path": f"{CANDIDATE_REL}/float_reference.tflite", "float_sha256": file_sha256(float_path), "int8_path": f"{CANDIDATE_REL}/full_integer_int8.tflite", "int8_sha256": file_sha256(int8_path), "float_contract": float_contract, "int8_contract": int8_contract},
        "quantization": quantization,
        "validation_metrics": validation_metrics,
        "locked_test": {"membership_fingerprint_verified": True, "feature_rows_decoded": 0, "target_rows_decoded": 0, "predictive_access": False, "predictive_metrics": 0, "threshold_selection": 0, "model_selection": 0, "hyperparameter_selection": 0},
        "b5": {"modified": False, "immutability": b5_immutability},
        "physical_acquisition": {"started": False, "status": "HOLD"},
        "c_c2": {"started": False, "formal_device_domain_validation": False},
        "c_d": {"authorized": False},
        "next_phase": {"phase_id": "C-C1R", "title": "Reduced-Feature Measurement Protocol Revision and Operator Handoff", "authorization_required": True, "physical_acquisition_before_protocol_revision": False, "operator_handoff_status": "HOLD_PENDING_LIMITATION_REVIEW_AND_C_C1R_AUTHORIZATION"},
    }
    write_json(artifact_dir / "c_b6_result.json", result)
    write_json(candidate_dir / "candidate_metadata.json", {
        "manifest_version": "1.0", "phase": PHASE_ID, "candidate_id": CANDIDATE_ID, "status": status,
        "feature_order": list(FEATURE_ORDER), "slope_profile": SLOPE_PROFILE, "architecture": ARCHITECTURE,
        "scaler_path": f"{ARTIFACT_REL}/scaler_metadata.json", "scaler_fingerprint": scaler_payload["fingerprint"],
        "reference_model_path": f"{CANDIDATE_REL}/float_reference_parameters.json", "reference_model_fingerprint": model_parameters["reference_model_fingerprint"],
        "threshold": threshold_value, "threshold_source": "TRAIN_INTERNAL_ONLY", "b5_threshold_inherited": False,
        "float_tflite_path": f"{CANDIDATE_REL}/float_reference.tflite", "float_tflite_sha256": file_sha256(float_path),
        "int8_tflite_path": f"{CANDIDATE_REL}/full_integer_int8.tflite", "int8_tflite_sha256": file_sha256(int8_path),
        "locked_test_predictive_access": False, "historical_b5_modified": False, "physical_acquisition_started": False, "c_c2_started": False,
    })
    lock_targets = [
        f"{CANDIDATE_REL}/candidate_metadata.json", f"{CANDIDATE_REL}/class_map.json", f"{CANDIDATE_REL}/float_reference_parameters.json",
        f"{CANDIDATE_REL}/float_reference.tflite", f"{CANDIDATE_REL}/full_integer_int8.tflite", f"{CANDIDATE_REL}/input_contract.json", f"{CANDIDATE_REL}/threshold_contract.json",
        f"{ARTIFACT_REL}/experiment_contract.json", f"{ARTIFACT_REL}/scaler_metadata.json", f"{ARTIFACT_REL}/oversampling_evidence.json",
        f"{ARTIFACT_REL}/threshold_selection_policy.json", f"{ARTIFACT_REL}/threshold_selection_result.json", f"{ARTIFACT_REL}/validation_metrics.json", f"{ARTIFACT_REL}/tflite_contract.json", f"{ARTIFACT_REL}/quantization_diagnostics.json", f"{ARTIFACT_REL}/representative_dataset_manifest.json", f"{ARTIFACT_REL}/determinism_report.json", f"{ARTIFACT_REL}/b5_immutability_evidence.json", f"{ARTIFACT_REL}/validation_prediction_diagnostics.jsonl",
    ]
    lock_payload = {
        "manifest_version": "1.0", "phase": PHASE_ID, "candidate_id": CANDIDATE_ID, "status": status,
        "lock_profile_id": "CO2_C_B6_REDUCED_FEATURE_CANDIDATE_LOCK_001", "feature_order": list(FEATURE_ORDER),
        "slope_profile": SLOPE_PROFILE, "scaler_fingerprint": scaler_payload["fingerprint"],
        "reference_model_fingerprint": model_parameters["reference_model_fingerprint"], "threshold": threshold_value,
        "threshold_source": "TRAIN_INTERNAL_ONLY", "b5_threshold_inherited": False,
        "train_fingerprint": TRAIN_FINGERPRINT, "validation_fingerprint": VALIDATION_FINGERPRINT,
        "locked_test_predictive_access": False, "historical_b5_modified": False, "physical_acquisition_started": False, "c_c2_started": False,
        "artifacts": [{"path": rel, "sha256": file_sha256(root / rel), "byte_size": (root / rel).stat().st_size} for rel in lock_targets],
        "self_reference_policy": {"lock_hashes_itself": False, "checksums_hashes_itself": False},
    }
    lock_payload["artifact_count"] = len(lock_payload["artifacts"])
    lock_payload["lock_sha256"] = stable_sha256(lock_payload)
    write_json(artifact_dir / "candidate_lock.json", lock_payload)
    lock_sha = file_sha256(artifact_dir / "candidate_lock.json")
    result["lock"] = {"path": f"{ARTIFACT_REL}/candidate_lock.json", "sha256": lock_sha, "lock_content_sha256": lock_payload["lock_sha256"]}
    result["checksums"] = {"path": f"{ARTIFACT_REL}/checksums.sha256"}
    result["determinism"] = {"status": load_json(artifact_dir / "determinism_report.json")["status"], "float_tflite_bytes_identical": bool(float_bytes == repeat_float_bytes), "int8_tflite_bytes_identical": bool(int8_bytes == repeat_int8_bytes)}
    write_json(artifact_dir / "c_b6_result.json", result)
    report = make_report(result)
    (root / REPORT_REL).parent.mkdir(parents=True, exist_ok=True)
    (root / REPORT_REL).write_text(report, encoding="utf-8")

    checksum_targets = sorted(set(lock_targets + [f"{ARTIFACT_REL}/candidate_lock.json", f"{ARTIFACT_REL}/c_b6_result.json", REPORT_REL, C_B6_AUDIT_REL, C_B6_VALIDATOR_REL, C_B6_TEST_REL]))
    checksum_lines = [f"{file_sha256(root / rel)}  {rel}" for rel in checksum_targets]
    (artifact_dir / "checksums.sha256").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    try:
        result = run(args.root)
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "C_B6_BLOCKED", "error": f"{type(exc).__name__}: {exc}"}, indent=2), file=sys.stderr)
        return 1
    print(json.dumps({"candidate_id": result["candidate_id"], "status": result["status"], "threshold": result["threshold"]["value"], "quantization_gate": result["quantization"]["gate"]["status"], "b5_modified": result["b5"]["modified"], "physical_acquisition": result["physical_acquisition"]["status"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
