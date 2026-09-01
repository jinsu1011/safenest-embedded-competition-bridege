#!/usr/bin/env python3
"""Audit CO2 temperature/humidity necessity without opening LOCKED_TEST.

This is a follow-up offline comparison on the already-closed C-B2 lineage.
It keeps the canonical split, ENDPOINT_H150 slope, TRAIN-only scaling, the
selected BALANCED_RANDOM_OVERSAMPLE procedure, the fixed logistic probe, and
the frozen B5 reference threshold. Only the model input dimension changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import warnings
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

import numpy as np
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from datasets.co2.imbalance_calibration import (
    DEFAULT_SEED,
    _probability_fingerprint,
    build_balanced_oversample_plan,
    build_logistic_probe,
    classification_metrics_at_threshold,
    expected_calibration_error,
    fit_train_only_scaler,
    probability_quality_metrics,
)
from datasets.co2.offline_experiment import MatrixBundle, ordered_id_list_sha256


FULL_FEATURES: Tuple[str, ...] = ("CO2", "Temperature", "Humidity", "CO2_slope")
ARM_FEATURES: Mapping[str, Tuple[str, ...]] = {
    "A": FULL_FEATURES,
    "B": ("CO2", "CO2_slope"),
    "C": ("CO2",),
    "D": ("CO2", "Temperature", "Humidity"),
}
ARM_DESCRIPTIONS: Mapping[str, str] = {
    "A": "CO2 + Temperature + Humidity + CO2_slope",
    "B": "CO2 + CO2_slope",
    "C": "CO2 only",
    "D": "CO2 + Temperature + Humidity",
}

TRAIN_COUNT = 8140
VALIDATION_COUNT = 2662
LOCKED_TEST_COUNT = 9749
THRESHOLD = 0.58
EXPECTED_TRAIN_FINGERPRINT = (
    "492ca1f67e44b4a2018b743ec0fc3d20b418f7823d5f2643d8c90b0d39de8fab"
)
EXPECTED_VALIDATION_FINGERPRINT = (
    "19321e57fe72f6482b3c7b5d3714d21e9c13b753173ceb56ea694524ac6529ef"
)
EXPECTED_LOCKED_TEST_FINGERPRINT = (
    "0bac8dc1affae1de48ea68f01e866508ea19f31e194a7c0dccbf617e529344e7"
)
EXPECTED_B5_SCALER_FINGERPRINT = (
    "d0cf83558fb0de9dcdc97f0d94781a5a475a6f68e8d818121aee929030e5dc89"
)
EXPECTED_B5_MODEL_SHA256 = (
    "bb2ed28533bca75d4fa3d06348e017c506df47d7c34b29574b77f70b6b386816"
)


def stable_json_sha256(payload: Any) -> str:
    blob = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_ordered_eligible_ids(root: Path) -> Dict[str, List[str]]:
    path = root / "datasets/co2/manifests/c_a5_canonical_samples/model_eligible_sample_ids.jsonl"
    by_role: Dict[str, List[str]] = {"TRAIN": [], "VALIDATION": [], "LOCKED_TEST": []}
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            sid = str(row["canonical_sample_id"])
            role = str(row["future_split_role"])
            if role not in by_role:
                raise RuntimeError(f"Unexpected eligible split role: {role}")
            if sid in seen:
                raise RuntimeError(f"Duplicate eligible sample ID: {sid}")
            seen.add(sid)
            by_role[role].append(sid)
    expected = {
        "TRAIN": (TRAIN_COUNT, EXPECTED_TRAIN_FINGERPRINT),
        "VALIDATION": (VALIDATION_COUNT, EXPECTED_VALIDATION_FINGERPRINT),
        "LOCKED_TEST": (LOCKED_TEST_COUNT, EXPECTED_LOCKED_TEST_FINGERPRINT),
    }
    for role, (count, fingerprint) in expected.items():
        if len(by_role[role]) != count:
            raise RuntimeError(f"{role} eligible count drift: {len(by_role[role])}")
        actual = ordered_id_list_sha256(by_role[role])
        if actual != fingerprint:
            raise RuntimeError(f"{role} eligible fingerprint drift: {actual}")
    return by_role


def _finite_feature(row: Mapping[str, Any], key: str, sid: str) -> float:
    value = row.get(key)
    if value is None or not math.isfinite(float(value)):
        raise RuntimeError(f"Missing/non-finite {key} for {sid}")
    return float(value)


def load_guarded_matrices(
    root: Path, eligible: Mapping[str, Sequence[str]]
) -> Tuple[Dict[str, MatrixBundle], Dict[str, Any]]:
    """Materialize only TRAIN/VALIDATION features; skip LOCKED_TEST values."""

    wanted = {
        role: set(ids) for role, ids in eligible.items()
    }
    rows_by_role: Dict[str, Dict[str, Tuple[List[float], int]]] = {
        "TRAIN": {},
        "VALIDATION": {},
    }
    source_path = root / "datasets/co2/manifests/c_a5_canonical_samples/canonical_source_samples.jsonl"
    stats: Dict[str, Any] = {
        "canonical_source_rows_seen": 0,
        "canonical_source_sha256": file_sha256(source_path),
        "train_validation_feature_rows_decoded": 0,
        "train_validation_target_rows_decoded": 0,
        "locked_test_canonical_rows_seen": 0,
        "locked_test_eligible_rows_seen": 0,
        "locked_test_feature_rows_decoded": 0,
        "locked_test_target_rows_decoded": 0,
        "locked_test_predictive_metrics": 0,
        "locked_test_accessed_for_selection": False,
        "source_archive_sha256_values": set(),
    }

    with source_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            stats["canonical_source_rows_seen"] += 1
            row = json.loads(line)
            sid = str(row["canonical_sample_id"])
            role = str(row["future_split_role"])

            # This branch intentionally does not read any feature or target
            # field. Membership/role inspection is integrity-only.
            if role == "LOCKED_TEST":
                stats["locked_test_canonical_rows_seen"] += 1
                if sid in wanted["LOCKED_TEST"]:
                    stats["locked_test_eligible_rows_seen"] += 1
                continue

            if role not in ("TRAIN", "VALIDATION") or sid not in wanted[role]:
                continue
            if sid in rows_by_role[role]:
                raise RuntimeError(f"Duplicate canonical row for {sid}")
            if row.get("co2_slope_status") != "FEATURE_AVAILABLE":
                raise RuntimeError(f"Eligible row has unavailable slope: {sid}")

            # Feature/target access is confined to TRAIN and VALIDATION rows.
            features = [
                _finite_feature(row, "co2", sid),
                _finite_feature(row, "temperature", sid),
                _finite_feature(row, "humidity", sid),
                _finite_feature(row, "co2_slope", sid),
            ]
            label = int(row["occupancy_source_value"])
            if label not in (0, 1):
                raise RuntimeError(f"Non-binary occupancy target for {sid}")
            rows_by_role[role][sid] = (features, label)
            stats["train_validation_feature_rows_decoded"] += 1
            stats["train_validation_target_rows_decoded"] += 1
            source_sha = row.get("source_archive_sha256")
            if source_sha:
                stats["source_archive_sha256_values"].add(str(source_sha))

    if stats["locked_test_eligible_rows_seen"] != LOCKED_TEST_COUNT:
        raise RuntimeError("LOCKED_TEST membership accounting drift")
    if len(rows_by_role["TRAIN"]) != TRAIN_COUNT:
        raise RuntimeError("TRAIN canonical materialization incomplete")
    if len(rows_by_role["VALIDATION"]) != VALIDATION_COUNT:
        raise RuntimeError("VALIDATION canonical materialization incomplete")

    bundles: Dict[str, MatrixBundle] = {}
    for role in ("TRAIN", "VALIDATION"):
        ids = list(eligible[role])
        features = np.asarray([rows_by_role[role][sid][0] for sid in ids], dtype=np.float64)
        labels = np.asarray([rows_by_role[role][sid][1] for sid in ids], dtype=np.int64)
        if not np.isfinite(features).all():
            raise RuntimeError(f"Non-finite values in {role} matrix")
        bundles[role] = MatrixBundle(
            sample_ids=ids,
            features=features,
            labels=labels,
            feature_names=FULL_FEATURES,
            split_role=role,
        )

    stats["source_archive_sha256_values"] = sorted(stats["source_archive_sha256_values"])
    return bundles, stats


def subset_bundle(bundle: MatrixBundle, feature_names: Sequence[str]) -> MatrixBundle:
    indices = [FULL_FEATURES.index(name) for name in feature_names]
    return MatrixBundle(
        sample_ids=list(bundle.sample_ids),
        # Keep the same C-contiguous reduction order used by the original
        # four-feature B2 materialization; otherwise StandardScaler's
        # floating-point reduction can produce a different evidence hash.
        features=np.ascontiguousarray(bundle.features[:, indices]),
        labels=bundle.labels.copy(),
        feature_names=tuple(feature_names),
        split_role=bundle.split_role,
    )


def fit_scaler(bundle: MatrixBundle, train_fingerprint: str) -> Tuple[StandardScaler, Dict[str, Any]]:
    if bundle.feature_names == FULL_FEATURES:
        scaler, evidence = fit_train_only_scaler(
            bundle, fit_population_fingerprint=train_fingerprint
        )
        return scaler, evidence

    if bundle.split_role != "TRAIN":
        raise RuntimeError("Reduced-arm scaler fit must use TRAIN")
    scaler = StandardScaler(copy=True, with_mean=True, with_std=True)
    with threadpool_limits(limits=1):
        scaler.fit(bundle.features)
    payload = {
        "feature_order": list(bundle.feature_names),
        "fit_population_fingerprint": train_fingerprint,
        "mean": [float(x) for x in scaler.mean_],
        "scale": [float(x) for x in scaler.scale_],
        "var": [float(x) for x in scaler.var_],
        "n_samples_seen": int(scaler.n_samples_seen_),
    }
    evidence = {
        "implementation": "sklearn.preprocessing.StandardScaler",
        "feature_order": list(bundle.feature_names),
        "fit_population": "ORIGINAL_NATURALLY_DISTRIBUTED_TRAIN_ONLY",
        "fit_sample_count": int(bundle.features.shape[0]),
        "fit_population_fingerprint": train_fingerprint,
        "validation_fit_rows": 0,
        "locked_test_fit_rows": 0,
        "oversampled_fit_rows": 0,
        "fit_once": True,
        "reused_for_arm": True,
        "mean": payload["mean"],
        "scale": payload["scale"],
        "variance": payload["var"],
        "n_samples_seen": payload["n_samples_seen"],
        "scaler_fingerprint": stable_json_sha256(payload),
    }
    return scaler, evidence


def run_arm(
    arm_id: str,
    train: MatrixBundle,
    validation: MatrixBundle,
    train_fingerprint: str,
    validation_fingerprint: str,
    oversample_indices: np.ndarray,
) -> Dict[str, Any]:
    scaler, scaler_evidence = fit_scaler(train, train_fingerprint)
    with threadpool_limits(limits=1):
        train_scaled = scaler.transform(train.features)
        validation_scaled = scaler.transform(validation.features)

    model = build_logistic_probe(None)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        with threadpool_limits(limits=1):
            model.fit(train_scaled[oversample_indices], train.labels[oversample_indices])
    convergence_warnings = [
        str(item.message)
        for item in caught
        if issubclass(item.category, ConvergenceWarning)
    ]
    if convergence_warnings:
        raise RuntimeError(f"Convergence warning for arm {arm_id}: {convergence_warnings}")

    probabilities = np.asarray(model.predict_proba(validation_scaled)[:, 1], dtype=np.float64)
    metrics, _ = classification_metrics_at_threshold(
        validation.labels, probabilities, THRESHOLD
    )
    quality = probability_quality_metrics(validation.labels, probabilities)
    ece = expected_calibration_error(validation.labels, probabilities)
    numeric_metrics = {
        key: float(metrics[key])
        for key in (
            "accuracy",
            "balanced_accuracy",
            "precision_occupied",
            "recall_occupied",
            "precision_vacant",
            "recall_vacant",
            "f1_occupied",
            "f1_vacant",
            "macro_f1",
        )
    }
    return {
        "arm_id": arm_id,
        "description": ARM_DESCRIPTIONS[arm_id],
        "feature_order": list(train.feature_names),
        "feature_count": len(train.feature_names),
        "scaler": scaler_evidence,
        "model": {
            "architecture": "B2_FIXED_LOGISTIC_PROBE_001",
            "class_imbalance_strategy": "BALANCED_RANDOM_OVERSAMPLE",
            "fit_population": "TRAIN_ONLY",
            "fit_row_count": int(oversample_indices.size),
            "fit_unique_original_row_count": int(train.features.shape[0]),
            "coefficients": [float(x) for x in model.coef_[0]],
            "intercept": [float(x) for x in model.intercept_],
            "n_iter": [int(x) for x in model.n_iter_],
            "seed": DEFAULT_SEED,
            "threshold": THRESHOLD,
        },
        "validation": {
            "sample_count": int(validation.labels.size),
            "population_fingerprint": validation_fingerprint,
            "metrics": numeric_metrics,
            "confusion_matrix": metrics["confusion_matrix"],
            "threshold": THRESHOLD,
            "probability_quality_metrics": quality,
            "expected_calibration_error": float(ece["expected_calibration_error"]),
            "probability_vector_sha256": _probability_fingerprint(
                validation.sample_ids, probabilities
            ),
        },
    }


def directional_classification(arms: Mapping[str, Mapping[str, Any]]) -> Tuple[str, str]:
    a = arms["A"]["validation"]["metrics"]
    b = arms["B"]["validation"]["metrics"]
    primary = ("macro_f1", "precision_occupied", "recall_occupied")
    b_values = [float(b[key]) for key in primary]
    a_values = [float(a[key]) for key in primary]
    b_dominates = all(bv >= av for av, bv in zip(a_values, b_values))
    a_dominates = all(av >= bv for av, bv in zip(a_values, b_values))
    any_difference = any(av != bv for av, bv in zip(a_values, b_values))
    if b_dominates and any_difference:
        return (
            "T_RH_FEATURE_DEPENDENCE_LOW",
            "Arm B is directionally no worse than arm A on macro F1, occupied precision, and occupied recall; no equivalence margin was imposed.",
        )
    if a_dominates and any_difference:
        return (
            "T_RH_FEATURE_DEPENDENCE_MATERIAL",
            "Arm A is directionally no worse than arm B on macro F1, occupied precision, and occupied recall; no equivalence margin was imposed.",
        )
    if not any_difference:
        return (
            "T_RH_FEATURE_DEPENDENCE_LOW",
            "Arms A and B are numerically identical on the three primary comparison metrics; no equivalence margin was imposed.",
        )
    return (
        "T_RH_FEATURE_DEPENDENCE_INCONCLUSIVE",
        "Arms A and B have mixed directional results across macro F1, occupied precision, and occupied recall; no equivalence margin was imposed.",
    )


def build_result(root: Path) -> Dict[str, Any]:
    eligible = load_ordered_eligible_ids(root)
    bundles, loading = load_guarded_matrices(root, eligible)
    train = bundles["TRAIN"]
    validation = bundles["VALIDATION"]
    train_fp = ordered_id_list_sha256(train.sample_ids)
    validation_fp = ordered_id_list_sha256(validation.sample_ids)
    if train_fp != EXPECTED_TRAIN_FINGERPRINT or validation_fp != EXPECTED_VALIDATION_FINGERPRINT:
        raise RuntimeError("TRAIN/VALIDATION fingerprint drift")

    oversample_plan = build_balanced_oversample_plan(
        train.labels, train.sample_ids, seed=DEFAULT_SEED, source_role="TRAIN"
    )
    arms: Dict[str, Dict[str, Any]] = {}
    for arm_id, feature_names in ARM_FEATURES.items():
        arms[arm_id] = run_arm(
            arm_id,
            subset_bundle(train, feature_names),
            subset_bundle(validation, feature_names),
            train_fp,
            validation_fp,
            oversample_plan.training_indices,
        )

    classification, classification_basis = directional_classification(arms)
    deltas_a_minus_b = {
        key: float(
            arms["A"]["validation"]["metrics"][key]
            - arms["B"]["validation"]["metrics"][key]
        )
        for key in (
            "accuracy",
            "balanced_accuracy",
            "precision_occupied",
            "recall_occupied",
            "precision_vacant",
            "recall_vacant",
            "macro_f1",
        )
    }

    b5_metadata_rel = "models/co2/candidates/c_b5/final_candidate_metadata.json"
    b5_metadata = load_json(root / b5_metadata_rel)
    if b5_metadata["feature_order"] != list(FULL_FEATURES):
        raise RuntimeError("B5 feature order drift")
    if float(b5_metadata["threshold"]) != THRESHOLD:
        raise RuntimeError("B5 threshold drift")
    if b5_metadata["scaler_identity"]["fingerprint"] != EXPECTED_B5_SCALER_FINGERPRINT:
        raise RuntimeError("B5 scaler fingerprint drift")
    if b5_metadata["model_sha256"] != EXPECTED_B5_MODEL_SHA256:
        raise RuntimeError("B5 model fingerprint drift")
    a_scaler_fp = arms["A"]["scaler"]["scaler_fingerprint"]
    if a_scaler_fp != EXPECTED_B5_SCALER_FINGERPRINT:
        raise RuntimeError(f"Reconstructed A scaler fingerprint drift: {a_scaler_fp}")

    result = {
        "manifest_version": "1.0",
        "audit_id": "CO2_TRH_FEATURE_NECESSITY_AUDIT_001",
        "phase_boundary": "C-C1_FOLLOW_UP_OFFLINE_EVIDENCE_ONLY",
        "repo_relative_source_paths": {
            "eligible_ids": "datasets/co2/manifests/c_a5_canonical_samples/model_eligible_sample_ids.jsonl",
            "canonical_samples": "datasets/co2/manifests/c_a5_canonical_samples/canonical_source_samples.jsonl",
            "b0_contract": "datasets/co2/manifests/c_b0_offline_experiment_contract/experiment_contract.json",
            "b2_scaler_evidence": "datasets/co2/manifests/c_b2_imbalance_calibration/preprocessing_scaler_evidence.json",
            "b5_metadata": b5_metadata_rel,
        },
        "dataset_lineage": {
            "train_count": TRAIN_COUNT,
            "validation_count": VALIDATION_COUNT,
            "locked_test_count": LOCKED_TEST_COUNT,
            "train_fingerprint": train_fp,
            "validation_fingerprint": validation_fp,
            "locked_test_fingerprint": EXPECTED_LOCKED_TEST_FINGERPRINT,
            "canonical_source_sha256": loading["canonical_source_sha256"],
            "source_archive_sha256_values": loading["source_archive_sha256_values"],
            "synthetic_fixture_used": False,
            "random_row_split_used": False,
        },
        "locked_test_policy": {
            "sealed": True,
            "used_for_feature_selection": False,
            "used_for_scaler_fit": False,
            "used_for_model_fit": False,
            "used_for_threshold_selection": False,
            "used_for_predictive_metrics": False,
            "canonical_rows_seen_for_membership_accounting": loading["locked_test_canonical_rows_seen"],
            "eligible_rows_seen_for_membership_accounting": loading["locked_test_eligible_rows_seen"],
            "feature_rows_decoded": loading["locked_test_feature_rows_decoded"],
            "target_rows_decoded": loading["locked_test_target_rows_decoded"],
            "predictive_metrics": loading["locked_test_predictive_metrics"],
        },
        "fixed_procedure": {
            "feature_arms": {key: list(value) for key, value in ARM_FEATURES.items()},
            "slope_profile": "ENDPOINT_H150",
            "scaler_fit_population": "ORIGINAL_TRAIN_ONLY",
            "imbalance_strategy": "BALANCED_RANDOM_OVERSAMPLE",
            "oversampling_seed": DEFAULT_SEED,
            "model_family": "B2_FIXED_LOGISTIC_PROBE_001",
            "model_parameters": {
                "penalty": "l2",
                "C": 1.0,
                "solver": "lbfgs",
                "fit_intercept": True,
                "max_iter": 2000,
                "random_state": DEFAULT_SEED,
            },
            "decision_threshold": THRESHOLD,
            "threshold_policy": "INHERITED_FROZEN_B5_REFERENCE_THRESHOLD; NOT_RETUNED_FOR_THIS_AUDIT",
            "validation_only_for_comparison": True,
        },
        "arms": arms,
        "metric_deltas_A_minus_B": deltas_a_minus_b,
        "classification": classification,
        "classification_basis": classification_basis,
        "b5_frozen_unchanged": {
            "feature_order": list(b5_metadata["feature_order"]),
            "threshold": float(b5_metadata["threshold"]),
            "scaler_fingerprint": b5_metadata["scaler_identity"]["fingerprint"],
            "model_sha256": b5_metadata["model_sha256"],
            "production_model_modified": False,
            "production_scaler_modified": False,
            "b5_metadata_modified": False,
        },
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Repository-relative JSON output path")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    result = build_result(root)
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": args.output,
        "classification": result["classification"],
        "train_fingerprint": result["dataset_lineage"]["train_fingerprint"],
        "validation_fingerprint": result["dataset_lineage"]["validation_fingerprint"],
        "locked_test_predictive_metrics": result["locked_test_policy"]["predictive_metrics"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
