#!/usr/bin/env python3
"""Read-only aiming helper for MR60BHA2 installation.

Prints a rolling presence rate so the operator can change sensor aim and see
within seconds whether the current direction is free of static reflectors.
This tool never writes logs and never applies filters or thresholds; it only
summarises the raw ESP telemetry stream over a short trailing window.

Distance is reported by MR60BHA2 in ~5.74 cm range bins, so the bin index is
shown next to the raw value to make a fixed reflector obvious.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import Counter, deque
from typing import Any

import serial

BIN_CM = 5.74


def bin_index(distance_cm: Any) -> int | None:
    if not isinstance(distance_cm, (int, float)) or not math.isfinite(distance_cm) or distance_cm <= 0:
        return None
    return round(distance_cm / BIN_CM)


def positive(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value) and value > 0


def run(port: str, baud: int, window_s: float) -> None:
    samples: deque[tuple[float, dict[str, Any]]] = deque()
    last_frame_at: float | None = None
    started = time.monotonic()
    next_report = started + 1.0

    print(f"포트 {port} · {baud}bps · 최근 {window_s:.0f}초 창 · Ctrl+C 종료")
    print("사람이 감지 범위 밖으로 완전히 벗어난 상태에서 센서 방향을 천천히 바꾸세요.")
    print("목표: 재실 YES가 0.0%로 유지되는 방향을 찾는 것입니다.\n")

    with serial.Serial(port, baudrate=baud, timeout=0.2) as stream:
        stream.reset_input_buffer()
        stream.readline()
        while True:
            raw = stream.readline()
            now = time.monotonic()
            if raw:
                try:
                    item = json.loads(raw.decode("utf-8", errors="strict").strip())
                except (UnicodeDecodeError, json.JSONDecodeError):
                    item = None
                if item is not None and "seq" in item:
                    last_frame_at = now
                    samples.append((now, item))

            cutoff = now - window_s
            while samples and samples[0][0] < cutoff:
                samples.popleft()

            if now < next_report:
                continue
            next_report = now + 1.0

            elapsed = now - started
            if last_frame_at is None or now - last_frame_at > 2.0:
                print(f"[{elapsed:5.0f}s] FAULT · ESP JSON 수신 없음 (마지막 프레임 2초 초과)")
                continue
            if not samples:
                print(f"[{elapsed:5.0f}s] 창 안에 샘플 없음")
                continue

            records = [item for _, item in samples]
            total = len(records)
            yes = sum(item.get("human_detected_raw") is True for item in records)
            yes_rate = yes / total

            bins = Counter()
            for item in records:
                index = bin_index(item.get("distance_cm_raw"))
                if index is not None:
                    bins[index] += 1
            bin_text = (
                " ".join(f"bin{index}({count})" for index, count in sorted(bins.items()))
                if bins
                else "거리 없음"
            )
            current = records[-1].get("distance_cm_raw")
            current_text = f"{current:.2f}cm" if positive(current) else "-"

            breath = sum(positive(item.get("breath_rate_raw")) for item in records) / total
            heart = sum(positive(item.get("heart_rate_raw")) for item in records) / total

            last = records[-1]
            errors = f"chk{last.get('checksum_errors', 0)}/parse{last.get('parse_errors', 0)}"

            if yes_rate == 0.0:
                verdict = "조준 양호"
            elif yes_rate < 0.10:
                verdict = "간헐 오탐"
            else:
                verdict = "반사체 있음"

            print(
                f"[{elapsed:5.0f}s] 재실 YES {yes_rate * 100:5.1f}% ({yes}/{total}) "
                f"| 현재 {current_text:>9} | {bin_text} "
                f"| 호흡+ {breath * 100:4.0f}% 심박+ {heart * 100:4.0f}% "
                f"| {errors} | {verdict}"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--window", type=float, default=10.0)
    args = parser.parse_args()
    try:
        run(args.port, args.baud, args.window)
    except KeyboardInterrupt:
        print("\n종료했습니다. 포트가 해제되었습니다.")


if __name__ == "__main__":
    main()
