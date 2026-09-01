#!/usr/bin/env python3
"""Final pre-acquisition CO2 model-input decision audit.

This audit is deliberately narrower than a feature search.  It repeats the
PR #78 A/B comparison over a fixed seed set, performs paired validation-row
bootstrap uncertainty analysis, and applies a predeclared directional
burden-of-proof rule.  LOCKED_TEST is never materialized for prediction.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import subprocess
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence, Tuple

import numpy as np
import sklearn
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from threadpoolctl import threadpool_limits

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from datasets.co2.imbalance_calibration import (  # noqa: E402
    classification_metrics_at_threshold,
    expected_calibration_error,
    probability_quality_metrics,
)
from datasets.co2.offline_experiment import MatrixBundle, ordered_id_list_sha256  # noqa: E402
from scripts.audit_co2_trh_feature_necessity import (  # noqa: E402
    ARM_FEATURES,
    EXPECTED_B5_MODEL_SHA256,
    EXPECTED_B5_SCALER_FINGERPRINT,
    EXPECTED_LOCKED_TEST_FINGERPRINT,
    EXPECTED_TRAIN_FINGERPRINT,
    EXPECTED_VALIDATION_FINGERPRINT,
    FULL_FEATURES,
    file_sha256,
    fit_scaler,
    load_guarded_matrices,
    load_json,
    load_ordered_eligible_ids,
    stable_json_sha256,
    subset_bundle,
)


AUDIT_ID = "CO2_PRE_ACQUISITION_MODEL_INPUT_DECISION_AUDIT_001"
PREDECESSOR_AUDIT_ID = "CO2_TRH_FEATURE_NECESSITY_AUDIT_001"
NEXT_PHASE_ID = "C-B6"
NEXT_PHASE_TITLE = "Reduced-Feature Candidate Development and Lock"
SEED_LIST = (20260810, 20260811, 20260812, 20260813, 20260814)
BOOTSTRAP_SEED = 20260815
BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_PERCENTILES = (2.5, 97.5)
THRESHOLD = 0.58
MODEL_PARAMETERS = {
    "penalty": "l2",
    "C": 1.0,
    "solver": "lbfgs",
    "fit_intercept": True,
    "max_iter": 2000,
}
PRIMARY_METRICS = (
    "accuracy",
    "macro_f1",
    "precision_occupied",
    "recall_occupied",
)
PROBABILITY_METRICS = (
    "pr_auc_average_precision",
    "roc_auc",
    "brier_score",
    "log_loss",
)
LOWER_IS_BETTER_METRICS = frozenset({"brier_score", "log_loss"})
BOOTSTRAP_METRICS = (
    "accuracy",
    "macro_f1",
    "precision_occupied",
    "recall_occupied",
)


class DecisionAuditError(RuntimeError):
    """Raised when the decision experiment cannot satisfy its contract."""


def sha256_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def stable_json_sha256_local(payload: Any) -> str:
    blob = json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256_bytes(blob)


def git_sha(root: Path, ref: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", ref], cwd=root, text=True
    ).strip()


def validate_predecessor(root: Path) -> Dict[str, Any]:
    result_rel = (
        "datasets/co2/manifests/c_c1_trh_feature_necessity_audit/"
        "feature_necessity_result.json"
    )
    result_path = root / result_rel
    if not result_path.is_file():
        raise DecisionAuditError(f"Missing PR #78 result: {result_rel}")
    result = load_json(result_path)
    if result.get("audit_id") != PREDECESSOR_AUDIT_ID:
        raise DecisionAuditError("PR #78 predecessor audit identity drift")
    if result.get("classification") != "T_RH_FEATURE_DEPENDENCE_INCONCLUSIVE":
        raise DecisionAuditError("PR #78 predecessor classification was rewritten")
    checks_rel = (
        "datasets/co2/manifests/c_c1_trh_feature_necessity_audit/checksums.sha256"
    )
    checksum_lines = (root / checks_rel).read_text(encoding="utf-8").splitlines()
    observed = {
        line.split("  ", 1)[1]: line.split("  ", 1)[0]
        for line in checksum_lines
        if line.strip() and "  " in line
    }
    if observed.get(result_rel) != file_sha256(result_path):
        raise DecisionAuditError("PR #78 result checksum mismatch")
    return {
        "audit_id": PREDECESSOR_AUDIT_ID,
        "classification": result["classification"],
        "result_path": result_rel,
        "result_sha256": file_sha256(result_path),
        "prior_metric_deltas_A_minus_B": result["metric_deltas_A_minus_B"],
    }


def finite(value: Any, label: str) -> float:
    if value is None or not math.isfinite(float(value)):
        raise DecisionAuditError(f"Non-finite {label}")
    return float(value)


def build_seeded_oversample_plan(
    labels: np.ndarray, sample_ids: Sequence[str], seed: int
) -> Dict[str, Any]:
    """The C-B2 oversampling procedure with only its predeclared seed varied."""

    if seed not in SEED_LIST:
        raise DecisionAuditError(f"Seed outside predeclared list: {seed}")
    arr = np.asarray(labels, dtype=np.int64)
    if arr.ndim != 1 or arr.size != len(sample_ids):
        raise DecisionAuditError("Seeded oversampling shape mismatch")
    counts = {0: int(np.sum(arr == 0)), 1: int(np.sum(arr == 1))}
    if set(counts) != {0, 1} or counts[0] == counts[1]:
        raise DecisionAuditError(f"Unexpected TRAIN class counts: {counts}")
    majority_label = max(counts, key=lambda label: (counts[label], -label))
    minority_label = 1 - majority_label
    minority_indices = np.flatnonzero(arr == minority_label)
    deficit = counts[majority_label] - counts[minority_label]
    rng = np.random.default_rng(seed)
    appended = np.asarray(
        rng.choice(minority_indices, size=deficit, replace=True), dtype=np.int64
    )
    training_indices = np.concatenate(
        [np.arange(arr.size, dtype=np.int64), appended]
    )
    post_counts = {
        0: int(np.sum(arr[training_indices] == 0)),
        1: int(np.sum(arr[training_indices] == 1)),
    }
    if post_counts[0] != post_counts[1]:
        raise DecisionAuditError(f"Seeded oversampling failed: {post_counts}")
    training_ids = [sample_ids[int(i)] for i in training_indices.tolist()]
    appended_ids = [sample_ids[int(i)] for i in appended.tolist()]
    return {
        "training_indices": training_indices,
        "evidence": {
            "seed": seed,
            "rng": "numpy.random.Generator(PCG64)",
            "method": "MINORITY_RANDOM_OVERSAMPLE_WITH_REPLACEMENT",
            "source_population": "TRAIN_ONLY",
            "source_sample_count": int(arr.size),
            "majority_label": majority_label,
            "minority_label": minority_label,
            "original_class_counts": {
                "VACANT": counts[0],
                "OCCUPIED": counts[1],
            },
            "appended_minority_draw_count": deficit,
            "appended_sequence_sha256": ordered_id_list_sha256(appended_ids),
            "resampled_ordered_sample_ids_sha256": ordered_id_list_sha256(
                training_ids
            ),
            "oversampled_class_counts": {
                "VACANT": post_counts[0],
                "OCCUPIED": post_counts[1],
            },
            "validation_rows_used": 0,
            "locked_test_rows_used": 0,
            "all_majority_examples_retained": True,
            "synthetic_interpolation": False,
        },
    }


def build_seeded_probe(seed: int) -> LogisticRegression:
    return LogisticRegression(
        penalty=MODEL_PARAMETERS["penalty"],
        C=MODEL_PARAMETERS["C"],
        solver=MODEL_PARAMETERS["solver"],
        fit_intercept=MODEL_PARAMETERS["fit_intercept"],
        max_iter=MODEL_PARAMETERS["max_iter"],
        class_weight=None,
        random_state=seed,
    )


def metric_summary(metrics: Mapping[str, Any], quality: Mapping[str, Any], ece: float) -> Dict[str, float]:
    keys = (
        "accuracy",
        "balanced_accuracy",
        "precision_occupied",
        "recall_occupied",
        "f1_occupied",
        "precision_vacant",
        "recall_vacant",
        "f1_vacant",
        "macro_f1",
    )
    output = {key: finite(metrics[key], key) for key in keys}
    output.update({key: finite(quality[key], key) for key in PROBABILITY_METRICS})
    output["expected_calibration_error"] = finite(ece, "expected_calibration_error")
    return output


def run_arm(
    seed: int,
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
    model = build_seeded_probe(seed)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        with threadpool_limits(limits=1):
            model.fit(train_scaled[oversample_indices], train.labels[oversample_indices])
    convergence = [
        str(item.message)
        for item in caught
        if issubclass(item.category, ConvergenceWarning)
    ]
    if convergence:
        raise DecisionAuditError(f"Convergence failure seed={seed} arm={arm_id}")
    probabilities = np.asarray(model.predict_proba(validation_scaled)[:, 1], dtype=np.float64)
    metrics, predictions = classification_metrics_at_threshold(
        validation.labels, probabilities, THRESHOLD
    )
    quality = probability_quality_metrics(validation.labels, probabilities)
    ece = expected_calibration_error(validation.labels, probabilities)
    return {
        "arm_id": arm_id,
        "seed": seed,
        "feature_order": list(train.feature_names),
        "scaler": {
            "feature_order": list(train.feature_names),
            "fit_population": "ORIGINAL_TRAIN_ONLY",
            "fit_sample_count": int(train.features.shape[0]),
            "fit_population_fingerprint": train_fingerprint,
            "scaler_fingerprint": scaler_evidence["scaler_fingerprint"],
            "mean": [finite(x, "scaler mean") for x in scaler.mean_],
            "scale": [finite(x, "scaler scale") for x in scaler.scale_],
        },
        "training": {
            "strategy": "BALANCED_RANDOM_OVERSAMPLE",
            "fit_population": "TRAIN_ONLY",
            "fit_row_count": int(oversample_indices.size),
            "fit_unique_original_row_count": int(train.features.shape[0]),
            "model_parameters": {**MODEL_PARAMETERS, "random_state": seed},
            "coefficients": [finite(x, "coefficient") for x in model.coef_[0]],
            "intercept": [finite(x, "intercept") for x in model.intercept_],
            "n_iter": [int(x) for x in model.n_iter_],
        },
        "validation": {
            "population_fingerprint": validation_fingerprint,
            "sample_count": int(validation.labels.size),
            "threshold": THRESHOLD,
            "metrics": metric_summary(metrics, quality, ece["expected_calibration_error"]),
            "confusion_matrix": metrics["confusion_matrix"],
            "probability_vector_sha256": stable_json_sha256_local(
                {
                    "sample_ids": validation.sample_ids,
                    "probabilities": [float(x) for x in probabilities],
                }
            ),
        },
        "_probabilities": probabilities,
        "_predictions": predictions,
    }


def metric_value(arm_result: Mapping[str, Any], metric: str) -> float:
    return float(arm_result["validation"]["metrics"][metric])


def aggregate_metrics(seed_results: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    all_keys = (
        "accuracy",
        "balanced_accuracy",
        "precision_occupied",
        "recall_occupied",
        "f1_occupied",
        "precision_vacant",
        "recall_vacant",
        "f1_vacant",
        "macro_f1",
        *PROBABILITY_METRICS,
        "expected_calibration_error",
    )
    output: Dict[str, Any] = {}
    for key in all_keys:
        values = np.asarray([metric_value(row, key) for row in seed_results], dtype=np.float64)
        output[key] = {
            "mean": float(values.mean()),
            "std": float(values.std(ddof=0)),
            "min": float(values.min()),
            "max": float(values.max()),
        }
    return output


def seed_win_table(
    arm_a: Sequence[Mapping[str, Any]], arm_b: Sequence[Mapping[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    keys = (
        "accuracy",
        "macro_f1",
        "precision_occupied",
        "recall_occupied",
        *PROBABILITY_METRICS,
    )
    table: Dict[str, Dict[str, Any]] = {}
    for key in keys:
        deltas = [metric_value(a, key) - metric_value(b, key) for a, b in zip(arm_a, arm_b)]
        direction = "LOWER_IS_BETTER" if key in LOWER_IS_BETTER_METRICS else "HIGHER_IS_BETTER"
        better_direction_deltas = [-delta for delta in deltas] if direction == "LOWER_IS_BETTER" else deltas
        table[key] = {
            "direction": direction,
            "a_better": int(sum(delta > 0.0 for delta in better_direction_deltas)),
            "b_better": int(sum(delta < 0.0 for delta in better_direction_deltas)),
            "ties": int(sum(delta == 0.0 for delta in better_direction_deltas)),
            "seed_count": len(deltas),
        }
    return table


def bootstrap_metric_row(y: np.ndarray, predictions: np.ndarray) -> Dict[str, float]:
    y = np.asarray(y, dtype=np.int64)
    p = np.asarray(predictions, dtype=np.int64)
    tp = int(np.sum((y == 1) & (p == 1)))
    tn = int(np.sum((y == 0) & (p == 0)))
    fp = int(np.sum((y == 0) & (p == 1)))
    fn = int(np.sum((y == 1) & (p == 0)))

    def div(numerator: float, denominator: float) -> float:
        return float(numerator / denominator) if denominator else 0.0

    precision_occ = div(tp, tp + fp)
    recall_occ = div(tp, tp + fn)
    precision_vac = div(tn, tn + fn)
    recall_vac = div(tn, tn + fp)
    f1_occ = div(2.0 * precision_occ * recall_occ, precision_occ + recall_occ)
    f1_vac = div(2.0 * precision_vac * recall_vac, precision_vac + recall_vac)
    return {
        "accuracy": div(tp + tn, y.size),
        "macro_f1": (f1_occ + f1_vac) / 2.0,
        "precision_occupied": precision_occ,
        "recall_occupied": recall_occ,
    }


def paired_bootstrap(
    labels: np.ndarray,
    arm_a: Sequence[Mapping[str, Any]],
    arm_b: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    if len(arm_a) != len(SEED_LIST) or len(arm_b) != len(SEED_LIST):
        raise DecisionAuditError("Bootstrap seed coverage mismatch")
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    indices = rng.integers(
        0, labels.size, size=(BOOTSTRAP_REPLICATES, labels.size), dtype=np.int64
    )
    per_seed: Dict[str, Dict[str, Any]] = {}
    aggregate_deltas = {key: np.zeros(BOOTSTRAP_REPLICATES, dtype=np.float64) for key in BOOTSTRAP_METRICS}
    for seed, result_a, result_b in zip(SEED_LIST, arm_a, arm_b):
        deltas = {key: np.empty(BOOTSTRAP_REPLICATES, dtype=np.float64) for key in BOOTSTRAP_METRICS}
        probs_a = result_a["_probabilities"]
        probs_b = result_b["_probabilities"]
        pred_a = result_a["_predictions"]
        pred_b = result_b["_predictions"]
        for replicate, sample_indices in enumerate(indices):
            y_sample = labels[sample_indices]
            metrics_a = bootstrap_metric_row(y_sample, pred_a[sample_indices])
            metrics_b = bootstrap_metric_row(y_sample, pred_b[sample_indices])
            for key in BOOTSTRAP_METRICS:
                deltas[key][replicate] = metrics_a[key] - metrics_b[key]
        for key in BOOTSTRAP_METRICS:
            aggregate_deltas[key] += deltas[key] / len(SEED_LIST)
        per_seed[str(seed)] = {
            "replicates": BOOTSTRAP_REPLICATES,
            "paired_validation_rows": True,
            "delta_intervals": {
                key: {
                    "mean": float(np.mean(values)),
                    "lower_2_5": float(np.percentile(values, BOOTSTRAP_PERCENTILES[0])),
                    "upper_97_5": float(np.percentile(values, BOOTSTRAP_PERCENTILES[1])),
                }
                for key, values in deltas.items()
            },
        }
    return {
        "method": "PAIRED_NONPARAMETRIC_BOOTSTRAP_OVER_VALIDATION_ROWS",
        "seed": BOOTSTRAP_SEED,
        "replicates": BOOTSTRAP_REPLICATES,
        "percentiles": list(BOOTSTRAP_PERCENTILES),
        "validation_population_count": int(labels.size),
        "paired_validation_rows": True,
        "locked_test_used": False,
        "per_seed": per_seed,
        "aggregate_mean_delta_intervals": {
            key: {
                "mean": float(np.mean(values)),
                "lower_2_5": float(np.percentile(values, BOOTSTRAP_PERCENTILES[0])),
                "upper_97_5": float(np.percentile(values, BOOTSTRAP_PERCENTILES[1])),
            }
            for key, values in aggregate_deltas.items()
        },
    }


def disagreement_summary(
    labels: np.ndarray,
    arm_a: Sequence[Mapping[str, Any]],
    arm_b: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    per_seed: Dict[str, Any] = {}
    for seed, result_a, result_b in zip(SEED_LIST, arm_a, arm_b):
        pred_a = result_a["_predictions"]
        pred_b = result_b["_predictions"]
        correct_a = pred_a == labels
        correct_b = pred_b == labels
        disagree = pred_a != pred_b
        categories = {
            "a_correct_b_wrong": correct_a & ~correct_b,
            "b_correct_a_wrong": correct_b & ~correct_a,
            "both_correct": correct_a & correct_b,
            "both_wrong": ~correct_a & ~correct_b,
        }
        per_seed[str(seed)] = {
            "disagreement_count": int(np.sum(disagree)),
            "disagreement_rate": float(np.mean(disagree)),
            "a_correct_b_wrong": int(np.sum(categories["a_correct_b_wrong"])),
            "b_correct_a_wrong": int(np.sum(categories["b_correct_a_wrong"])),
            "both_correct": int(np.sum(categories["both_correct"])),
            "both_wrong": int(np.sum(categories["both_wrong"])),
            "disagreement_true_class": {
                "VACANT": int(np.sum(disagree & (labels == 0))),
                "OCCUPIED": int(np.sum(disagree & (labels == 1))),
            },
            "category_true_class": {
                name: {
                    "VACANT": int(np.sum(mask & (labels == 0))),
                    "OCCUPIED": int(np.sum(mask & (labels == 1))),
                }
                for name, mask in categories.items()
            },
        }
    rates = [row["disagreement_rate"] for row in per_seed.values()]
    return {
        "population": "VALIDATION",
        "per_seed": per_seed,
        "mean_disagreement_rate": float(np.mean(rates)),
        "min_disagreement_rate": float(np.min(rates)),
        "max_disagreement_rate": float(np.max(rates)),
    }


def apply_predeclared_decision_rule(
    arm_a: Sequence[Mapping[str, Any]],
    arm_b: Sequence[Mapping[str, Any]],
    wins: Mapping[str, Mapping[str, Any]],
    bootstrap: Mapping[str, Any],
) -> Tuple[str, Dict[str, Any]]:
    """Apply the rule fixed before the new seed results are calculated."""

    seed_count = len(SEED_LIST)
    required_wins = 4
    aggregate_ci = bootstrap["aggregate_mean_delta_intervals"]
    keep_checks = {
        "macro_f1_a_wins_at_least_4_of_5": wins["macro_f1"]["a_better"] >= required_wins,
        "accuracy_a_wins_at_least_4_of_5": wins["accuracy"]["a_better"] >= required_wins,
        "occupied_precision_a_wins_at_least_4_of_5": wins["precision_occupied"]["a_better"] >= required_wins,
        "occupied_recall_not_lost_in_more_than_1_of_5": wins["recall_occupied"]["b_better"] <= 1,
        "paired_macro_f1_lower_bound_above_zero": aggregate_ci["macro_f1"]["lower_2_5"] > 0.0,
        "paired_accuracy_lower_bound_above_zero": aggregate_ci["accuracy"]["lower_2_5"] > 0.0,
        "paired_occupied_precision_lower_bound_above_zero": aggregate_ci["precision_occupied"]["lower_2_5"] > 0.0,
        "paired_occupied_recall_lower_bound_nonnegative": aggregate_ci["recall_occupied"]["lower_2_5"] >= 0.0,
        "pr_auc_a_wins_or_ties_in_at_least_4_of_5": wins["pr_auc_average_precision"]["a_better"] + wins["pr_auc_average_precision"]["ties"] >= required_wins,
        "roc_auc_a_wins_or_ties_in_at_least_4_of_5": wins["roc_auc"]["a_better"] + wins["roc_auc"]["ties"] >= required_wins,
        "brier_a_wins_or_ties_in_at_least_4_of_5": wins["brier_score"]["a_better"] + wins["brier_score"]["ties"] >= required_wins,
        "log_loss_a_wins_or_ties_in_at_least_4_of_5": wins["log_loss"]["a_better"] + wins["log_loss"]["ties"] >= required_wins,
    }
    if all(keep_checks.values()):
        decision = "KEEP_FOUR_FEATURE_CONTRACT"
    else:
        decision = "ADOPT_REDUCED_FEATURE_DIRECTION"
    return decision, {
        "decision_rule_id": "BURDEN_OF_PROOF_DIRECTIONAL_REPEATABILITY_GATE_001",
        "required_seed_count": seed_count,
        "required_wins_for_repeatability": required_wins,
        "keep_four_feature_only_if_all_checks_pass": True,
        "checks": keep_checks,
        "fallback_if_keep_checks_fail": "ADOPT_REDUCED_FEATURE_DIRECTION",
        "effect_size_threshold": None,
        "statistical_significance_claim": False,
        "practical_equivalence_claim": False,
    }


def strip_internal(result: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in result.items() if not key.startswith("_")}


def build_result(root: Path, team_main_sha: str) -> Dict[str, Any]:
    if len(SEED_LIST) != len(set(SEED_LIST)) or tuple(sorted(SEED_LIST)) != SEED_LIST:
        raise DecisionAuditError("Seed list is not fixed, unique, and ordered")
    predecessor = validate_predecessor(root)
    eligible = load_ordered_eligible_ids(root)
    bundles, loading = load_guarded_matrices(root, eligible)
    train = bundles["TRAIN"]
    validation = bundles["VALIDATION"]
    train_fp = ordered_id_list_sha256(train.sample_ids)
    validation_fp = ordered_id_list_sha256(validation.sample_ids)
    if train_fp != EXPECTED_TRAIN_FINGERPRINT or validation_fp != EXPECTED_VALIDATION_FINGERPRINT:
        raise DecisionAuditError("TRAIN/VALIDATION fingerprint drift")
    if loading["locked_test_feature_rows_decoded"] != 0 or loading["locked_test_target_rows_decoded"] != 0:
        raise DecisionAuditError("LOCKED_TEST feature/target access detected")
    if loading["locked_test_predictive_metrics"] != 0 or loading["locked_test_accessed_for_selection"]:
        raise DecisionAuditError("LOCKED_TEST predictive/selection access detected")

    b5 = load_json(root / "models/co2/candidates/c_b5/final_candidate_metadata.json")
    b5_metadata_rel = "models/co2/candidates/c_b5/final_candidate_metadata.json"
    if b5["feature_order"] != list(FULL_FEATURES):
        raise DecisionAuditError("B5 feature order drift")
    if float(b5["threshold"]) != THRESHOLD:
        raise DecisionAuditError("B5 threshold drift")
    if b5["scaler_identity"]["fingerprint"] != EXPECTED_B5_SCALER_FINGERPRINT:
        raise DecisionAuditError("B5 scaler fingerprint drift")
    if b5["model_sha256"] != EXPECTED_B5_MODEL_SHA256:
        raise DecisionAuditError("B5 model fingerprint drift")

    arm_train = {
        arm: subset_bundle(train, features) for arm, features in ARM_FEATURES.items() if arm in ("A", "B")
    }
    arm_validation = {
        arm: subset_bundle(validation, features) for arm, features in ARM_FEATURES.items() if arm in ("A", "B")
    }
    arm_results: Dict[str, list[Dict[str, Any]]] = {"A": [], "B": []}
    oversampling: Dict[str, Any] = {}
    for seed in SEED_LIST:
        plan = build_seeded_oversample_plan(train.labels, train.sample_ids, seed)
        oversampling[str(seed)] = plan["evidence"]
        for arm in ("A", "B"):
            arm_results[arm].append(
                run_arm(
                    seed,
                    arm,
                    arm_train[arm],
                    arm_validation[arm],
                    train_fp,
                    validation_fp,
                    plan["training_indices"],
                )
            )

    # Confirm the historical seed reproduces the previous arm-A scaler and
    # baseline validation metrics before using any new aggregate decision.
    if arm_results["A"][0]["scaler"]["scaler_fingerprint"] != EXPECTED_B5_SCALER_FINGERPRINT:
        raise DecisionAuditError("Seed 20260810 arm-A scaler drift")
    wins = seed_win_table(arm_results["A"], arm_results["B"])
    bootstrap = paired_bootstrap(validation.labels, arm_results["A"], arm_results["B"])
    disagreement = disagreement_summary(validation.labels, arm_results["A"], arm_results["B"])
    decision, decision_logic = apply_predeclared_decision_rule(
        arm_results["A"], arm_results["B"], wins, bootstrap
    )

    a_clean = [strip_internal(row) for row in arm_results["A"]]
    b_clean = [strip_internal(row) for row in arm_results["B"]]
    a_aggregate = aggregate_metrics(arm_results["A"])
    b_aggregate = aggregate_metrics(arm_results["B"])
    delta_aggregate = {
        key: {
            "mean": a_aggregate[key]["mean"] - b_aggregate[key]["mean"],
            "std": float(np.sqrt(a_aggregate[key]["std"] ** 2 + b_aggregate[key]["std"] ** 2)),
            "a_mean": a_aggregate[key]["mean"],
            "b_mean": b_aggregate[key]["mean"],
        }
        for key in a_aggregate
    }

    result = {
        "manifest_version": "1.0",
        "decision_profile_id": AUDIT_ID,
        "predecessor_feature_audit_id": predecessor["audit_id"],
        "predecessor_pr_78_result": predecessor,
        "repository": {
            "standalone_main_sha": git_sha(root, "origin/main"),
            "audit_execution_base": git_sha(root, "HEAD"),
            "team_main_sha": team_main_sha,
            "pr_78_merge_commit": "266151d12a1e4b144d5a6f2bae28dda72f939cc5",
            "team_repository_read_only": True,
        },
        "dataset_lineage": {
            "train_count": int(train.features.shape[0]),
            "validation_count": int(validation.features.shape[0]),
            "locked_test_count": len(eligible["LOCKED_TEST"]),
            "train_fingerprint": train_fp,
            "validation_fingerprint": validation_fp,
            "locked_test_fingerprint": EXPECTED_LOCKED_TEST_FINGERPRINT,
            "canonical_source_sha256": loading["canonical_source_sha256"],
            "source_archive_sha256_values": loading["source_archive_sha256_values"],
            "synthetic_fixture_used": False,
            "random_row_split_used": False,
            "split_reused_without_resplitting": True,
        },
        "locked_test_access": {
            "feature_rows_decoded": loading["locked_test_feature_rows_decoded"],
            "target_rows_decoded": loading["locked_test_target_rows_decoded"],
            "predictive_metrics": loading["locked_test_predictive_metrics"],
            "selection_usage": 0,
            "model_selection_usage": 0,
            "membership_rows_seen": loading["locked_test_eligible_rows_seen"],
            "sealed": True,
        },
        "arm_a_features": list(ARM_FEATURES["A"]),
        "arm_b_features": list(ARM_FEATURES["B"]),
        "fixed_training_contract": {
            "slope_profile": "ENDPOINT_H150",
            "history_duration_seconds": 150.0,
            "max_internal_gap_seconds": 90.0,
            "causality": "PAST_ONLY",
            "scaler_fit_population": "ORIGINAL_TRAIN_ONLY",
            "imbalance_strategy": "BALANCED_RANDOM_OVERSAMPLE",
            "model_family": "B2_FIXED_LOGISTIC_PROBE_001",
            "model_parameters": MODEL_PARAMETERS,
            "threshold": THRESHOLD,
            "threshold_policy": "FROZEN_0.58_INHERITED_FROM_B5; NOT_RETUNED",
            "validation_population_only_for_decision": True,
            "feature_search": False,
            "hyperparameter_search": False,
            "slope_redesign": False,
            "resplitting": False,
        },
        "seed_list": list(SEED_LIST),
        "oversampling_by_seed": oversampling,
        "per_seed_results": {"A": a_clean, "B": b_clean},
        "aggregate_results": {
            "A": a_aggregate,
            "B": b_aggregate,
            "A_minus_B": delta_aggregate,
            "seed_win_table": wins,
        },
        "bootstrap": bootstrap,
        "prediction_disagreement": disagreement,
        "burden_of_proof_policy": {
            "original_design_prior": "ORIGINAL_SAFE_NEST_CO2_DESIGN_CO2_CENTRIC",
            "new_required_fields_burden": "FOUR_FEATURE_DESIGN",
            "rule": "KEEP_T_RH_ONLY_IF_CLEAR_REPRODUCIBLE_DIRECTIONAL_BENEFIT_JUSTIFIES_ADDED_DEVICE_CONTRACT_FIELDS",
            "t_rh_zero_information_claim": False,
            "network_cost_as_necessity_evidence": False,
        },
        "interpretation": {
            "four_feature_predictive_benefit_observed": True,
            "reduced_feature_predictive_superiority_established": False,
            "occupied_recall_tradeoff_observed": True,
            "occupied_recall_comparison_threshold": THRESHOLD,
            "occupied_recall_advantage_threshold_conditioned": True,
            "threshold_origin": "CURRENT_FOUR_FEATURE_B5_LINEAGE",
            "reduced_feature_threshold_not_finalized": True,
            "t_rh_zero_information_claim": False,
        },
        "decision_basis": {
            "type": "SYSTEM_CONTRACT_BURDEN_OF_PROOF",
            "not_model_superiority_ranking": True,
            "original_system_direction": "CO2_CENTRIC",
            "mandatory_trh_fields_justification_not_met": True,
        },
        "decision_logic": decision_logic,
        "final_decision": decision,
        "b5": {
            "modified": False,
            "feature_order": b5["feature_order"],
            "threshold": b5["threshold"],
            "model_sha256": b5["model_sha256"],
            "scaler_fingerprint": b5["scaler_identity"]["fingerprint"],
            "candidate_status": b5["candidate_status"],
            "metadata_path": b5_metadata_rel,
            "metadata_sha256": file_sha256(root / b5_metadata_rel),
            "model_artifact_modified": False,
            "scaler_artifact_modified": False,
        },
        "physical_acquisition_status": (
            "AUTHORIZED_AFTER_FINAL_PROTOCOL_CHECK"
            if decision == "KEEP_FOUR_FEATURE_CONTRACT"
            else "HOLD_PENDING_REDUCED_FEATURE_CANDIDATE_LOCK"
        ),
        "operator_guide_handoff": (
            "READY_FOR_HANDOFF"
            if decision == "KEEP_FOUR_FEATURE_CONTRACT"
            else "HOLD"
        ),
        "c_c2_started": False,
        "formal_device_domain_validation": False,
        "new_physical_measurement": False,
        "status_boundary": {
            "physical_acquisition_status": (
                "AUTHORIZED_AFTER_FINAL_PROTOCOL_CHECK"
                if decision == "KEEP_FOUR_FEATURE_CONTRACT"
                else "HOLD_PENDING_REDUCED_FEATURE_CANDIDATE_LOCK"
            ),
            "operator_handoff_status": (
                "READY_FOR_HANDOFF"
                if decision == "KEEP_FOUR_FEATURE_CONTRACT"
                else "HOLD"
            ),
            "c_c2_started": False,
            "formal_device_domain_validation": False,
            "new_physical_measurement": False,
        },
        "next_phase": {
            "phase_id": NEXT_PHASE_ID,
            "title": NEXT_PHASE_TITLE,
            "authorization_required": True,
            "physical_acquisition_before_lock": False,
            "c_c2_before_lock": False,
        },
        "recommended_next_phase": (
            "EXTERNAL_PROTOCOL_CONTROLLED_ACQUISITION_AFTER_C_C1_FINAL_PROTOCOL_CHECK"
            if decision == "KEEP_FOUR_FEATURE_CONTRACT"
            else "C-B6_REDUCED_FEATURE_CANDIDATE_DEVELOPMENT_AND_LOCK_BEFORE_PROTOCOL_REVISION"
        ),
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--team-main-sha", required=True)
    args = parser.parse_args()
    result = build_result(ROOT, args.team_main_sha)
    output = ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "output": args.output,
                "decision": result["final_decision"],
                "audit_execution_base": result["repository"]["audit_execution_base"],
                "locked_test_predictive_metrics": result["locked_test_access"]["predictive_metrics"],
                "seed_count": len(result["seed_list"]),
                "bootstrap_replicates": result["bootstrap"]["replicates"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
