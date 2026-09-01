#!/usr/bin/env python3
"""Live MR60 -> ESP -> Serial -> V5 TFLite performance monitor.

This is a validation utility, not production inference code.  It observes the
same JSONL bytes consumed by ``MMWaveSensorAdapter`` and reports independent
300-sample trials without altering firmware, model, thresholds, or samples.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Callable, Iterable


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from devices.mmwave.src.mmwave_adapter import MMWaveSensorAdapter


RESET_EXEMPT_ERRORS = {"MMWAVE_WARMUP", "MMWAVE_WINDOW_NOT_READY"}
SPARK_LEVELS = "▁▂▃▄▅▆▇█"


def finite_number(value: object) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def percentile(values: Iterable[float], fraction: float) -> float | None:
    ordered = sorted(float(value) for value in values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def latency_stats(values: Iterable[float]) -> dict[str, float | int | None]:
    samples = [float(value) for value in values]
    if not samples:
        return {"count": 0, "mean": None, "p50": None, "p95": None, "max": None}
    return {
        "count": len(samples),
        "mean": statistics.fmean(samples),
        "p50": percentile(samples, 0.50),
        "p95": percentile(samples, 0.95),
        "max": max(samples),
    }


def sparkline(values: Iterable[float], width: int = 60) -> str:
    points = [float(value) for value in values if finite_number(value)]
    if not points:
        return "(유효한 breath_phase 없음)"
    points = points[-width:]
    low, high = min(points), max(points)
    if math.isclose(low, high, abs_tol=1e-12):
        return SPARK_LEVELS[len(SPARK_LEVELS) // 2] * len(points)
    scale = (len(SPARK_LEVELS) - 1) / (high - low)
    return "".join(SPARK_LEVELS[round((value - low) * scale)] for value in points)


def format_number(value: float | int | None, digits: int = 3) -> str:
    if value is None:
        return "-"
    if isinstance(value, int):
        return str(value)
    return f"{value:.{digits}f}"


def progress_bar(count: int, required: int, width: int = 30) -> str:
    ratio = min(1.0, max(0.0, count / required)) if required else 0.0
    filled = round(width * ratio)
    return "[" + "#" * filled + "-" * (width - filled) + f"] {count}/{required}"


@dataclass
class StreamMetrics:
    records: int = 0
    json_errors: int = 0
    uart_failures: int = 0
    checksum_failures: int = 0
    invalid_phase: int = 0
    dropped_sequences: int = 0
    nonmonotonic_sequences: int = 0
    presence_loss_records: int = 0
    last_record: dict[str, Any] = field(default_factory=dict)
    last_sequence: int | None = None
    last_sensor_time_s: float | None = None
    intervals_s: list[float] = field(default_factory=list)
    phases: deque[float] = field(default_factory=lambda: deque(maxlen=120))
    first_checksum_errors: int | None = None
    last_checksum_errors: int | None = None
    first_parse_errors: int | None = None
    last_parse_errors: int | None = None
    checksum_error_increases: int = 0
    parse_error_increases: int = 0

    def observe(self, raw: bytes | str) -> None:
        try:
            text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
            record = json.loads(text)
        except (UnicodeDecodeError, json.JSONDecodeError, TypeError):
            self.json_errors += 1
            return
        if not isinstance(record, dict):
            self.json_errors += 1
            return

        self.records += 1
        self.last_record = record
        sequence = record.get("seq")
        if isinstance(sequence, int) and not isinstance(sequence, bool):
            if self.last_sequence is not None:
                if sequence > self.last_sequence + 1:
                    self.dropped_sequences += sequence - self.last_sequence - 1
                elif sequence <= self.last_sequence:
                    self.nonmonotonic_sequences += 1
            self.last_sequence = sequence

        timestamp_ms = record.get("ts_monotonic_ms")
        if finite_number(timestamp_ms):
            timestamp_s = float(timestamp_ms) / 1000.0
            if self.last_sensor_time_s is not None and timestamp_s > self.last_sensor_time_s:
                self.intervals_s.append(timestamp_s - self.last_sensor_time_s)
            self.last_sensor_time_s = timestamp_s

        if record.get("uart_frame_ok") is not True:
            self.uart_failures += 1
        if record.get("checksum_ok") is not True:
            self.checksum_failures += 1
        if record.get("human_detected_stable", record.get("human_detected_raw")) is False:
            self.presence_loss_records += 1

        phase = record.get("breath_phase")
        if finite_number(phase):
            self.phases.append(float(phase))
        else:
            self.invalid_phase += 1

        self._observe_counter(record.get("checksum_errors"), "checksum")
        self._observe_counter(record.get("parse_errors"), "parse")

    def _observe_counter(self, value: object, kind: str) -> None:
        if not isinstance(value, int) or isinstance(value, bool):
            return
        first_name = f"first_{kind}_errors"
        last_name = f"last_{kind}_errors"
        increase_name = f"{kind}_error_increases"
        if getattr(self, first_name) is None:
            setattr(self, first_name, value)
        previous = getattr(self, last_name)
        if previous is not None and value > previous:
            setattr(self, increase_name, getattr(self, increase_name) + value - previous)
        setattr(self, last_name, value)

    @property
    def checksum_error_delta(self) -> int:
        return self.checksum_error_increases

    @property
    def parse_error_delta(self) -> int:
        return self.parse_error_increases

    @property
    def effective_rate_hz(self) -> float | None:
        if not self.intervals_s:
            return None
        mean_interval = statistics.fmean(self.intervals_s)
        return 1.0 / mean_interval if mean_interval > 0 else None

    @property
    def max_gap_s(self) -> float | None:
        return max(self.intervals_s) if self.intervals_s else None


class ObservedSerial:
    """Transparent Serial proxy that observes each non-empty provider read."""

    def __init__(self, serial_obj: Any, observer: Callable[[bytes | str], None]) -> None:
        self._serial = serial_obj
        self._observer = observer

    def readline(self) -> Any:
        raw = self._serial.readline()
        if raw:
            self._observer(raw)
        return raw

    def __getattr__(self, name: str) -> Any:
        return getattr(self._serial, name)


@dataclass
class SessionMetrics:
    scenario: str
    distance_cm: float | None
    posture: str | None
    target_windows: int = 0
    started_wall: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_monotonic: float = field(default_factory=time.monotonic)
    attempted_windows: int = 0
    completed_windows: int = 0
    failed_windows: int = 0
    active_window: bool = False
    active_window_started: float | None = None
    reset_reasons: Counter[str] = field(default_factory=Counter)
    insufficient_history_events: int = 0
    stale_events: int = 0
    fallback_count: int = 0
    predictions: Counter[str] = field(default_factory=Counter)
    inference_latencies_ms: list[float] = field(default_factory=list)
    provider_latencies_ms: list[float] = field(default_factory=list)
    window_durations_s: list[float] = field(default_factory=list)
    last_result: Any | None = None
    last_window_ready: bool = False

    def note_read(self, result: Any, before_count: int, after_count: int) -> str | None:
        self.last_result = result
        self.last_window_ready = False
        self.provider_latencies_ms.append(float(result.latency_ms))
        error = result.error
        if error in RESET_EXEMPT_ERRORS:
            self.insufficient_history_events += 1
        if error and ("STALE" in error or "TIMEOUT" in error):
            self.stale_events += 1

        if not self.active_window and after_count > 0:
            self.active_window = True
            self.active_window_started = time.monotonic()
            self.attempted_windows += 1

        if result.valid:
            self.completed_windows += 1
            self.last_window_ready = True
            if self.active_window_started is not None:
                self.window_durations_s.append(time.monotonic() - self.active_window_started)
            metadata = result.metadata
            prediction = str(metadata.get("class_name", result.state))
            self.predictions[prediction] += 1
            latency = metadata.get("inference_latency_ms")
            if finite_number(latency):
                self.inference_latencies_ms.append(float(latency))
            if metadata.get("fallback_used") is True:
                self.fallback_count += 1
            self.active_window = False
            self.active_window_started = None
            return "completed"

        # At 10 Hz, timestamps t0..t299 span 29.9 s. The production adapter
        # may therefore need sample 301 before its 30 s warm-up gate opens.
        # Never turn that expected one-sample wait into a failed trial.
        reached_invalid_boundary = (
            self.active_window
            and after_count >= 300
            and error not in RESET_EXEMPT_ERRORS
        )
        reset_during_window = self.active_window and before_count > 0 and after_count == 0
        if reached_invalid_boundary or reset_during_window:
            reason = error or "MMWAVE_WINDOW_INVALID"
            self.failed_windows += 1
            self.reset_reasons[reason] += 1
            self.active_window = False
            self.active_window_started = None
            return "failed"
        return None

    @property
    def window_success_rate(self) -> float | None:
        finished = self.completed_windows + self.failed_windows
        return self.completed_windows / finished if finished else None


class JsonlResultWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = path.open("x", encoding="utf-8")

    def write(self, event: dict[str, Any]) -> None:
        self._stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + "\n")
        self._stream.flush()

    def close(self) -> None:
        self._stream.close()


def build_event(
    kind: str,
    session: SessionMetrics,
    stream: StreamMetrics,
    result: Any | None,
) -> dict[str, Any]:
    metadata = result.metadata if result is not None else {}
    provider_result = (
        result.to_dict()
        if result is not None and callable(getattr(result, "to_dict", None))
        else None
    )
    record = stream.last_record
    return {
        "kind": kind,
        "experiment_timestamp": datetime.now(timezone.utc).isoformat(),
        "trial_id": session.attempted_windows,
        "ground_truth_scenario": session.scenario,
        "distance_cm": session.distance_cm,
        "posture": session.posture,
        "number_of_samples": metadata.get("window_samples", len(getattr(result, "metadata", {}))),
        "effective_sample_rate_hz": stream.effective_rate_hz,
        "prediction": metadata.get("class_name"),
        "confidence": getattr(result, "confidence", None),
        "probabilities": metadata.get("probabilities"),
        "inference_latency_ms": metadata.get("inference_latency_ms"),
        "provider_latency_ms": getattr(result, "latency_ms", None),
        "fallback_used": metadata.get("fallback_used", False),
        "valid": bool(getattr(result, "valid", False)),
        "error_reset_reason": getattr(result, "error", None),
        "seq": record.get("seq"),
        "schema_version": record.get("schema_version"),
        "esp_firmware_version": record.get("firmware_version"),
        "sensor_firmware_version": record.get("sensor_firmware_version"),
        "provider_result": provider_result,
    }


def summary_event(session: SessionMetrics, stream: StreamMetrics) -> dict[str, Any]:
    normal_valid = session.completed_windows if session.scenario == "normal" else 0
    normal_predictions = session.predictions.get("NORMAL", 0) if session.scenario == "normal" else 0
    return {
        "kind": "session_summary",
        "experiment_timestamp": datetime.now(timezone.utc).isoformat(),
        "started_timestamp": session.started_wall,
        "scenario": session.scenario,
        "target_windows": session.target_windows,
        "distance_cm": session.distance_cm,
        "posture": session.posture,
        "elapsed_s": time.monotonic() - session.started_monotonic,
        "records": stream.records,
        "effective_sample_rate_hz": stream.effective_rate_hz,
        "sample_intervals_s": latency_stats(stream.intervals_s),
        "dropped_sequences": stream.dropped_sequences,
        "nonmonotonic_sequences": stream.nonmonotonic_sequences,
        "uart_failures": stream.uart_failures,
        "host_json_errors": stream.json_errors,
        "checksum_failures": stream.checksum_failures,
        "checksum_error_delta": stream.checksum_error_delta,
        "parser_error_delta": stream.parse_error_delta,
        "invalid_phase": stream.invalid_phase,
        "presence_loss_records": stream.presence_loss_records,
        "maximum_gap_s": stream.max_gap_s,
        "attempted_windows": session.attempted_windows,
        "completed_windows": session.completed_windows,
        "failed_windows": session.failed_windows,
        "window_success_rate": session.window_success_rate,
        "average_window_duration_s": (
            statistics.fmean(session.window_durations_s) if session.window_durations_s else None
        ),
        "reset_reasons": dict(session.reset_reasons),
        "insufficient_history_events": session.insufficient_history_events,
        "stale_events": session.stale_events,
        "inference_count": len(session.inference_latencies_ms),
        "fallback_count": session.fallback_count,
        "prediction_distribution": dict(session.predictions),
        "inference_latency_ms": latency_stats(session.inference_latencies_ms),
        "provider_read_latency_ms": latency_stats(session.provider_latencies_ms),
        "normal_ground_truth_trials": normal_valid,
        "normal_predictions": normal_predictions,
        "normal_agreement_rate": normal_predictions / normal_valid if normal_valid else None,
    }


def render_dashboard(
    port: str,
    provider: MMWaveSensorAdapter,
    stream: StreamMetrics,
    session: SessionMetrics,
) -> str:
    record = stream.last_record
    result = session.last_result
    metadata = result.metadata if result is not None else {}
    config_expected = provider.adapter.config.get("expected_esp_config_hash")
    config_actual = record.get("config_hash")
    config_match = config_actual == config_expected if config_actual is not None else None
    count = len(provider.adapter.estimator.values)
    required = provider.window_samples
    phase = record.get("breath_phase")
    phase_age = record.get("phase_age_ms")
    phase_fresh = finite_number(phase_age) and float(phase_age) <= float(
        provider.adapter.config["max_phase_age_ms"]
    )
    presence = record.get("human_detected_stable", record.get("human_detected_raw"))
    provider_state = getattr(result, "state", "대기")
    elapsed = time.monotonic() - session.started_monotonic
    probabilities = metadata.get("probabilities")
    probability_text = "-" if probabilities is None else ", ".join(f"{value:.4f}" for value in probabilities)
    fallback = metadata.get("fallback_used", False)
    reset_text = ", ".join(f"{key}:{value}" for key, value in session.reset_reasons.items()) or "없음"

    lines = [
        "=" * 78,
        "SafeNest mmWave 실시간 성능 검증  (Ctrl+C: 안전 종료 및 요약)",
        "=" * 78,
        "[하드웨어 / 스트림]",
        f"Port/연결       : {port} / {'CONNECTED' if provider.connected else 'DISCONNECTED'}",
        f"Schema / ESP FW : {record.get('schema_version', '-')} / {record.get('firmware_version', '-')}",
        f"Sensor FW       : {record.get('sensor_firmware_version', '-')}",
        f"Config hash     : {config_actual or '-'} / match={config_match}",
        f"Seq / rate      : {record.get('seq', '-')} / {format_number(stream.effective_rate_hz)} Hz",
        f"UART/check/parser/hostJSON: {stream.uart_failures}/{stream.checksum_error_delta}/{stream.parse_error_delta}/{stream.json_errors}",
        f"Dropped / max gap: {stream.dropped_sequences} / {format_number(stream.max_gap_s)} s",
        "",
        "[센서]",
        f"Presence/distance: {presence} / {format_number(record.get('distance_cm_raw'))} cm",
        f"breath_phase     : {format_number(phase)}  valid={finite_number(phase)} fresh={phase_fresh}",
        f"Warmup/provider  : {provider_state == 'WARMUP'} / {provider_state}",
        "",
        "[AI Window]",
        f"{progress_bar(count, required)}  elapsed={elapsed:.1f}s",
        f"시도/완료/실패   : {session.attempted_windows}/{session.completed_windows}/{session.failed_windows}",
        f"Reset            : {sum(session.reset_reasons.values())} ({reset_text})",
        f"AI WINDOW READY  : {'YES' if session.last_window_ready else 'NO'}",
        "",
        "[실제 breath_phase — 누락값 생성/보간 없음]",
        sparkline(stream.phases),
        "",
        "[최근 실제 TFLite 결과]",
        f"Model/version    : {metadata.get('model_id', '-')} / {metadata.get('model_version', '-')}",
        f"Prediction       : {metadata.get('class_name', '-')}  confidence={format_number(getattr(result, 'confidence', None))}",
        f"Probabilities    : {probability_text}",
        f"TFLite/provider  : {format_number(metadata.get('inference_latency_ms'))} / {format_number(getattr(result, 'latency_ms', None))} ms",
        f"Fallback         : {'!!! FAILURE: ' + str(metadata.get('fallback_reason')) if fallback else 'false'}",
        f"현재 오류        : {getattr(result, 'error', None) or '없음'}",
    ]
    return "\n".join(lines)


def render_summary(summary: dict[str, Any]) -> str:
    inference = summary["inference_latency_ms"]
    provider = summary["provider_read_latency_ms"]
    intervals = summary["sample_intervals_s"]
    agreement = summary["normal_agreement_rate"]
    finished = summary["completed_windows"] + summary["failed_windows"]
    target_met = (
        summary["completed_windows"] >= summary["target_windows"]
        if summary["target_windows"]
        else summary["completed_windows"] >= 2
    )
    if summary["scenario"] == "no-person":
        target_met = summary["completed_windows"] == 0 and summary["presence_loss_records"] > 0
    status = "PASS" if (
        target_met
        and summary["fallback_count"] == 0
        and summary["dropped_sequences"] == 0
        and summary["uart_failures"] == 0
        and summary["checksum_error_delta"] == 0
    ) else "PARTIAL"
    return "\n".join([
        "=" * 72,
        "SafeNest mmWave 성능 검증 요약",
        "=" * 72,
        f"실행 시간: {summary['elapsed_s']:.1f} s",
        f"수집 레코드: {summary['records']}",
        f"평균 sampling rate: {format_number(summary['effective_sample_rate_hz'])} Hz",
        f"샘플 간격 mean/p50/p95/max: {format_number(intervals['mean'])}/{format_number(intervals['p50'])}/{format_number(intervals['p95'])}/{format_number(intervals['max'])} s",
        "",
        "[통신]",
        f"Dropped sequence: {summary['dropped_sequences']}",
        f"UART/checksum/parser/host JSON errors: {summary['uart_failures']}/{summary['checksum_error_delta']}/{summary['parser_error_delta']}/{summary['host_json_errors']}",
        f"Maximum gap: {format_number(summary['maximum_gap_s'])} s",
        "",
        "[AI Window]",
        f"시도/완성/실패: {summary['attempted_windows']}/{summary['completed_windows']}/{summary['failed_windows']}",
        f"Window 성공률: {format_number(summary['window_success_rate'] * 100 if summary['window_success_rate'] is not None else None, 1)} % ({finished}개 종료)",
        f"평균 완성 시간: {format_number(summary['average_window_duration_s'])} s",
        f"Reset 사유: {summary['reset_reasons'] or '없음'}",
        "",
        "[TFLite]",
        f"실제 추론/Fallback: {summary['inference_count']}/{summary['fallback_count']}",
        f"Prediction 분포: {summary['prediction_distribution']}",
        f"latency mean/p50/p95/max: {format_number(inference['mean'])}/{format_number(inference['p50'])}/{format_number(inference['p95'])}/{format_number(inference['max'])} ms",
        "",
        "[Provider]",
        f"read latency mean/p50/p95/max: {format_number(provider['mean'])}/{format_number(provider['p50'])}/{format_number(provider['p95'])}/{format_number(provider['max'])} ms",
        "Serial 대기 시간이 provider read latency의 대부분을 차지할 수 있습니다.",
        "",
        "[정상 호흡 실험]",
        f"Ground truth NORMAL trials/valid/NORMAL: {summary['normal_ground_truth_trials']}/{summary['normal_ground_truth_trials']}/{summary['normal_predictions']}",
        f"기본 일치율(의학적 정확도 아님): {format_number(agreement * 100 if agreement is not None else None, 1)} %",
        "",
        f"[최종 상태] {status}",
        "=" * 72,
    ])


def default_output_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return REPO_ROOT / "devices" / "mmwave" / "validation_results" / f"{stamp}_performance.jsonl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", default="/dev/cu.usbserial-110")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--scenario", choices=("unlabeled", "normal", "no-person"), default="unlabeled")
    parser.add_argument("--distance-cm", type=float)
    parser.add_argument("--posture")
    parser.add_argument("--target-windows", type=int, default=0)
    parser.add_argument("--duration", type=float, default=0.0)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--refresh-hz", type=float, default=4.0)
    parser.add_argument("--plain", action="store_true", help="ANSI 화면 갱신 대신 1초 상태행 출력")
    args = parser.parse_args()
    if args.target_windows < 0 or args.duration < 0 or args.refresh_hz <= 0:
        parser.error("target-windows/duration은 음수가 아니고 refresh-hz는 양수여야 합니다")
    if args.target_windows == 0 and args.duration == 0:
        parser.error("--target-windows 또는 --duration 중 하나는 지정해야 합니다")
    if args.scenario == "normal" and (args.distance_cm is None or not args.posture):
        parser.error("normal 시나리오는 --distance-cm 및 --posture가 필요합니다")
    return args


def main() -> int:
    args = parse_args()
    output = args.output or default_output_path()
    stream_metrics = StreamMetrics()
    session = SessionMetrics(args.scenario, args.distance_cm, args.posture, args.target_windows)
    writer = JsonlResultWriter(output)

    def serial_factory(**kwargs: Any) -> ObservedSerial:
        import serial
        return ObservedSerial(serial.Serial(**kwargs), stream_metrics.observe)

    provider = MMWaveSensorAdapter(
        port=args.port,
        baudrate=args.baud,
        serial_factory=serial_factory,
    )
    if not provider.connect():
        writer.write({"kind": "connection_failure", "port": args.port, "error": provider.last_error})
        writer.close()
        print(f"연결 실패: {provider.last_error}; 결과: {output}", file=sys.stderr)
        return 2

    writer.write({
        "kind": "session_start",
        "experiment_timestamp": session.started_wall,
        "port": args.port,
        "baud": args.baud,
        "scenario": args.scenario,
        "distance_cm": args.distance_cm,
        "posture": args.posture,
        "target_windows": args.target_windows,
        "duration_s": args.duration,
        "raw_sensor_data_stored": False,
    })
    deadline = session.started_monotonic + args.duration if args.duration else None
    next_render = 0.0
    next_plain = 0.0
    try:
        while True:
            before = len(provider.adapter.estimator.values)
            result = provider.read()
            after = len(provider.adapter.estimator.values)
            event = session.note_read(result, before, after)
            if event is not None:
                writer.write(build_event(f"window_{event}", session, stream_metrics, result))
                # Independent non-overlapping validation windows. No sensor value
                # is changed or synthesized; only accumulated validation history
                # is cleared after a terminal window outcome.
                if after >= provider.window_samples:
                    provider.adapter.estimator.reset("MMWAVE_VALIDATION_TRIAL_BOUNDARY")

            now = time.monotonic()
            if now >= next_render:
                dashboard = render_dashboard(args.port, provider, stream_metrics, session)
                if args.plain:
                    if now >= next_plain:
                        print(dashboard.splitlines()[8] + " | " + dashboard.splitlines()[16], flush=True)
                        next_plain = now + 1.0
                else:
                    print("\033[2J\033[H" + dashboard, end="", flush=True)
                next_render = now + 1.0 / args.refresh_hz

            if args.target_windows and session.completed_windows >= args.target_windows:
                break
            if deadline is not None and now >= deadline:
                break
    except KeyboardInterrupt:
        pass
    finally:
        provider.close()
        summary = summary_event(session, stream_metrics)
        writer.write(summary)
        writer.close()

    print("\n" + render_summary(summary))
    print(f"검증 결과(JSONL): {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
