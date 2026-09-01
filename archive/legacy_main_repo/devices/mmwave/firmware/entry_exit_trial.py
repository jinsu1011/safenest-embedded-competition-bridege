#!/usr/bin/env python3
"""Entry/exit KPI trial runner for MR60BHA2.

Streams ESP telemetry and beep events into a single JSONL. Each line has a
unified host_monotonic_ns timestamp so offline analysis can compute per-trial
entry/exit latencies without relying on ESP clock alignment.

The user follows spoken cues: on "들어가세요" they walk to the IN mark and sit
still; on "나가세요" they walk to the OUT mark clear of the cone. Timing:

  pre-roll 5s -> N trials (12s IN + 15s OUT each) -> post-roll 5s.

Nothing about sensor collection is filtered; raw JSON lines are recorded as-is
with a `kind: "sensor"` tag added. Beep events use `kind: "beep"`.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
from pathlib import Path

import serial


VOICE = "Yuna"


def say_blocking(text: str) -> None:
    """Speak and wait until finished — for setup announcements."""
    subprocess.run(["say", "-v", VOICE, text])


def say_async(text: str) -> None:
    subprocess.Popen(["say", "-v", VOICE, text])


def play_sound(sound_path: str) -> None:
    subprocess.Popen(["afplay", sound_path])


def countdown(seconds: int) -> None:
    """Speak each remaining second, aligned to 1s intervals."""
    for s in range(seconds, 0, -1):
        say_async(str(s))
        time.sleep(1.0)


def sensor_reader(ser: serial.Serial, out_file, stop_event: threading.Event) -> None:
    ser.reset_input_buffer()
    ser.readline()
    while not stop_event.is_set():
        raw = ser.readline()
        if not raw:
            continue
        host_ns = time.monotonic_ns()
        try:
            item = json.loads(raw.decode("utf-8", errors="strict").strip())
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if "seq" not in item:
            continue
        item["kind"] = "sensor"
        item["host_monotonic_ns"] = host_ns
        out_file.write(json.dumps(item, ensure_ascii=False) + "\n")
        out_file.flush()


def log_beep(out_file, event: str, trial: int) -> int:
    host_ns = time.monotonic_ns()
    entry = {"kind": "beep", "event": event, "trial": trial, "host_monotonic_ns": host_ns}
    out_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
    out_file.flush()
    return host_ns


def run(port: str, baud: int, trials: int, output: Path,
        in_phase_s: float, out_phase_s: float) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with serial.Serial(port, baud, timeout=0.2) as ser, output.open("w", encoding="utf-8") as out:
        stop = threading.Event()
        reader = threading.Thread(target=sensor_reader, args=(ser, out, stop), daemon=True)
        reader.start()

        time.sleep(2.0)
        play_sound("/System/Library/Sounds/Glass.aiff")
        say_blocking(f"진입퇴장 시험을 시작합니다. 총 {trials}회 반복합니다.")

        for i in range(1, trials + 1):
            say_blocking(f"{i}회. 준비가 완료되었습니다. 5초 뒤에 들어오세요.")
            countdown(5)
            log_beep(out, "enter", i)
            play_sound("/System/Library/Sounds/Ping.aiff")
            say_blocking("측정을 시작합니다.")
            countdown(int(in_phase_s))
            log_beep(out, "exit", i)
            play_sound("/System/Library/Sounds/Ping.aiff")
            say_blocking("나가세요.")
            time.sleep(out_phase_s)

        time.sleep(5.0)
        play_sound("/System/Library/Sounds/Hero.aiff")
        say_blocking(f"진입퇴장 {trials}회 시험이 완료되었습니다.")

        stop.set()
        reader.join(timeout=2.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--in-phase", type=float, default=12.0)
    parser.add_argument("--out-phase", type=float, default=15.0)
    args = parser.parse_args()
    run(args.port, args.baud, args.trials, args.output, args.in_phase, args.out_phase)


if __name__ == "__main__":
    main()
