#!/usr/bin/env python3
"""SafeNest LCD display and laptop control server.

Runs entirely on the Raspberry Pi with Python's standard library.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import signal
import socket
import struct
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"
STATE_FILE = ROOT / "state.json"
ALLOWED_STATES = {
    "normal-empty",
    "normal-occupied",
    "warning",
    "danger",
    "emergency",
    "offline",
}


def empty_emergency_state() -> dict[str, object]:
    return {
        "active": False,
        "entered_at": None,
        "acknowledged": False,
        "acknowledged_at": None,
        "cleared_at": None,
        "cleared_to": None,
        "recovery_pending": False,
        "recovery_acknowledged_at": None,
    }


DEFAULT_STATE = {
    "state": "normal-empty",
    "room": "밀폐공간 A-01",
    "revision": 1,
    "updated_at": int(time.time()),
    "emergency": empty_emergency_state(),
}
STATE_LOCK = threading.Lock()

SENSOR_MAGIC = b"SNST"
SENSOR_PROTOCOL_VERSION = 1
PACKET_TELEMETRY_JSON = 1
PACKET_THERMAL_U16_BE = 2
PACKET_HEADER = struct.Struct("!4sBBHII")
MAX_SENSOR_PAYLOAD_BYTES = 20_000
EXPECTED_TELEMETRY_SCHEMA = "safenest.telemetry.v1"


class SensorStore:
    """Thread-safe latest-value store for the ESP32 telemetry stream."""

    def __init__(self, stale_seconds: float = 5.0) -> None:
        self.stale_seconds = stale_seconds
        self._lock = threading.Lock()
        self._connected = False
        self._peer: str | None = None
        self._last_received_monotonic: float | None = None
        self._last_received_at: int | None = None
        self._listener_error: str | None = None
        self._revision = 0
        self._thermal_frames_received = 0
        self._telemetry: dict[str, object] = {
            "device_id": None,
            "boot_id": None,
            "seq": None,
            "uptime_ms": None,
            "resp_rate_bpm": None,
            "heart_rate_bpm": None,
            "co2_ppm": None,
            "pir_motion": None,
            "valid": {
                "respiration": False,
                "heart": False,
                "co2": False,
            },
            "co2_measurement_event_id": None,
            "co2_measurement_monotonic_ms": None,
            "co2_measurement_event_valid": None,
            "co2_sensor_model": None,
            "co2_event_identity_class": None,
            "co2_preheat_complete": None,
            "abc_enabled": None,
            "configured_range_ppm": None,
        }

    def set_listener_error(self, error: str | None) -> None:
        with self._lock:
            self._listener_error = error
            self._revision += 1

    def set_connected(self, connected: bool, peer: tuple[str, int] | None = None) -> None:
        with self._lock:
            self._connected = connected
            self._peer = f"{peer[0]}:{peer[1]}" if connected and peer else None
            self._revision += 1

    @staticmethod
    def _optional_number(value: object, name: str) -> int | float | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{name} must be a number or null")
        return value

    @staticmethod
    def _optional_bool(value: object, name: str) -> bool | None:
        if value is None:
            return None
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be a boolean or null")
        return value

    @staticmethod
    def _optional_text(value: object, name: str) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str) or not value:
            raise ValueError(f"{name} must be a non-empty string or null")
        return value[:64]

    @staticmethod
    def _preheat_complete(payload: dict[str, object]) -> bool | None:
        if "co2_preheat_complete" in payload:
            return SensorStore._optional_bool(
                payload.get("co2_preheat_complete"), "co2_preheat_complete"
            )
        if "co2_preheat" in payload:
            return SensorStore._optional_bool(payload.get("co2_preheat"), "co2_preheat")
        return None

    def record_telemetry(self, payload: dict[str, object]) -> None:
        if payload.get("schema") != EXPECTED_TELEMETRY_SCHEMA:
            raise ValueError(f"unsupported telemetry schema: {payload.get('schema')!r}")
        valid = payload.get("valid")
        if not isinstance(valid, dict):
            raise ValueError("telemetry valid field must be an object")
        pir_motion = payload.get("pir_motion")
        if not isinstance(pir_motion, bool):
            raise ValueError("pir_motion must be a boolean")

        telemetry: dict[str, object] = {
            "device_id": str(payload.get("device_id", ""))[:64] or None,
            "boot_id": self._optional_text(payload.get("boot_id"), "boot_id")
            if payload.get("boot_id") is not None
            else None,
            "seq": self._optional_number(payload.get("seq"), "seq"),
            "uptime_ms": self._optional_number(payload.get("uptime_ms"), "uptime_ms"),
            "resp_rate_bpm": self._optional_number(
                payload.get("resp_rate_bpm"), "resp_rate_bpm"
            ),
            "heart_rate_bpm": self._optional_number(
                payload.get("heart_rate_bpm"), "heart_rate_bpm"
            ),
            "co2_ppm": self._optional_number(payload.get("co2_ppm"), "co2_ppm"),
            "pir_motion": pir_motion,
            "valid": {
                "respiration": valid.get("respiration") is True,
                "heart": valid.get("heart") is True,
                "co2": valid.get("co2") is True,
            },
            "co2_measurement_event_id": self._optional_number(
                payload.get("co2_measurement_event_id"), "co2_measurement_event_id"
            ),
            "co2_measurement_monotonic_ms": self._optional_number(
                payload.get("co2_measurement_monotonic_ms"),
                "co2_measurement_monotonic_ms",
            ),
            "co2_measurement_event_valid": self._optional_bool(
                payload.get("co2_measurement_event_valid"),
                "co2_measurement_event_valid",
            ),
            "co2_sensor_model": self._optional_text(
                payload.get("co2_sensor_model"), "co2_sensor_model"
            ),
            "co2_event_identity_class": self._optional_text(
                payload.get("co2_event_identity_class"), "co2_event_identity_class"
            ),
            "co2_preheat_complete": self._preheat_complete(payload),
            "abc_enabled": self._optional_bool(payload.get("abc_enabled"), "abc_enabled"),
            "configured_range_ppm": self._optional_number(
                payload.get("configured_range_ppm"), "configured_range_ppm"
            ),
        }
        with self._lock:
            self._telemetry = telemetry
            self._last_received_monotonic = time.monotonic()
            self._last_received_at = int(time.time())
            self._listener_error = None
            self._revision += 1

    def record_thermal_frame(self) -> None:
        with self._lock:
            self._thermal_frames_received += 1

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            age_seconds = None
            if self._last_received_monotonic is not None:
                age_seconds = max(0.0, time.monotonic() - self._last_received_monotonic)
            fresh = (
                self._connected
                and age_seconds is not None
                and age_seconds <= self.stale_seconds
            )
            if self._listener_error:
                status = "error"
            elif fresh:
                status = "live"
            elif self._last_received_at is not None:
                status = "stale"
            else:
                status = "waiting"
            return {
                **self._telemetry,
                "connected": self._connected,
                "fresh": fresh,
                "status": status,
                "peer": self._peer,
                "age_seconds": round(age_seconds, 1) if age_seconds is not None else None,
                "last_received_at": self._last_received_at,
                "listener_error": self._listener_error,
                "thermal_frames_received": self._thermal_frames_received,
                "revision": self._revision,
            }


def recv_exact(
    connection: socket.socket,
    size: int,
    *,
    stop_event: threading.Event | None = None,
    idle_ok: bool = False,
    frame_deadline_seconds: float = 5.0,
) -> bytes:
    """Receive exactly ``size`` bytes, keeping partial progress.

    When ``idle_ok`` is true, a timeout with zero bytes is not fatal. ESP 1.7.3
    may skip a 1 Hz snapshot and leave a ~2 s gap on a live socket. Once any
    byte of this field has arrived, ``frame_deadline_seconds`` bounds completion
    so a truncated SNST header/body still closes the connection.
    """

    if size < 0:
        raise ValueError("size must be non-negative")
    if frame_deadline_seconds <= 0:
        raise ValueError("frame_deadline_seconds must be positive")
    if size == 0:
        return b""

    chunks: list[bytes] = []
    remaining = size
    received = 0
    frame_deadline: float | None = None
    while remaining:
        if stop_event is not None and stop_event.is_set():
            raise ConnectionError("ESP32 receiver stopping")
        now = time.monotonic()
        if received == 0:
            pass
        elif frame_deadline is not None and now >= frame_deadline:
            raise ConnectionError(
                f"receive deadline exceeded: got {received} of {size} bytes"
            )
        try:
            chunk = connection.recv(remaining)
        except socket.timeout:
            if received == 0 and idle_ok:
                continue
            if received == 0:
                if frame_deadline is None:
                    frame_deadline = time.monotonic() + frame_deadline_seconds
                if time.monotonic() >= frame_deadline:
                    raise ConnectionError(
                        f"receive deadline exceeded: got 0 of {size} bytes"
                    )
                continue
            if frame_deadline is not None and time.monotonic() >= frame_deadline:
                raise ConnectionError(
                    f"receive deadline exceeded: got {received} of {size} bytes"
                )
            continue
        if not chunk:
            raise ConnectionError("ESP32 closed the TCP connection")
        if received == 0:
            frame_deadline = time.monotonic() + frame_deadline_seconds
        chunks.append(chunk)
        received += len(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


class SensorReceiver:
    """Consume SafeNest protocol v1 packets without blocking the LCD server."""

    def __init__(self, host: str, port: int, store: SensorStore) -> None:
        self.host = host
        self.port = port
        self.store = store
        self.stop_event = threading.Event()
        self.thread = threading.Thread(
            target=self._run,
            name="safenest-sensor-receiver",
            daemon=True,
        )

    def start(self) -> None:
        self.thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        self.thread.join(timeout=3.0)

    def _handle_connection(
        self,
        connection: socket.socket,
        peer: tuple[str, int],
    ) -> None:
        connection.settimeout(0.25)
        try:
            connection.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            if hasattr(socket, "TCP_KEEPIDLE"):
                connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 30)
            if hasattr(socket, "TCP_KEEPINTVL"):
                connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
            if hasattr(socket, "TCP_KEEPCNT"):
                connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
        except OSError:
            pass
        self.store.set_connected(True, peer)
        try:
            while not self.stop_event.is_set():
                header_bytes = recv_exact(
                    connection,
                    PACKET_HEADER.size,
                    stop_event=self.stop_event,
                    idle_ok=True,
                    frame_deadline_seconds=5.0,
                )
                magic, version, packet_type, flags, _sequence, payload_length = (
                    PACKET_HEADER.unpack(header_bytes)
                )
                if magic != SENSOR_MAGIC:
                    raise ValueError(f"bad packet magic: {magic!r}")
                if version != SENSOR_PROTOCOL_VERSION:
                    raise ValueError(f"unsupported protocol version: {version}")
                if flags != 0:
                    raise ValueError(f"unsupported packet flags: 0x{flags:04x}")
                if payload_length > MAX_SENSOR_PAYLOAD_BYTES:
                    raise ValueError(f"payload is too large: {payload_length} bytes")

                payload = recv_exact(
                    connection,
                    payload_length,
                    stop_event=self.stop_event,
                    idle_ok=False,
                    frame_deadline_seconds=5.0,
                )
                if packet_type == PACKET_TELEMETRY_JSON:
                    decoded = json.loads(payload.decode("utf-8"))
                    if not isinstance(decoded, dict):
                        raise ValueError("telemetry JSON root must be an object")
                    self.store.record_telemetry(decoded)
                elif packet_type == PACKET_THERMAL_U16_BE:
                    self.store.record_thermal_frame()
                else:
                    print(f"센서 수신기: 알 수 없는 패킷 유형 {packet_type} 무시")
        finally:
            self.store.set_connected(False)

    def _run(self) -> None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                listener.bind((self.host, self.port))
                listener.listen(2)
                listener.settimeout(1.0)
                self.store.set_listener_error(None)
                print(f"ESP32 센서 수신 대기: {self.host}:{self.port}")
                while not self.stop_event.is_set():
                    try:
                        connection, peer = listener.accept()
                    except socket.timeout:
                        continue
                    print(f"ESP32 센서 연결: {peer[0]}:{peer[1]}")
                    with connection:
                        try:
                            self._handle_connection(connection, peer)
                        except (ConnectionError, OSError, ValueError, json.JSONDecodeError) as error:
                            if not self.stop_event.is_set():
                                print(f"ESP32 센서 연결 종료: {error}")
        except OSError as error:
            self.store.set_listener_error(str(error))
            print(f"ESP32 센서 수신기 시작 실패: {error}")


class BuzzerController:
    """Drive a passive piezo buzzer with GPIO Zero's BCM pin numbering."""

    def __init__(
        self,
        pin: int = 18,
        frequency_hz: float = 880.0,
        enabled: bool = True,
    ) -> None:
        self.pin = pin
        self.frequency_hz = frequency_hz
        self.enabled = enabled
        self.available = False
        self.sounding = False
        self.error: str | None = None
        self._device: object | None = None
        self._lock = threading.Lock()

        if not enabled:
            return

        try:
            from gpiozero import TonalBuzzer

            self._device = TonalBuzzer(pin)
            self._device.stop()
            self.available = True
            print(f"피에조 부저 준비 완료: BCM GPIO{pin}, {frequency_hz:g} Hz")
        except Exception as error:  # GPIO support differs between Pi models/images.
            self.error = str(error)
            print(f"피에조 부저 초기화 실패(GPIO{pin}): {error}")

    def set_emergency(self, emergency: bool) -> None:
        with self._lock:
            if self._device is None:
                self.sounding = False
                return
            if emergency == self.sounding:
                return
            try:
                if emergency:
                    self._device.play(self.frequency_hz)
                else:
                    self._device.stop()
                self.sounding = emergency
                self.error = None
                print("피에조 부저: 긴급 경보 ON" if emergency else "피에조 부저: OFF")
            except Exception as error:
                self.sounding = False
                self.error = str(error)
                print(f"피에조 부저 제어 실패(GPIO{self.pin}): {error}")

    def status(self) -> dict[str, object]:
        with self._lock:
            return {
                "enabled": self.enabled,
                "available": self.available,
                "pin_bcm": self.pin,
                "frequency_hz": self.frequency_hz,
                "sounding": self.sounding,
                "error": self.error,
            }

    def close(self) -> None:
        with self._lock:
            if self._device is None:
                return
            try:
                self._device.stop()
                self._device.close()
            except Exception as error:
                self.error = str(error)
                print(f"피에조 부저 종료 실패(GPIO{self.pin}): {error}")
            finally:
                self.sounding = False
                self._device = None


def load_state() -> dict[str, object]:
    try:
        saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        state = saved.get("state")
        room = str(saved.get("room", "")).strip()
        if state in ALLOWED_STATES and room:
            emergency = empty_emergency_state()
            saved_emergency = saved.get("emergency")
            if isinstance(saved_emergency, dict):
                for key in emergency:
                    if key in saved_emergency:
                        emergency[key] = saved_emergency[key]
            return {
                "state": state,
                "room": room[:24],
                "revision": int(saved.get("revision", 1)),
                "updated_at": int(saved.get("updated_at", time.time())),
                "emergency": emergency,
            }
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        pass
    return DEFAULT_STATE.copy()


APP_STATE = load_state()



def persist_state() -> None:
    temporary = STATE_FILE.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(APP_STATE, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, STATE_FILE)


def apply_state_change(
    buzzer: BuzzerController,
    new_state: str | None,
    new_room: str | None,
) -> dict[str, object]:
    """Persist one state update and keep the audible alarm in sync with it."""
    with STATE_LOCK:
        previous_state = str(APP_STATE["state"])
        changed_at = int(time.time())
        if new_state is not None:
            APP_STATE["state"] = new_state
        if new_room is not None:
            APP_STATE["room"] = new_room
        APP_STATE["revision"] = int(APP_STATE["revision"]) + 1
        APP_STATE["updated_at"] = changed_at
        emergency = APP_STATE.setdefault("emergency", empty_emergency_state())
        if new_state == "emergency" and previous_state != "emergency":
            emergency.update(empty_emergency_state())
            emergency.update({"active": True, "entered_at": changed_at})
        elif new_state is not None and previous_state == "emergency" and new_state != "emergency":
            emergency.update({
                "active": False,
                "cleared_at": changed_at,
                "cleared_to": new_state,
                "recovery_pending": True,
                "recovery_acknowledged_at": None,
            })
        try:
            persist_state()
        except OSError as error:
            print(f"상태 파일 저장 실패: {error}")
        buzzer.set_emergency(
            APP_STATE["state"] == "emergency" and emergency.get("acknowledged") is not True
        )
        return APP_STATE.copy()


def acknowledge_display_emergency(buzzer: BuzzerController) -> dict[str, object]:
    with STATE_LOCK:
        emergency = APP_STATE.setdefault("emergency", empty_emergency_state())
        if APP_STATE["state"] != "emergency" or emergency.get("active") is not True:
            raise RuntimeError("확인할 긴급 경보가 없습니다.")
        emergency["acknowledged"] = True
        emergency["acknowledged_at"] = int(time.time())
        APP_STATE["revision"] = int(APP_STATE["revision"]) + 1
        persist_state()
        buzzer.set_emergency(False)
        return APP_STATE.copy()


def acknowledge_display_recovery() -> dict[str, object]:
    with STATE_LOCK:
        emergency = APP_STATE.setdefault("emergency", empty_emergency_state())
        if emergency.get("recovery_pending") is not True:
            raise RuntimeError("확인할 정상 복귀 상태가 없습니다.")
        emergency["recovery_pending"] = False
        emergency["recovery_acknowledged_at"] = int(time.time())
        APP_STATE["revision"] = int(APP_STATE["revision"]) + 1
        persist_state()
        return APP_STATE.copy()


def build_state_response(sensor_store: SensorStore) -> dict[str, object]:
    with STATE_LOCK:
        response = APP_STATE.copy()
    response["sensors"] = sensor_store.snapshot()
    return response


class SafeNestHandler(BaseHTTPRequestHandler):
    server_version = "SafeNestLCD/1.1"

    def log_message(self, format_string: str, *args: object) -> None:
        print(f"[{self.log_date_time_string()}] {self.address_string()} {format_string % args}")

    def send_common_headers(self, content_type: str, length: int) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")

    def send_bytes(
        self,
        body: bytes,
        content_type: str,
        status: HTTPStatus = HTTPStatus.OK,
    ) -> None:
        self.send_response(status)
        self.send_common_headers(content_type, len(body))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_bytes(body, "application/json; charset=utf-8", status)

    def redirect(self, location: str) -> None:
        self.send_response(HTTPStatus.FOUND)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/":
            self.redirect("/control")
            return
        if path == "/control":
            path = "/control.html"
        elif path == "/display":
            path = "/display.html"
        elif path.startswith("/lcd/assets/"):
            # Keep the legacy standalone LCD server compatible with the
            # canonical FastAPI-served LCD pages.
            path = path[len("/lcd/assets/") - 1 :]
        elif path in {"/api/state", "/health"}:
            if path == "/health":
                self.send_json(
                    {
                        "ok": True,
                        "buzzer": self.server.buzzer.status(),
                        "sensors": self.server.sensor_store.snapshot(),
                    }
                )
            else:
                self.send_json(build_state_response(self.server.sensor_store))
            return

        relative = path.lstrip("/")
        requested = (STATIC_DIR / relative).resolve()
        try:
            requested.relative_to(STATIC_DIR.resolve())
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN)
            return

        if not requested.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(requested.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {
            "application/javascript",
            "application/json",
        }:
            content_type += "; charset=utf-8"
        self.send_bytes(requested.read_bytes(), content_type)

    def do_POST(self) -> None:  # noqa: N802
        request_path = urlparse(self.path).path
        if request_path == "/api/emergency/acknowledge":
            try:
                acknowledge_display_emergency(self.server.buzzer)
            except RuntimeError as error:
                self.send_json({"ok": False, "message": str(error)}, HTTPStatus.CONFLICT)
                return
            self.send_json({"ok": True, "emergency": build_state_response(self.server.sensor_store)["emergency"]})
            return
        if request_path == "/api/emergency/recovery/acknowledge":
            try:
                acknowledge_display_recovery()
            except RuntimeError as error:
                self.send_json({"ok": False, "message": str(error)}, HTTPStatus.CONFLICT)
                return
            self.send_json({"ok": True, "emergency": build_state_response(self.server.sensor_store)["emergency"]})
            return
        if request_path != "/api/state":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_json({"error": "잘못된 요청 길이입니다."}, HTTPStatus.BAD_REQUEST)
            return
        if content_length <= 0 or content_length > 4096:
            self.send_json({"error": "요청 크기가 올바르지 않습니다."}, HTTPStatus.BAD_REQUEST)
            return

        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self.send_json({"error": "JSON 형식이 올바르지 않습니다."}, HTTPStatus.BAD_REQUEST)
            return

        if not isinstance(payload, dict):
            self.send_json({"error": "객체 형식의 요청이 필요합니다."}, HTTPStatus.BAD_REQUEST)
            return

        new_state = payload.get("state")
        new_room = payload.get("room")
        if new_state is not None and new_state not in ALLOWED_STATES:
            self.send_json({"error": "지원하지 않는 화면 상태입니다."}, HTTPStatus.BAD_REQUEST)
            return
        if new_room is not None:
            if not isinstance(new_room, str) or not new_room.strip():
                self.send_json({"error": "공간 이름을 입력하세요."}, HTTPStatus.BAD_REQUEST)
                return
            new_room = new_room.strip()[:24]
        if new_state is None and new_room is None:
            self.send_json({"error": "변경할 항목이 없습니다."}, HTTPStatus.BAD_REQUEST)
            return

        apply_state_change(self.server.buzzer, new_state, new_room)
        self.send_json(build_state_response(self.server.sensor_store))


def main() -> None:
    parser = argparse.ArgumentParser(description="SafeNest LCD remote-control server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--buzzer-pin", type=int, default=18)
    parser.add_argument("--buzzer-frequency", type=float, default=880.0)
    parser.add_argument("--disable-buzzer", action="store_true")
    parser.add_argument("--sensor-host", default="0.0.0.0")
    parser.add_argument("--sensor-port", type=int, default=9000)
    parser.add_argument("--sensor-stale-seconds", type=float, default=5.0)
    parser.add_argument("--disable-sensors", action="store_true")
    args = parser.parse_args()

    if args.sensor_stale_seconds <= 0:
        parser.error("--sensor-stale-seconds must be greater than zero")

    buzzer = BuzzerController(
        pin=args.buzzer_pin,
        frequency_hz=args.buzzer_frequency,
        enabled=not args.disable_buzzer,
    )
    buzzer.set_emergency(APP_STATE["state"] == "emergency")
    sensor_store = SensorStore(stale_seconds=args.sensor_stale_seconds)
    sensor_receiver = None
    if not args.disable_sensors:
        sensor_receiver = SensorReceiver(args.sensor_host, args.sensor_port, sensor_store)
        sensor_receiver.start()
    else:
        sensor_store.set_listener_error("sensor receiver disabled")

    server = ThreadingHTTPServer((args.host, args.port), SafeNestHandler)
    server.daemon_threads = True
    server.buzzer = buzzer
    server.sensor_store = sensor_store

    def request_shutdown(signum: int, _frame: object) -> None:
        print(f"종료 신호 수신: {signal.Signals(signum).name}")
        raise KeyboardInterrupt

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)
    print("SafeNest LCD 서버가 시작되었습니다.")
    print(f"LCD 화면: http://127.0.0.1:{args.port}/display")
    print(f"노트북 제어: http://<라즈베리파이-IP>:{args.port}/control")
    if sensor_receiver is not None:
        print(f"ESP32 센서 입력: TCP {args.sensor_host}:{args.sensor_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if sensor_receiver is not None:
            sensor_receiver.stop()
        buzzer.close()
        print("SafeNest LCD 서버를 종료했습니다.")


if __name__ == "__main__":
    main()
