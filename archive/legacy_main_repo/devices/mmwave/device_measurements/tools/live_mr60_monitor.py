#!/usr/bin/env python3
"""Capture MR60 ESP JSONL and show a live, human-readable health line.

The saved output is the received JSON line verbatim. The monitor adds no
filtering, interpolation, or mutation to the raw evidence file.
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import sys
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path


def serial_candidates() -> list[str]:
    patterns = (
        "/dev/cu.usbserial*", "/dev/cu.SLAB*", "/dev/cu.usbmodem*",
        "/dev/ttyUSB*", "/dev/ttyACM*",
    )
    return sorted({item for pattern in patterns for item in glob.glob(pattern)})


def finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def status_line(stats: dict, last: dict, window_timestamps: deque[float], start_wall: float) -> str:
    elapsed = max(time.monotonic() - start_wall, 1e-9)
    timestamps = list(window_timestamps)
    rate = ((timestamps[-1] - timestamps[0]) / max(len(timestamps) - 1, 1)) if len(timestamps) > 1 else 0.0
    hz = 1.0 / rate if rate > 0 else 0.0
    last_gap_ms = stats.get("last_gap_ms")
    presence = last.get("human_detected_stable", last.get("human_detected_raw"))
    distance = last.get("distance_cm_raw")
    phase = last.get("breath_phase")
    if not finite(distance):
        distance_text = "-"
    else:
        distance_text = f"{float(distance):.1f}cm"
    if not finite(phase):
        phase_text = "-"
    else:
        phase_text = f"{float(phase):+.4f}"
    ready = len(window_timestamps) >= 300 and (timestamps[-1] - timestamps[0] >= 29.9) if timestamps else False
    bad_stream = stats["uart_bad"] or stats["checksum_bad"] or stats["gap_over_500ms"] or stats["timestamp_errors"]
    if bad_stream:
        state = "FAULT"
    elif presence is not True:
        state = "UNKNOWN_NO_PRESENCE"
    elif not finite(distance) or not 40.0 <= float(distance) <= 150.0:
        state = "UNKNOWN_DISTANCE"
    elif not ready:
        state = "WARMUP_WINDOW"
    else:
        state = "VALID_CANDIDATE"
    last_gap_text = "-" if last_gap_ms is None else f"{last_gap_ms:.0f}ms"
    return (
        f"[{elapsed:7.1f}s] records={stats['sensor_records']:5d} "
        f"rate={hz:5.2f}Hz last_gap={last_gap_text:>6} max_gap={stats['max_gap_ms']:4.0f}ms "
        f"json_bad={stats['json_bad']} uart_bad={stats['uart_bad']} checksum_bad={stats['checksum_bad']} "
        f"presence={presence!s:5} distance={distance_text:>7} phase={phase_text:>8} "
        f"window={'READY' if ready else 'WAIT'} state={state}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--port", help="USB serial port; if omitted, auto-detect /dev/cu.usb* or /dev/ttyUSB*/ACM*")
    source.add_argument("--replay", type=Path, help="replay an existing JSONL file for monitor testing")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--output", type=Path, help="raw output JSONL; required for live port capture")
    parser.add_argument("--status-interval", type=float, default=1.0)
    parser.add_argument("--replay-delay", type=float, default=0.0)
    parser.add_argument(
        "--duration-seconds",
        type=float,
        help="stop a live capture after this many host-monotonic seconds",
    )
    args = parser.parse_args()

    if args.duration_seconds is not None and args.duration_seconds <= 0:
        parser.error("--duration-seconds must be greater than zero")

    if args.port:
        port = args.port
    elif args.replay:
        port = None
    else:
        candidates = serial_candidates()
        if len(candidates) != 1:
            print("No unique USB serial port detected.")
            print("Candidates:", ", ".join(candidates) if candidates else "none")
            print("Connect ESP32 and pass --port explicitly if more than one port appears.")
            return 2
        port = candidates[0]

    if port and args.output is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        args.output = Path("raw") / f"live_{stamp}.jsonl"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)

    stream = None
    close_stream = False
    if port:
        try:
            import serial
        except ImportError:
            print("pyserial is required for --port. Install it in the capture runtime first.")
            return 2
        print(f"Opening {port} at {args.baud} baud")
        stream = serial.Serial(port, baudrate=args.baud, timeout=0.5)
        stream.reset_input_buffer()
        boundary_line = stream.readline()
        print(
            "Capture boundary synchronized before raw recording "
            f"(discarded_pre_capture_bytes={len(boundary_line)})"
        )
        close_stream = True
    else:
        print(f"Replaying {args.replay}")
        stream = args.replay.open(encoding="utf-8")
        close_stream = True

    stats = {
        "physical_lines": 0, "json_bad": 0, "non_sensor_lines": 0,
        "sensor_records": 0, "uart_bad": 0, "checksum_bad": 0,
        "gap_over_500ms": 0, "timestamp_errors": 0, "max_gap_ms": 0.0,
        "last_gap_ms": None,
    }
    previous_ts = None
    previous_seq = None
    window_timestamps: deque[float] = deque(maxlen=300)
    last = {}
    start_utc = datetime.now(timezone.utc)
    start_wall = time.monotonic()
    print(f"Capture start UTC: {start_utc.isoformat().replace('+00:00', 'Z')}")
    next_status = start_wall
    output_handle = args.output.open("x", encoding="utf-8") if args.output else None

    def handle_line(text: str) -> None:
        nonlocal previous_ts, previous_seq, next_status, last
        stats["physical_lines"] += 1
        if output_handle:
            output_handle.write(text if text.endswith("\n") else text + "\n")
            output_handle.flush()
        try:
            record = json.loads(text)
        except json.JSONDecodeError:
            stats["json_bad"] += 1
            return
        if not isinstance(record, dict) or record.get("kind") not in (None, "sensor"):
            stats["non_sensor_lines"] += 1
            return
        stats["sensor_records"] += 1
        last = record
        if record.get("uart_frame_ok") is not True:
            stats["uart_bad"] += 1
        if record.get("checksum_ok") is not True:
            stats["checksum_bad"] += 1
        timestamp_ms = record.get("ts_monotonic_ms")
        if finite(timestamp_ms):
            timestamp_s = float(timestamp_ms) / 1000.0
            if previous_ts is not None:
                gap_ms = (timestamp_s - previous_ts) * 1000.0
                stats["last_gap_ms"] = gap_ms
                stats["max_gap_ms"] = max(stats["max_gap_ms"], gap_ms)
                if gap_ms <= 0:
                    stats["timestamp_errors"] += 1
                if gap_ms > 500.0:
                    stats["gap_over_500ms"] += 1
            previous_ts = timestamp_s
            window_timestamps.append(timestamp_s)
        seq = record.get("seq")
        if isinstance(seq, int) and not isinstance(seq, bool):
            if previous_seq is not None and seq <= previous_seq:
                stats["timestamp_errors"] += 1
            previous_seq = seq
        now = time.monotonic()
        if now >= next_status:
            print(status_line(stats, last, window_timestamps, start_wall), flush=True)
            next_status = now + max(args.status_interval, 0.1)

    try:
        if port:
            while True:
                if args.duration_seconds is not None and time.monotonic() - start_wall >= args.duration_seconds:
                    print(f"\nCapture duration reached: {args.duration_seconds:.1f}s")
                    break
                raw = stream.readline()
                if raw:
                    handle_line(raw.decode("utf-8", errors="replace"))
                elif time.monotonic() >= next_status:
                    print(status_line(stats, last, window_timestamps, start_wall), flush=True)
                    next_status = time.monotonic() + max(args.status_interval, 0.1)
        else:
            for line in stream:
                handle_line(line)
                if args.replay_delay > 0:
                    time.sleep(args.replay_delay)
    except KeyboardInterrupt:
        print("\nStopping capture...")
    finally:
        if output_handle:
            output_handle.close()
        if close_stream:
            stream.close()

    end_utc = datetime.now(timezone.utc)
    print(status_line(stats, last, window_timestamps, start_wall), flush=True)
    print(f"Capture end UTC: {end_utc.isoformat().replace('+00:00', 'Z')}")
    if args.output and args.output.is_file():
        digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
        print(f"Saved raw: {args.output}")
        print(f"SHA-256: {digest}")
        print(f"Bytes: {args.output.stat().st_size}")
    print(json.dumps(stats, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
