#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest

import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_ROOT = REPO_ROOT / "devices/mmwave/tools"
for search_path in (REPO_ROOT, TOOLS_ROOT):
    if str(search_path) not in sys.path:
        sys.path.insert(0, str(search_path))

from mmwave_v5_replay_benchmark import (
    DatasetSpec,
    benchmark_dataset,
    entry_exit_metrics,
    quality_metrics,
)
from devices.mmwave.src.mr60_esp_adapter import MR60ESPAdapter


EXPECTED_HASH = "b817e8bfd5e52b18275626f7b6a9bd60098ea4b108428a5aaf63600dbc987834"


class FakeInterpreter:
    model_meta = {"model_id": "mmwave_resp_int8", "version": "0.1.0"}
    sha256_hash = "a" * 64
    sha256_matches = True

    def __init__(self) -> None:
        self.calls = 0

    def predict(self, window):
        array = np.asarray(window)
        if array.shape != (300,):
            raise AssertionError(array.shape)
        self.calls += 1
        return SimpleNamespace(
            model_id="mmwave_resp_int8",
            model_version="0.1.0",
            class_index=0,
            class_name="NORMAL",
            confidence=0.875,
            probabilities=[0.875, 0.1, 0.025],
            latency_ms=1.25,
            fallback_used=False,
            fallback_reason=None,
        )


def sensor_record(index: int, *, schema="1.2", present=True, **overrides):
    timestamp_s = index / 10.0
    item = {
        "schema_version": schema,
        "firmware_version": "safenest-mr60-esp/1.2.0" if schema == "1.2" else None,
        "config_hash": EXPECTED_HASH if schema == "1.2" else None,
        "seq": index,
        "ts_monotonic_ms": int(timestamp_s * 1000),
        "uart_frame_ok": True,
        "checksum_ok": True,
        "checksum_errors": 0,
        "parse_errors": 0,
        "human_detected_raw": present,
        "human_detected_stable": present,
        "distance_cm_raw": 80.0 if present else None,
        "breath_phase": float(np.sin(2 * np.pi * 0.25 * timestamp_s)) if present else 0.0,
        "phase_age_ms": 10,
        "heart_rate_raw": 70.0 if present else 0.0,
        "heart_age_ms": 10,
        "sensor_state": "RAW" if present else "UNKNOWN",
        "kind": "sensor",
        "host_monotonic_ns": index * 100_000_000,
    }
    item.update(overrides)
    return item


def write_jsonl(path: Path, records) -> None:
    path.write_text(
        "".join(json.dumps(item, allow_nan=False) + "\n" for item in records),
        encoding="utf-8",
    )


class TestReplayBenchmark(unittest.TestCase):
    def run_dataset(self, records, **spec_overrides):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "source.jsonl"
            write_jsonl(path, records)
            spec = DatasetSpec(
                id="test",
                path=path,
                scenario="test",
                classification="REAL_REPLAY_READY",
                strict_provenance=spec_overrides.pop("strict_provenance", True),
                **spec_overrides,
            )
            interpreter = FakeInterpreter()
            summary, windows = benchmark_dataset(
                spec, interpreter, git_commit="test-commit"
            )
            return summary, windows, interpreter.calls

    def test_schema_1_2_strict_uses_same_adapter_and_real_window_contract(self):
        records = [sensor_record(index) for index in range(900)]
        summary, windows, calls = self.run_dataset(
            records,
            presence_ground_truth="PRESENT",
            ai_class_ground_truth="NORMAL",
            analysis_start_s=60.0,
            analysis_duration_s=30.0,
        )
        self.assertEqual(summary["completed_windows"], 1)
        self.assertEqual(summary["tflite_runs"], 1)
        self.assertEqual(summary["fallback_count"], 0)
        self.assertEqual(summary["classification_accuracy"], 1.0)
        self.assertEqual(windows[0]["window_samples"], 300)
        self.assertEqual(calls, 1)

    def test_schema_1_0_existing_compatibility_mode(self):
        records = [sensor_record(index, schema="1.0") for index in range(900)]
        summary, _, calls = self.run_dataset(
            records,
            strict_provenance=False,
            presence_ground_truth="PRESENT",
            analysis_start_s=60.0,
            analysis_duration_s=30.0,
        )
        self.assertFalse(summary["strict_provenance"])
        self.assertEqual(summary["analysis_quality"]["schema_versions"], {"1.0": 300})
        self.assertEqual(summary["completed_windows"], 1)
        self.assertEqual(calls, 1)

    def test_empty_space_never_produces_normal_or_apnea(self):
        records = [sensor_record(index, present=False) for index in range(700)]
        summary, windows, calls = self.run_dataset(
            records,
            presence_ground_truth="ABSENT",
        )
        self.assertEqual(summary["presence"]["false_presence_rate"], 0.0)
        self.assertEqual(summary["attempted_windows"], 0)
        self.assertEqual(summary["completed_windows"], 0)
        self.assertEqual(summary["prediction_distribution"], {})
        self.assertEqual(windows, [])
        self.assertEqual(calls, 0)
        self.assertEqual(summary["result"], "PASS")

    def test_respiration_rate_truth_is_not_ai_class_truth(self):
        records = [sensor_record(index) for index in range(900)]
        summary, _, _ = self.run_dataset(
            records,
            presence_ground_truth="PRESENT",
            reference_respiration_rpm=15.0,
            analysis_start_s=60.0,
            analysis_duration_s=30.0,
        )
        self.assertIsNone(summary["ai_class_ground_truth"])
        self.assertIsNone(summary["classification_accuracy"])
        self.assertIn("분류 정확도를 계산하지 않았습니다", summary["classification_accuracy_note"])
        self.assertIsNotNone(summary["respiration_rate"]["mae_rpm"])

    def test_quality_counts_gap_drop_and_stale_without_fabrication(self):
        records = [sensor_record(0), sensor_record(1), sensor_record(8, phase_age_ms=600)]
        quality = quality_metrics(records, MR60ESPAdapter().config)
        self.assertEqual(quality["sequence_drops"], 6)
        self.assertEqual(quality["stream_gap_count"], 1)
        self.assertEqual(quality["stale_phase_records"], 1)
        self.assertEqual(quality["breath_phase_finite"], 3)
        self.assertEqual(quality["breath_phase_usable"], 2)

    def test_entry_exit_ground_truth_metrics_preserve_vendor_hysteresis(self):
        records = []
        for index in range(250):
            present = 10 <= index < 170
            records.append(sensor_record(index, present=present))
        records.extend([
            {"kind": "beep", "event": "enter", "trial": 1, "host_monotonic_ns": 0},
            {"kind": "beep", "event": "exit", "trial": 1, "host_monotonic_ns": 2_000_000_000},
        ])
        metrics = entry_exit_metrics(records)
        self.assertIsNotNone(metrics)
        self.assertEqual(metrics["entry_success"], 1)
        self.assertEqual(metrics["exit_release_success"], 1)
        self.assertGreater(metrics["exit_latency_s"]["p50"], 10.0)
        self.assertTrue(metrics["vendor_hysteresis_dominates"])


if __name__ == "__main__":
    unittest.main()
