#!/usr/bin/env python3
"""Benchmark the locked int8 TFLite model on existing offline CSV windows."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from collections import Counter
from pathlib import Path

import numpy as np
import tensorflow as tf
from scipy.signal import butter

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
from offline_pipeline_audit import iter_windows, preprocess_window  # noqa: E402


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def percentile(values: list[float], p: float) -> float:
    return float(np.percentile(np.asarray(values, dtype=np.float64), p))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--warmup", type=int, default=10)
    args = parser.parse_args()

    csv_paths = sorted(args.csv_dir.glob("*.csv"))
    windows = []
    for path in csv_paths:
        windows.extend(iter_windows(path))
    if not windows:
        raise SystemExit("no CSV windows found")

    b, a = butter(4, [0.1 / 5.0, 0.5 / 5.0], btype="bandpass")
    preprocessed = []
    source_labels = []
    for item in windows:
        output, quality = preprocess_window(
            item["values"],
            mean=0.0031162832173884064,
            std=2.955399434649939,
            b=b,
            a=a,
        )
        if not quality["valid"]:
            raise SystemExit(f"unexpected invalid preprocessing: {quality}")
        preprocessed.append(output)
        source_labels.append(item["label"])
    float_batch = np.concatenate(preprocessed, axis=0).astype(np.float32)

    interpreter = tf.lite.Interpreter(model_path=str(args.model), num_threads=1)
    interpreter.allocate_tensors()
    input_info = interpreter.get_input_details()[0]
    output_info = interpreter.get_output_details()[0]
    input_scale, input_zero_point = input_info["quantization"]
    output_scale, output_zero_point = output_info["quantization"]
    input_unbounded = np.rint(float_batch / input_scale) + input_zero_point
    input_saturated = (input_unbounded < -128) | (input_unbounded > 127)
    input_batch = np.clip(input_unbounded, -128, 127).astype(input_info["dtype"])

    def invoke_one(sample: np.ndarray) -> np.ndarray:
        interpreter.set_tensor(input_info["index"], sample[None, ...])
        interpreter.invoke()
        return interpreter.get_tensor(output_info["index"]).copy()

    warmup_count = min(max(args.warmup, 0), len(input_batch))
    for sample in input_batch[:warmup_count]:
        invoke_one(sample)

    latencies_ms = []
    outputs = []
    for sample in input_batch:
        start_ns = time.perf_counter_ns()
        output = invoke_one(sample)
        latencies_ms.append((time.perf_counter_ns() - start_ns) / 1_000_000.0)
        outputs.append(output[0])
    output_q = np.stack(outputs).astype(np.int8)
    output_float = (output_q.astype(np.float32) - output_zero_point) * output_scale
    predictions = np.argmax(output_float, axis=1)
    class_map = {0: "NORMAL", 1: "RAPID_OR_ABNORMAL", 2: "APNEA"}
    prediction_by_source_label = {}
    for source_label in sorted(set(source_labels)):
        mask = np.asarray([label == source_label for label in source_labels])
        prediction_by_source_label[source_label] = {
            class_map[i]: int(np.sum(predictions[mask] == i)) for i in range(3)
        }

    result = {
        "runtime": {"tensorflow": tf.__version__, "threads": 1},
        "model": {
            "path": str(args.model),
            "sha256": sha256(args.model),
            "input_name": input_info["name"],
            "input_shape": input_info["shape"].tolist(),
            "input_dtype": str(input_info["dtype"]),
            "input_scale": float(input_scale),
            "input_zero_point": int(input_zero_point),
            "output_name": output_info["name"],
            "output_shape": output_info["shape"].tolist(),
            "output_dtype": str(output_info["dtype"]),
            "output_scale": float(output_scale),
            "output_zero_point": int(output_zero_point),
        },
        "dataset": {
            "csv_files": len(csv_paths),
            "windows": len(windows),
            "preprocessed_shape": list(float_batch.shape),
            "source_label_counts": dict(Counter(str(label) for label in source_labels)),
            "label_alignment": "NOT_COMPUTED_CSV_LABELS_ARE_NOT_MODEL_CLASS_GROUND_TRUTH",
        },
        "input_quantization": {
            "saturation_ratio": float(np.mean(input_saturated)),
            "quantized_min": int(np.min(input_batch)),
            "quantized_max": int(np.max(input_batch)),
        },
        "inference": {
            "classification": "EXPLORATORY_PRE_CORRESPONDENCE_INFERENCE",
            "warning_classifications": [
                "PIPELINE_CORRESPONDENCE_WARNING",
                "DEVICE_DOMAIN_MISMATCH_WARNING",
            ],
            "m_c0_correspondence_complete": False,
            "m_c2_complete": False,
            "clinical_apnea_evidence": False,
            "single_root_cause_claimed": False,
            "invoke_count": len(input_batch),
            "warmup_count": warmup_count,
            "all_invokes_completed": True,
            "latency_ms": {
                "mean": float(np.mean(latencies_ms)),
                "median_p50": percentile(latencies_ms, 50),
                "p95": percentile(latencies_ms, 95),
                "min": float(np.min(latencies_ms)),
                "max": float(np.max(latencies_ms)),
            },
            "prediction_counts": {class_map[i]: int(np.sum(predictions == i)) for i in range(3)},
            "prediction_counts_by_source_label": prediction_by_source_label,
            "output_quantized_min": int(np.min(output_q)),
            "output_quantized_max": int(np.max(output_q)),
            "output_float_min": float(np.min(output_float)),
            "output_float_max": float(np.max(output_float)),
            "output_float_mean": float(np.mean(output_float)),
        },
        "performance_metrics": {
            "accuracy": None,
            "macro_f1": None,
            "recall": None,
            "confusion_matrix": None,
            "reason": "No independent ground-truth labels aligned to NORMAL/RAPID_OR_ABNORMAL/APNEA were available in this CSV delivery.",
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
