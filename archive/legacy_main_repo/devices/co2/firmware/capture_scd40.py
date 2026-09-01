#!/usr/bin/env python3
"""Raspberry Pi HTTP API의 ESP32 SCD40 실측값을 CSV로 캡처한다."""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


FIELDS = [
    "host_timestamp",
    "host_unix_s",
    "host_monotonic_ns",
    "scenario",
    "source_url",
    "device_id",
    "seq",
    "uptime_ms",
    "co2_ppm",
    "valid",
    "sensor_state",
    "error",
    "connected",
    "fresh",
    "transport_status",
    "peer",
    "age_seconds",
    "last_received_at",
    "raw_response_json",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="SafeNest Pi /health에서 실제 SCD40 값을 읽어 원본 CSV로 저장합니다."
    )
    parser.add_argument("--url", default="http://192.168.1.44:8080/health")
    parser.add_argument("--duration-sec", type=float, required=True)
    parser.add_argument("--interval-sec", type=float, default=1.0)
    parser.add_argument("--timeout-sec", type=float, default=3.0)
    parser.add_argument("--scenario", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.duration_sec <= 0 or args.interval_sec <= 0 or args.timeout_sec <= 0:
        parser.error("duration-sec, interval-sec, timeout-sec는 양수여야 합니다.")
    if args.output.suffix.lower() != ".csv":
        parser.error("output 파일 확장자는 .csv여야 합니다.")
    return args


def fetch_json(url: str, timeout_sec: float) -> tuple[dict | None, str | None, str]:
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=timeout_sec) as response:
            raw = response.read().decode("utf-8")
        payload = json.loads(raw)
        if not isinstance(payload, dict):
            return None, "INVALID_FORMAT", raw
        return payload, None, raw
    except HTTPError as exc:
        return None, f"HTTP_ERROR_{exc.code}", ""
    except URLError as exc:
        return None, f"READ_TIMEOUT_OR_CONNECTION_ERROR:{exc.reason}", ""
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return None, f"INVALID_FORMAT:{exc}", ""


def optional_number(value: object) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return value if math.isfinite(number) else None


def build_row(args: argparse.Namespace) -> dict[str, object]:
    now = time.time()
    payload, fetch_error, raw = fetch_json(args.url, args.timeout_sec)
    row: dict[str, object] = {
        "host_timestamp": datetime.fromtimestamp(now, timezone.utc).isoformat(timespec="milliseconds"),
        "host_unix_s": f"{now:.6f}",
        "host_monotonic_ns": time.monotonic_ns(),
        "scenario": args.scenario,
        "source_url": args.url,
        "sensor_state": "READ_TIMEOUT" if fetch_error else "INVALID_FORMAT",
        "error": fetch_error or "MISSING_SENSOR_OBJECT",
        "raw_response_json": raw,
    }
    if payload is None:
        return row

    sensors = payload.get("sensors")
    if not isinstance(sensors, dict):
        row["error"] = "MISSING_SENSOR_OBJECT"
        return row

    valid_map = sensors.get("valid")
    valid_co2 = isinstance(valid_map, dict) and valid_map.get("co2") is True
    co2_ppm = optional_number(sensors.get("co2_ppm"))
    connected = sensors.get("connected") is True
    fresh = sensors.get("fresh") is True
    transport_status = str(sensors.get("status") or "")

    row.update(
        {
            "device_id": sensors.get("device_id"),
            "seq": optional_number(sensors.get("seq")),
            "uptime_ms": optional_number(sensors.get("uptime_ms")),
            "co2_ppm": co2_ppm,
            "valid": valid_co2 and co2_ppm is not None and connected and fresh,
            "connected": connected,
            "fresh": fresh,
            "transport_status": transport_status,
            "peer": sensors.get("peer"),
            "age_seconds": optional_number(sensors.get("age_seconds")),
            "last_received_at": optional_number(sensors.get("last_received_at")),
        }
    )

    if not connected:
        row.update(sensor_state="NOT_CONNECTED", error="ESP32_NOT_CONNECTED")
    elif not fresh or transport_status != "live":
        row.update(sensor_state="STALE", error="ESP32_TELEMETRY_STALE")
    elif not valid_co2:
        row.update(sensor_state="INVALID_FORMAT", error="CO2_VALID_FALSE")
    elif co2_ppm is None:
        row.update(sensor_state="INVALID_FORMAT", error="CO2_VALUE_MISSING_OR_NON_FINITE")
    else:
        row.update(sensor_state="NORMAL", error="")
    return row


def main() -> None:
    args = parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit(f"원본 로그 덮어쓰기 금지: {args.output}")

    started = time.monotonic()
    deadline = started + args.duration_sec
    samples = 0
    invalid = 0
    with args.output.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, extrasaction="ignore")
        writer.writeheader()
        next_sample = started
        while time.monotonic() < deadline:
            row = build_row(args)
            writer.writerow(row)
            stream.flush()
            samples += 1
            if row.get("valid") is not True:
                invalid += 1
            next_sample += args.interval_sec
            remaining = next_sample - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)

    print(f"captured_samples={samples} invalid_samples={invalid} path={args.output}")


if __name__ == "__main__":
    main()
