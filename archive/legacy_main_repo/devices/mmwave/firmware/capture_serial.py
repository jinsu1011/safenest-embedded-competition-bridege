#!/usr/bin/env python3
"""Capture ESP JSONL output without modifying sensor records."""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

import serial


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/cu.usbserial-10")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path)
    parser.add_argument("--cue-output", type=Path)
    parser.add_argument("--cue-interval", type=float, default=30.0)
    parser.add_argument("--cue-count", type=int, default=0)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.receipt_output:
        args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
    if args.cue_output:
        args.cue_output.parent.mkdir(parents=True, exist_ok=True)
    if args.cue_count < 0 or args.cue_interval <= 0:
        parser.error("cue count must be non-negative and cue interval must be positive")
    if args.cue_count and args.duration < args.cue_count * args.cue_interval:
        parser.error("duration must include the final scheduled cue")
    deadline = time.monotonic() + args.duration
    records = 0
    cues = 0
    with serial.Serial(args.port, args.baud, timeout=0.2) as stream:
        stream.reset_input_buffer()
        # Opening can occur in the middle of a USB serial line. Discard only
        # that partial line; every subsequent sensor record is preserved.
        stream.readline()
        capture_started = time.monotonic()
        next_cue = capture_started + args.cue_interval
        with args.output.open("wb") as output, (
            args.receipt_output.open("a", encoding="utf-8")
            if args.receipt_output
            else open("/dev/null", "w", encoding="utf-8")
        ) as receipts, (
            args.cue_output.open("x", encoding="utf-8")
            if args.cue_output
            else open("/dev/null", "w", encoding="utf-8")
        ) as cue_stream:
            while time.monotonic() < deadline:
                raw = stream.readline()
                if raw:
                    output.write(raw)
                    output.flush()
                    records += 1
                    if args.receipt_output:
                        try:
                            item = json.loads(raw)
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            item = {}
                        receipts.write(
                            json.dumps(
                                {
                                    "kind": "telemetry",
                                    "host_monotonic_ns": time.monotonic_ns(),
                                    "seq": item.get("seq"),
                                    "esp_ts_monotonic_ms": item.get("ts_monotonic_ms"),
                                }
                            )
                            + "\n"
                        )
                        receipts.flush()
                now = time.monotonic()
                if cues < args.cue_count and now >= next_cue:
                    cues += 1
                    cue_stream.write(
                        json.dumps(
                            {
                                "kind": "watch_prompt",
                                "index": cues,
                                "scheduled_elapsed_s": cues * args.cue_interval,
                                "host_monotonic_ns": time.monotonic_ns(),
                            }
                        )
                        + "\n"
                    )
                    cue_stream.flush()
                    subprocess.Popen(
                        ["say", "-v", "Yuna", f"체크 {cues}"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    next_cue = capture_started + (cues + 1) * args.cue_interval
    if args.cue_count:
        subprocess.Popen(
            ["say", "-v", "Yuna", "측정 완료. 기록한 숫자를 보내 주세요."],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    print(f"captured_records={records} cues={cues} path={args.output}")


if __name__ == "__main__":
    main()
