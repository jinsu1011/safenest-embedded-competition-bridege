#!/usr/bin/env python3

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_ROOT = REPO_ROOT / "devices" / "mmwave" / "tools"
for path in (REPO_ROOT, TOOLS_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from mmwave_performance_monitor import (
    SessionMetrics,
    StreamMetrics,
    build_event,
    latency_stats,
    progress_bar,
    sparkline,
    summary_event,
)


class FakeResult:
    def __init__(self, *, valid=False, error="MMWAVE_WARMUP", latency_ms=100.0, metadata=None):
        self.valid = valid
        self.error = error
        self.latency_ms = latency_ms
        self.metadata = metadata or {}
        self.state = "NORMAL" if valid else "WARMUP"
        self.confidence = 0.9 if valid else 0.0

    def to_dict(self):
        return {
            "sensor_id": "mmwave",
            "state": self.state,
            "valid": self.valid,
            "error": self.error,
            "metadata": self.metadata,
        }


def record(seq: int, timestamp_ms: int, **overrides):
    item = {
        "seq": seq,
        "ts_monotonic_ms": timestamp_ms,
        "uart_frame_ok": True,
        "checksum_ok": True,
        "checksum_errors": 2,
        "parse_errors": 3,
        "human_detected_stable": True,
        "breath_phase": 0.1,
    }
    item.update(overrides)
    return (json.dumps(item) + "\n").encode()


class TestStreamMetrics(unittest.TestCase):
    def test_tracks_rate_drops_errors_and_real_phase_only(self):
        metrics = StreamMetrics()
        metrics.observe(record(10, 1000, breath_phase=-1.0))
        metrics.observe(record(12, 1100, checksum_errors=4, parse_errors=4, breath_phase=None))
        metrics.observe(record(13, 1200, uart_frame_ok=False, checksum_ok=False, human_detected_stable=False))
        self.assertEqual(metrics.records, 3)
        self.assertEqual(metrics.dropped_sequences, 1)
        self.assertEqual(metrics.uart_failures, 1)
        self.assertEqual(metrics.checksum_failures, 1)
        self.assertEqual(metrics.checksum_error_delta, 2)
        self.assertEqual(metrics.parse_error_delta, 1)
        self.assertEqual(metrics.invalid_phase, 1)
        self.assertEqual(metrics.presence_loss_records, 1)
        self.assertAlmostEqual(metrics.effective_rate_hz, 10.0)
        self.assertAlmostEqual(metrics.max_gap_s, 0.1)
        self.assertEqual(list(metrics.phases), [-1.0, 0.1])

    def test_invalid_json_is_counted_without_fake_point(self):
        metrics = StreamMetrics()
        metrics.observe(b"not-json\n")
        self.assertEqual(metrics.json_errors, 1)
        self.assertEqual(metrics.records, 0)
        self.assertEqual(sparkline(metrics.phases), "(유효한 breath_phase 없음)")
        summary = summary_event(SessionMetrics("unlabeled", None, None), metrics)
        self.assertEqual(summary["host_json_errors"], 1)


class TestSessionMetrics(unittest.TestCase):
    def test_independent_completed_window_metrics(self):
        session = SessionMetrics("normal", 80.0, "seated")
        with patch("mmwave_performance_monitor.time.monotonic", side_effect=[10.0, 40.0]):
            warmup = FakeResult()
            self.assertIsNone(session.note_read(warmup, 0, 1))
            valid = FakeResult(
                valid=True,
                error=None,
                latency_ms=103.0,
                metadata={
                    "class_name": "NORMAL",
                    "inference_latency_ms": 2.0,
                    "fallback_used": False,
                },
            )
            self.assertEqual(session.note_read(valid, 299, 300), "completed")
        self.assertEqual(session.attempted_windows, 1)
        self.assertEqual(session.completed_windows, 1)
        self.assertEqual(session.failed_windows, 0)
        self.assertEqual(session.predictions, {"NORMAL": 1})
        self.assertEqual(session.window_durations_s, [30.0])

    def test_reset_and_invalid_boundary_are_failures(self):
        session = SessionMetrics("unlabeled", None, None)
        with patch("mmwave_performance_monitor.time.monotonic", return_value=10.0):
            session.note_read(FakeResult(), 0, 1)
            event = session.note_read(
                FakeResult(error="MMWAVE_PRESENCE_NOT_DETECTED"), 42, 0
            )
        self.assertEqual(event, "failed")
        self.assertEqual(session.failed_windows, 1)
        self.assertEqual(session.reset_reasons["MMWAVE_PRESENCE_NOT_DETECTED"], 1)

    def test_sample_300_warmup_wait_is_not_a_failed_window(self):
        session = SessionMetrics("unlabeled", None, None, 1)
        with patch("mmwave_performance_monitor.time.monotonic", return_value=10.0):
            session.note_read(FakeResult(), 0, 1)
            event = session.note_read(FakeResult(error="MMWAVE_WARMUP"), 299, 300)
        self.assertIsNone(event)
        self.assertTrue(session.active_window)
        self.assertEqual(session.failed_windows, 0)

    def test_full_flat_window_after_warmup_is_terminal_failure(self):
        session = SessionMetrics("no-person", None, None)
        with patch("mmwave_performance_monitor.time.monotonic", return_value=10.0):
            session.note_read(FakeResult(), 0, 1)
            session.note_read(FakeResult(error="MMWAVE_WARMUP"), 299, 300)
            event = session.note_read(
                FakeResult(error="MMWAVE_PHASE_SIGNAL_TOO_FLAT"), 300, 300
            )
        self.assertEqual(event, "failed")
        self.assertEqual(session.failed_windows, 1)
        self.assertEqual(
            session.reset_reasons["MMWAVE_PHASE_SIGNAL_TOO_FLAT"], 1
        )

    def test_summary_never_calls_normal_agreement_accuracy_for_unlabeled(self):
        session = SessionMetrics("unlabeled", None, None)
        stream = StreamMetrics()
        summary = summary_event(session, stream)
        self.assertIsNone(summary["normal_agreement_rate"])

    def test_event_preserves_full_provider_contract_result(self):
        session = SessionMetrics("normal", 70.0, "seated")
        stream = StreamMetrics()
        stream.observe(record(1, 1000))
        result = FakeResult(valid=True, error=None, metadata={"class_name": "NORMAL"})
        event = build_event("window_completed", session, stream, result)
        self.assertEqual(event["provider_result"]["sensor_id"], "mmwave")
        self.assertEqual(event["provider_result"]["state"], "NORMAL")


class TestFormatting(unittest.TestCase):
    def test_percentiles_progress_and_sparkline(self):
        stats = latency_stats([1.0, 2.0, 3.0, 4.0])
        self.assertEqual(stats["mean"], 2.5)
        self.assertEqual(stats["p50"], 2.5)
        self.assertAlmostEqual(stats["p95"], 3.85)
        self.assertEqual(progress_bar(150, 300), "[###############---------------] 150/300")
        graph = sparkline([-1.0, 0.0, 1.0], width=3)
        self.assertEqual(len(graph), 3)
        self.assertNotIn("?", graph)


if __name__ == "__main__":
    unittest.main()
