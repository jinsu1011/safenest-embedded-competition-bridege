#!/usr/bin/env python3
"""SafeNest MR60BHA2 read-only terminal dashboard."""

from __future__ import annotations

import argparse
import json
import math
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

import serial
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


HEART_COLOR = "#00A83B"
BREATH_COLOR = "#00A6C8"
DISTANCE_COLOR = "#246BFD"
PRESENCE_COLOR = "#C000E8"
UNKNOWN_COLOR = "#D18B00"


@dataclass
class LastValid:
    value: float | None = None
    received_at: float | None = None

    def update(self, candidate: Any, now: float, sensor_age_ms: Any = 0) -> None:
        if isinstance(candidate, (int, float)) and math.isfinite(candidate) and candidate > 0:
            self.value = float(candidate)
            age_seconds = (
                float(sensor_age_ms) / 1000.0
                if isinstance(sensor_age_ms, (int, float))
                and math.isfinite(sensor_age_ms)
                and sensor_age_ms >= 0
                else 0.0
            )
            self.received_at = now - age_seconds
        else:
            self.clear()

    def clear(self) -> None:
        self.value = None
        self.received_at = None

    def display(self, unit: str, now: float, presence: bool | None) -> tuple[str, str]:
        if presence is False:
            return "UNKNOWN", "재실 NO · 생체값 판정 금지"
        if presence is not True:
            return "UNKNOWN", "재실 상태 미확립"
        if self.value is None or self.received_at is None:
            return "UNKNOWN", "유효한 양수 샘플 없음"
        age = now - self.received_at
        return f"{self.value:.1f} {unit}", f"센서 원시 후보 · {age:.1f}초 전"


def value_text(value: str, detail: str, color: str) -> Group:
    return Group(
        Align.center(Text(value, style=f"bold {color}")),
        Align.center(Text(detail, style="dim")),
    )


def make_dashboard(state: dict[str, Any]) -> Group:
    now = time.monotonic()
    presence = state.get("presence")
    heart_value, heart_detail = state["heart"].display("bpm", now, presence)
    breath_value, breath_detail = state["breath"].display("rpm", now, presence)
    distance_value, distance_detail = state["distance"].display("cm", now, presence)
    if presence is True:
        presence_value, presence_detail = "감지됨", "RAW presence=true"
    elif presence is False:
        presence_value, presence_detail = "미감지", "RAW presence=false"
    else:
        presence_value, presence_detail = "UNKNOWN", "아직 프레임 없음"

    left = Table.grid(expand=True)
    left.add_column(ratio=1)
    left.add_column(ratio=1)
    left.add_row(
        Panel(
            value_text(heart_value, heart_detail, HEART_COLOR if heart_value != "UNKNOWN" else UNKNOWN_COLOR),
            title="심박수 · Heart Rate",
            border_style=HEART_COLOR,
        ),
        Panel(
            value_text(breath_value, breath_detail, BREATH_COLOR if breath_value != "UNKNOWN" else UNKNOWN_COLOR),
            title="호흡수 · Breath Rate",
            border_style=BREATH_COLOR,
        ),
    )
    left.add_row(
        Panel(
            value_text(distance_value, distance_detail, DISTANCE_COLOR if distance_value != "UNKNOWN" else UNKNOWN_COLOR),
            title="거리 · Distance",
            border_style=DISTANCE_COLOR,
        ),
        Panel(
            value_text(presence_value, presence_detail, PRESENCE_COLOR if presence is not None else UNKNOWN_COLOR),
            title="재실 · Presence",
            border_style=PRESENCE_COLOR,
        ),
    )

    elapsed = max(now - state["started_at"], 0.001)
    frame_rate = state["frames"] / elapsed
    last_age = now - state["last_frame_at"] if state["last_frame_at"] else math.inf
    if last_age > 2.0:
        link_state, link_color = "FAULT/NO DATA", "red"
    elif elapsed < 60.0:
        link_state, link_color = "WARMUP", "yellow"
    else:
        link_state, link_color = "RAW STREAM", "green"

    status = Table.grid(padding=(0, 2))
    status.add_column(style="bold")
    status.add_column()
    status.add_row("센서 상태", Text(link_state, style=f"bold {link_color}"))
    status.add_row("직렬 포트", state["port"])
    status.add_row("프레임", f"{state['frames']} ({frame_rate:.1f} frame/s)")
    status.add_row("JSON 오류", str(state["json_errors"]))
    status.add_row("체크섬 오류", str(state["checksum_errors"]))
    status.add_row("프레임 파싱 오류", str(state["parse_errors"]))
    status.add_row("마지막 프레임", "없음" if math.isinf(last_age) else f"{last_age:.2f}초 전")
    status.add_row("ESP uptime", f"{state.get('uptime_ms', 0) / 1000:.1f}초")

    events = Table(expand=True)
    events.add_column("ESP 시간", width=10)
    events.add_column("재실", width=8)
    events.add_column("거리", width=10)
    events.add_column("HR", width=9)
    events.add_column("BR", width=9)
    for item in list(state["events"])[-7:]:
        events.add_row(*item)
    if not state["events"]:
        events.add_row("-", "-", "-", "-", "-")

    header = Panel(
        Align.center(Text("SafeNest · MR60BHA2 실시간 원시 모니터", style="bold cyan")),
        subtitle="0/null/timeout은 정상 또는 무호흡으로 판정하지 않음 · Ctrl+C 종료",
    )
    lower = Table.grid(expand=True)
    lower.add_column(ratio=2)
    lower.add_column(ratio=1)
    lower.add_row(Panel(events, title="최근 원시 프레임"), Panel(status, title="통신 상태"))
    return Group(header, left, lower)


def text_value(value: Any, unit: str = "") -> str:
    if not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        return "UNKNOWN"
    return f"{value:.1f}{unit}"


def run(port: str, baud: int) -> None:
    console = Console(
        force_terminal=True,
        force_interactive=True,
        color_system="truecolor",
        no_color=False,
    )
    state: dict[str, Any] = {
        "port": port,
        "started_at": time.monotonic(),
        "last_frame_at": None,
        "frames": 0,
        "json_errors": 0,
        "checksum_errors": 0,
        "parse_errors": 0,
        "presence": None,
        "uptime_ms": 0,
        "heart": LastValid(),
        "breath": LastValid(),
        "distance": LastValid(),
        "events": deque(maxlen=20),
    }

    with serial.Serial(port, baudrate=baud, timeout=0.2) as stream:
        stream.reset_input_buffer()
        with Live(
            make_dashboard(state),
            console=console,
            refresh_per_second=5,
            screen=True,
        ) as live:
            while True:
                raw = stream.readline()
                now = time.monotonic()
                if raw:
                    try:
                        item = json.loads(raw.decode("utf-8", errors="strict").strip())
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        state["json_errors"] += 1
                    else:
                        if "seq" in item:
                            state["frames"] += 1
                            state["last_frame_at"] = now
                            state["uptime_ms"] = item.get("ts_monotonic_ms", 0)
                            state["presence"] = item.get("human_detected_raw")
                            state["checksum_errors"] = item.get("checksum_errors", 0)
                            state["parse_errors"] = item.get("parse_errors", 0)
                            state["heart"].update(
                                item.get("heart_rate_raw"), now, item.get("heart_age_ms")
                            )
                            state["breath"].update(
                                item.get("breath_rate_raw"), now, item.get("breath_age_ms")
                            )
                            state["distance"].update(
                                item.get("distance_cm_raw"), now, item.get("distance_age_ms")
                            )
                            if state["presence"] is False:
                                state["heart"].clear()
                                state["breath"].clear()
                                state["distance"].clear()
                            state["events"].append(
                                (
                                    f"{state['uptime_ms'] / 1000:.1f}s",
                                    "YES" if state["presence"] is True else "NO",
                                    text_value(item.get("distance_cm_raw"), "cm"),
                                    text_value(item.get("heart_rate_raw")),
                                    text_value(item.get("breath_rate_raw")),
                                )
                            )
                live.update(make_dashboard(state))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/cu.usbserial-10")
    parser.add_argument("--baud", type=int, default=115200)
    args = parser.parse_args()
    run(args.port, args.baud)


if __name__ == "__main__":
    main()
