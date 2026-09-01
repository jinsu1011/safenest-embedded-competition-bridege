#!/usr/bin/env python3
"""
SafeNest Raspberry Pi 수신 게이트웨이 (현장 브링업 / 통신 진단 전용)
=====================================================================

무엇인가
--------
ESP32 센서 노드가 보내는 SafeNest TCP v1 (:9000) 스칼라 telemetry 와
SafeNest Thermal UDP v1 (:5005) 열화상 프레임을 **저장소의 Runtime 과 완전히
동일한 규칙으로** 받아서, 들어온 것/거부한 것/왜 거부했는지를 전부 로그로
찍는 단일 파일 프로그램입니다. 표준 라이브러리만 씁니다(설치 불필요).

왜 필요한가
-----------
RaspberryPi/Runtime 의 수신 경로는 실패할 때 **아무것도 출력하지 않습니다.**
- `gateway/protocol.py` 가 ProtocolError 를 던지면 그 TCP 연결만 조용히 끊깁니다.
- 그 오류는 `store.record_runtime_error()` 로 들어가서 `/health` 를 직접
  긁어보기 전에는 화면에 안 나옵니다.
- Thermal UDP 는 CRC/길이/순서가 안 맞으면 카운터만 올리고 버립니다.
결과적으로 "ESP 는 보내는데 대시보드는 비어 있다"가 되고, 어디서 끊겼는지
알 방법이 없습니다. 이 파일이 그 사각지대를 없앱니다.

무엇을 보여주는가
-----------------
  [tcp]      연결/종료, peer, 세션 길이, 세션당 패킷 수
  [pkt]      들어온 telemetry 의 모든 필드 (null 은 null 그대로)
  [reject]   거부 사유 + 위반한 필드 + 실제 값  <-- Runtime 이 숨기던 것
  [gap]      seq 건너뜀 / 역행 / 중복
  [udp]      chunk 수신, 프레임 재조립 성공/실패, CRC, 타임아웃
  [rate]     5초마다: telemetry pps, thermal fps, 바이트, 오류 누계
  [state]    센서별 LIVE/STALE/INVALID/NO_DATA 와 마지막 값 (1초마다)

쓰는 법
-------
    python3 safenest_pi_gateway.py                 # 기본 (9000/5005, 웹 8001)
    python3 safenest_pi_gateway.py --strict         # Runtime 과 동일하게 연결 차단
    python3 safenest_pi_gateway.py --quiet-packets  # [pkt] 줄 끄기
    python3 safenest_pi_gateway.py --no-http        # 웹 상태 페이지 끄기

브라우저:  http://<pi-주소>:8001/         상태 페이지
           http://<pi-주소>:8001/status   JSON
           http://<pi-주소>:8001/thermal.pgm  마지막 열화상 프레임 (PGM)

**중요**: 이 프로그램은 :9000 과 :5005 를 직접 점유합니다. `./run_safenest.sh`
와 **동시에 실행할 수 없습니다.** 브링업 중에는 이것만 켜서 링크를 확정하고,
확정된 뒤에 원래 런타임으로 돌아가세요. 포트가 이미 쓰이고 있으면 시작할 때
어떤 프로세스가 쥐고 있는지까지 알려줍니다.

로그 파일
---------
    ./safenest_logs/gateway-YYYYmmdd-HHMMSS.log     콘솔과 동일한 전체 로그
    ./safenest_logs/telemetry-YYYYmmdd-HHMMSS.jsonl 수신한 telemetry 원본 JSON

Python 3.9+ / Raspberry Pi OS 기본 파이썬으로 동작합니다.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import socket
import struct
import subprocess
import sys
import threading
import time
import zlib
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

# =============================================================================
# 프로토콜 상수 — RaspberryPi/Runtime/gateway/protocol.py 와 반드시 일치
# =============================================================================
MAGIC = b"SNST"
PROTOCOL_VERSION = 1
PACKET_TELEMETRY_JSON = 1
PACKET_THERMAL_U16_BE = 2
HEADER = struct.Struct("!4sBBHII")          # 16 바이트
THERMAL_META = struct.Struct("!HHIIHH")     # 16 바이트
THERMAL_WIDTH = 80
THERMAL_HEIGHT = 62
THERMAL_PIXEL_BYTES = THERMAL_WIDTH * THERMAL_HEIGHT * 2      # 9920
THERMAL_PAYLOAD_BYTES = THERMAL_META.size + THERMAL_PIXEL_BYTES  # 9936
MAX_TELEMETRY_BYTES = 4096
MAX_U32 = 0xFFFFFFFF
EXPECTED_TELEMETRY_SCHEMA = "safenest.telemetry.v1"
ALLOWED_CO2_RANGE_PPM = frozenset({2000, 5000, 10000})

THERMAL_UDP_MAGIC = b"SNTU"
THERMAL_UDP_VERSION = 1
THERMAL_UDP_HEADER = struct.Struct("!4sBBHIHHIIHHI")   # 32 바이트
THERMAL_UDP_HEADER_BYTES = THERMAL_UDP_HEADER.size
THERMAL_UDP_DATAGRAM_BYTES = 1200
THERMAL_UDP_CHUNK_BYTES = THERMAL_UDP_DATAGRAM_BYTES - THERMAL_UDP_HEADER_BYTES  # 1168
THERMAL_UDP_EXPECTED_CHUNKS = math.ceil(THERMAL_PAYLOAD_BYTES / THERMAL_UDP_CHUNK_BYTES)
THERMAL_UDP_MAX_CHUNKS = 16

# Runtime 의 state/manager.py 기본 TTL. 이 값이 대시보드의 LIVE/STALE 을 정합니다.
SENSOR_TTL_SECONDS = {"mmwave": 3.0, "thermal": 3.0, "co2": 10.0, "pir": 10.0}

# ---------------------------------------------------------------------------
# 온디바이스 AI 입력 계약 (RaspberryPi/Runtime/ai 에서 그대로 가져온 상수)
#
#   ai/mmwave_b23_bridge.py   PHASE_AGE_MAX_MS = 1000.0
#   ai/mmwave_b23_runtime.py  R1 300 sample @ 10 Hz  (= 30 s 인과 창)
#                             창은 *새로운* mmwave.seq 에서만 전진합니다.
#                             같은 seq 재전송은 _republish_skip 으로 버려집니다.
#   ai/co2_canonical_runtime.py  h150_model_input_eligible():
#                             measurement_event_valid is True,
#                             measurement_event_id != 0,
#                             latest_measurement_ppm 유한,
#                             preheat_complete **is True**
#                             + 150 s 이상의 이벤트 이력
#   ai/pipeline.py            thermal 은 프레임 1장이면 즉시 추론
#
# 이 게이트웨이는 모델을 돌리지 않습니다(그건 run_safenest.sh 의 Runtime 몫).
# 대신 "모델이 돌 수 있는 입력이 실제로 도착하고 있는가"를 판정해서 보여줍니다.
# 대시보드에 WINDOW_NOT_READY / INPUT_UNAVAILABLE 이 뜰 때, 그게 센서 문제인지
# 그냥 아직 창이 안 찬 것인지 여기서 갈립니다.
# ---------------------------------------------------------------------------
B23_PHASE_AGE_MAX_MS = 1000.0
B23_WINDOW_SAMPLES = 300
B23_SAMPLE_RATE_HZ = 10.0
H150_WINDOW_SECONDS = 150.0

ANSI = {
    "reset": "\033[0m", "dim": "\033[2m", "bold": "\033[1m",
    "red": "\033[31m", "green": "\033[32m", "yellow": "\033[33m",
    "blue": "\033[34m", "magenta": "\033[35m", "cyan": "\033[36m",
}


# =============================================================================
# 로깅
# =============================================================================
class Logger:
    """콘솔 + 파일 동시 출력. 색은 tty 일 때만."""

    LEVEL_COLOR = {
        "TCP": "cyan", "UDP": "magenta", "PKT": "dim", "REJECT": "red",
        "GAP": "yellow", "RATE": "blue", "STATE": "green", "WARN": "yellow",
        "ERROR": "red", "INFO": "reset", "HTTP": "dim", "AI": "cyan",
    }

    def __init__(self, log_path: Path | None, use_color: bool) -> None:
        self._lock = threading.Lock()
        self._file = log_path.open("a", encoding="utf-8") if log_path else None
        self._color = use_color
        self.start_monotonic = time.monotonic()

    def __call__(self, tag: str, message: str) -> None:
        elapsed = time.monotonic() - self.start_monotonic
        stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        line = f"{stamp} +{elapsed:8.3f}s [{tag:<6}] {message}"
        with self._lock:
            if self._color:
                color = ANSI.get(self.LEVEL_COLOR.get(tag, "reset"), ANSI["reset"])
                sys.stdout.write(f"{color}{line}{ANSI['reset']}\n")
            else:
                sys.stdout.write(line + "\n")
            sys.stdout.flush()
            if self._file is not None:
                self._file.write(line + "\n")
                self._file.flush()

    def close(self) -> None:
        with self._lock:
            if self._file is not None:
                self._file.close()
                self._file = None


LOG: Logger  # main() 에서 설정


# =============================================================================
# 오류 타입
# =============================================================================
class ProtocolError(ValueError):
    """peer 가 SafeNest TCP v1 을 위반했습니다. field/value 를 항상 함께 실어 나릅니다."""

    def __init__(self, rule: str, field: str = "", value: Any = None) -> None:
        detail = f"{rule}"
        if field:
            detail += f"  field={field}"
        if value is not None:
            detail += f"  value={value!r}"
        super().__init__(detail)
        self.rule = rule
        self.field = field
        self.value = value


class ConnectionClosed(ProtocolError):
    pass


class ThermalUDPError(ProtocolError):
    pass


# =============================================================================
# telemetry 디코더 — Runtime protocol.py 와 규칙 동일, 단 오류에 필드/값을 담음
# =============================================================================
def _u32(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ProtocolError("정수여야 합니다", field, value)
    if not 0 <= value <= MAX_U32:
        raise ProtocolError("uint32 범위를 벗어났습니다", field, value)
    return value


def _optional_finite(value: Any, field: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolError("숫자 또는 null 이어야 합니다", field, value)
    converted = float(value)
    if not math.isfinite(converted):
        raise ProtocolError("유한한 값이어야 합니다 (NaN/Inf 금지)", field, value)
    return converted


def _optional_bool(value: Any, field: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ProtocolError("boolean 이어야 합니다", field, value)
    return value


def _optional_identifier(value: Any, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value) > 64:
        raise ProtocolError("1~64자 문자열이어야 합니다", field, value)
    if any(not (ch.isalnum() or ch in "-_.:") for ch in value):
        raise ProtocolError(
            "영숫자와 - _ . : 만 허용됩니다 (Runtime 의 _optional_identifier 규칙)",
            field, value,
        )
    return value


def decode_header(data: bytes) -> tuple[int, int, int]:
    """(packet_type, sequence, payload_length) 반환."""
    if len(data) != HEADER.size:
        raise ProtocolError(f"헤더는 {HEADER.size} 바이트여야 합니다", "header", len(data))
    magic, version, packet_type, flags, sequence, payload_length = HEADER.unpack(data)
    if magic != MAGIC:
        raise ProtocolError(
            "magic 이 'SNST' 가 아닙니다. 스트림 동기가 깨졌거나 다른 프로그램이 "
            "이 포트로 접속했습니다",
            "magic", magic,
        )
    if version != PROTOCOL_VERSION:
        raise ProtocolError("지원하지 않는 프로토콜 버전", "version", version)
    if flags != 0:
        raise ProtocolError("v1 에서 flags 는 0 이어야 합니다", "flags", flags)
    if packet_type == PACKET_TELEMETRY_JSON:
        if not 0 < payload_length <= MAX_TELEMETRY_BYTES:
            raise ProtocolError(
                f"telemetry payload 길이는 1..{MAX_TELEMETRY_BYTES} 여야 합니다",
                "payload_length", payload_length,
            )
    elif packet_type == PACKET_THERMAL_U16_BE:
        if payload_length != THERMAL_PAYLOAD_BYTES:
            raise ProtocolError(
                f"thermal payload 는 {THERMAL_PAYLOAD_BYTES} 바이트여야 합니다",
                "payload_length", payload_length,
            )
    else:
        raise ProtocolError("알 수 없는 packet type", "type", packet_type)
    return packet_type, sequence, payload_length


def decode_telemetry(sequence: int, payload: bytes) -> dict[str, Any]:
    """Runtime 과 동일한 검사. 통과하면 Runtime 도 반드시 통과합니다."""
    try:
        decoded = json.loads(payload.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise ProtocolError(f"UTF-8 디코딩 실패: {exc}", "payload") from exc
    except json.JSONDecodeError as exc:
        raise ProtocolError(
            f"JSON 파싱 실패: {exc}", "payload", payload[:120]
        ) from exc
    if not isinstance(decoded, dict):
        raise ProtocolError("JSON 최상위는 객체여야 합니다", "root", type(decoded).__name__)

    if decoded.get("schema") != EXPECTED_TELEMETRY_SCHEMA:
        raise ProtocolError(
            f"schema 는 '{EXPECTED_TELEMETRY_SCHEMA}' 여야 합니다",
            "schema", decoded.get("schema"),
        )

    device_id = decoded.get("device_id")
    if not isinstance(device_id, str) or not device_id or len(device_id) > 64:
        raise ProtocolError("device_id 는 1~64자 문자열", "device_id", device_id)

    json_sequence = _u32(decoded.get("seq"), "seq")
    if json_sequence != sequence:
        raise ProtocolError(
            "바이너리 헤더 sequence 와 JSON seq 가 다릅니다 (펌웨어 버그 신호)",
            "seq", f"header={sequence} json={json_sequence}",
        )
    uptime_ms = _u32(decoded.get("uptime_ms"), "uptime_ms")
    boot_id = _optional_identifier(decoded.get("boot_id"), "boot_id")

    valid_raw = decoded.get("valid")
    if not isinstance(valid_raw, dict):
        raise ProtocolError("valid 는 객체여야 합니다", "valid", valid_raw)
    valid: dict[str, bool] = {}
    for key in ("respiration", "heart", "co2"):
        value = valid_raw.get(key)
        if not isinstance(value, bool):
            raise ProtocolError("boolean 이어야 합니다", f"valid.{key}", value)
        valid[key] = value

    respiration = _optional_finite(decoded.get("resp_rate_bpm"), "resp_rate_bpm")
    heart = _optional_finite(decoded.get("heart_rate_bpm"), "heart_rate_bpm")
    co2 = _optional_finite(decoded.get("co2_ppm"), "co2_ppm")
    # 이 교차검증이 현장에서 제일 자주 걸립니다: valid 플래그와 값이 어긋나면
    # Runtime 은 연결 자체를 끊습니다.
    for key, is_valid, value in (
        ("respiration", valid["respiration"], respiration),
        ("heart", valid["heart"], heart),
        ("co2", valid["co2"], co2),
    ):
        if is_valid != (value is not None):
            raise ProtocolError(
                "valid 플래그와 값이 어긋납니다 (valid=true 면 값이 있어야 하고, "
                "valid=false 면 반드시 null 이어야 합니다)",
                f"valid.{key}", f"valid={is_valid} value={value}",
            )

    pir_motion = decoded.get("pir_motion")
    if not isinstance(pir_motion, bool):
        raise ProtocolError("boolean 이어야 합니다", "pir_motion", pir_motion)

    co2_event = _event_provenance(
        decoded, "co2_measurement_event_id", "co2_measurement_monotonic_ms",
        "co2_measurement_event_valid", boot_id,
    )
    pir_event = _transition_provenance(
        decoded, "pir_event_id", "pir_last_transition_monotonic_ms", boot_id,
    )

    nested = decoded.get("mmwave")
    if nested is not None and not isinstance(nested, dict):
        raise ProtocolError("mmwave 는 객체여야 합니다", "mmwave", nested)

    def promoted_finite(field: str) -> float | None:
        if field in decoded:
            return _optional_finite(decoded.get(field), field)
        if nested is not None and field in nested:
            return _optional_finite(nested.get(field), f"mmwave.{field}")
        return None

    def promoted_bool(field: str) -> bool | None:
        if field in decoded:
            return _optional_bool(decoded.get(field), field)
        if nested is not None and field in nested:
            return _optional_bool(nested.get(field), f"mmwave.{field}")
        return None

    mmwave_sequence: int | None = None
    if "mmwave_sequence" in decoded and decoded["mmwave_sequence"] is not None:
        mmwave_sequence = _u32(decoded["mmwave_sequence"], "mmwave_sequence")
    elif nested is not None and nested.get("seq") is not None:
        mmwave_sequence = _u32(nested["seq"], "mmwave.seq")

    co2_range = decoded.get("configured_range_ppm")
    if co2_range is not None:
        if isinstance(co2_range, bool) or not isinstance(co2_range, int):
            raise ProtocolError("정수여야 합니다", "configured_range_ppm", co2_range)
        if co2_range not in ALLOWED_CO2_RANGE_PPM:
            raise ProtocolError(
                "2000 / 5000 / 10000 중 하나여야 합니다",
                "configured_range_ppm", co2_range,
            )

    preheat_complete: bool | None
    if "co2_preheat_complete" in decoded:
        preheat_complete = _optional_bool(
            decoded.get("co2_preheat_complete"), "co2_preheat_complete"
        )
    elif "co2_preheat" in decoded:
        # 현재 펌웨어는 co2_preheat 만 보냅니다. Runtime 이 같은 의미로 매핑합니다.
        preheat_complete = _optional_bool(decoded.get("co2_preheat"), "co2_preheat")
    else:
        preheat_complete = None

    return {
        "sequence": sequence,
        "device_id": device_id,
        "boot_id": boot_id,
        "uptime_ms": uptime_ms,
        "firmware_version": decoded.get("firmware_version"),
        "resp_rate_bpm": respiration,
        "heart_rate_bpm": heart,
        "co2_ppm": co2,
        "pir_motion": pir_motion,
        "valid": valid,
        "co2_measurement_event_id": co2_event[0],
        "co2_measurement_monotonic_ms": co2_event[1],
        "co2_measurement_event_valid": co2_event[2],
        "pir_event_id": pir_event[0],
        "pir_last_transition_monotonic_ms": pir_event[1],
        "co2_sensor_model": _optional_identifier(
            decoded.get("co2_sensor_model"), "co2_sensor_model"
        ),
        "co2_event_identity_class": _optional_identifier(
            decoded.get("co2_event_identity_class"), "co2_event_identity_class"
        ),
        "co2_preheat_complete": preheat_complete,
        "breath_phase": promoted_finite("breath_phase"),
        "total_phase": promoted_finite("total_phase"),
        "heart_phase": promoted_finite("heart_phase"),
        "breath_rate_raw": promoted_finite("breath_rate_raw"),
        "ts_monotonic_ms": promoted_finite("ts_monotonic_ms"),
        "phase_age_ms": promoted_finite("phase_age_ms"),
        "human_detected_raw": promoted_bool("human_detected_raw"),
        "mmwave_sequence": mmwave_sequence,
        "health": decoded.get("health") if isinstance(decoded.get("health"), dict) else None,
        "_raw": decoded,
    }


def _event_provenance(
    document: dict[str, Any], id_field: str, time_field: str,
    valid_field: str, boot_id: str | None,
) -> tuple[int | None, int | None, bool | None]:
    present = tuple(field in document for field in (id_field, time_field, valid_field))
    if not any(present):
        return None, None, None
    if not all(present):
        raise ProtocolError(
            "세 필드는 항상 함께 나와야 합니다",
            f"{id_field}/{time_field}/{valid_field}", present,
        )
    event_id = _u32(document[id_field], id_field)
    event_ms = _u32(document[time_field], time_field)
    event_valid = document[valid_field]
    if not isinstance(event_valid, bool):
        raise ProtocolError("boolean 이어야 합니다", valid_field, event_valid)
    if event_valid:
        if event_id == 0:
            raise ProtocolError(
                f"{valid_field}=true 이면 0 이 아니어야 합니다", id_field, event_id
            )
        if boot_id is None:
            raise ProtocolError(
                f"{valid_field}=true 이면 boot_id 가 필요합니다", "boot_id", None
            )
    elif event_id != 0 or event_ms != 0:
        raise ProtocolError(
            f"{valid_field}=false 이면 id 와 time 이 둘 다 0 이어야 합니다",
            f"{id_field}/{time_field}", (event_id, event_ms),
        )
    return event_id, event_ms, event_valid


def _transition_provenance(
    document: dict[str, Any], id_field: str, time_field: str, boot_id: str | None,
) -> tuple[int | None, int | None]:
    present = (id_field in document, time_field in document)
    if not any(present):
        return None, None
    if not all(present):
        raise ProtocolError("두 필드는 함께 나와야 합니다", f"{id_field}/{time_field}", present)
    event_id = _u32(document[id_field], id_field)
    event_ms = _u32(document[time_field], time_field)
    if event_id == 0:
        if event_ms != 0:
            raise ProtocolError("첫 전환 전에는 0 이어야 합니다", time_field, event_ms)
    elif boot_id is None:
        raise ProtocolError(f"{id_field} 가 0 이 아니면 boot_id 필요", "boot_id", None)
    return event_id, event_ms


def decode_thermal_payload(sequence: int, payload: bytes) -> dict[str, Any]:
    if len(payload) != THERMAL_PAYLOAD_BYTES:
        raise ProtocolError(
            f"thermal payload 는 {THERMAL_PAYLOAD_BYTES} 바이트여야 합니다",
            "payload", len(payload),
        )
    width, height, frame_sequence, uptime_ms, minimum_raw, maximum_raw = (
        THERMAL_META.unpack_from(payload)
    )
    if (width, height) != (THERMAL_WIDTH, THERMAL_HEIGHT):
        raise ProtocolError("해상도가 80x62 가 아닙니다", "width/height", (width, height))
    if frame_sequence != sequence:
        raise ProtocolError(
            "envelope frame_id 와 metadata frame_sequence 가 다릅니다",
            "frame_sequence", f"envelope={sequence} meta={frame_sequence}",
        )
    if minimum_raw > maximum_raw:
        raise ProtocolError(
            "minimum_raw 가 maximum_raw 보다 큽니다", "min/max", (minimum_raw, maximum_raw)
        )

    pixel_bytes = payload[THERMAL_META.size:]
    actual_min = 0xFFFF
    actual_max = 0
    for (pixel,) in struct.iter_unpack("!H", pixel_bytes):
        if pixel < actual_min:
            actual_min = pixel
        if pixel > actual_max:
            actual_max = pixel
    if (minimum_raw, maximum_raw) != (actual_min, actual_max):
        # Runtime 이 프레임을 통째로 버리는 지점. ESP 가 min/max 를 픽셀과 다른
        # 시점에 계산했거나 SPI 캡처가 중간에 깨졌다는 뜻입니다.
        raise ProtocolError(
            "metadata 의 min/max 가 실제 픽셀과 다릅니다",
            "min/max",
            f"meta=({minimum_raw},{maximum_raw}) pixels=({actual_min},{actual_max})",
        )
    return {
        "frame_sequence": frame_sequence,
        "uptime_ms": uptime_ms,
        "minimum_raw": minimum_raw,
        "maximum_raw": maximum_raw,
        "pixel_bytes": pixel_bytes,
    }


# =============================================================================
# 센서 상태 (Runtime state/manager.py 의 freshness 규칙을 그대로 재현)
# =============================================================================
class SensorState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.records: dict[str, dict[str, Any]] = {
            name: {
                "status": "NO_DATA", "valid": False, "connected": False,
                "last_monotonic": None, "values": {}, "peer": None, "error": None,
            }
            for name in ("mmwave", "thermal", "co2", "pir")
        }
        self.latest_thermal: dict[str, Any] | None = None
        self.device_health: dict[str, Any] | None = None
        self.last_telemetry: dict[str, Any] | None = None
        self.co2_events = 0
        self._last_co2_event_key: tuple | None = None
        # 온디바이스 AI 입력 추적
        self.ai = {
            "b23_distinct_phase_events": 0,   # 새 mmwave.seq 로 창을 전진시킨 횟수
            "b23_republished_skips": 0,       # 같은 seq 재전송 (Pi 가 버리는 것)
            "b23_phase_missing": 0,           # breath_phase == null
            "b23_phase_stale": 0,             # phase_age_ms > 1000
            "b23_seq_missing": 0,             # mmwave.seq 없음
            "b23_boot_resets": 0,             # boot_id 변경 -> 창 초기화
            "h150_eligible_events": 0,        # C-B6 입력 자격을 갖춘 측정 이벤트
            "h150_blocked_preheat": 0,        # preheat_complete != True 로 탈락
            "h150_first_monotonic": None,
            "h150_last_monotonic": None,
        }
        self._last_phase_seq: int | None = None
        self._last_boot_id: str | None = None

    def ingest_telemetry(self, packet: dict[str, Any], peer: str) -> None:
        now = time.monotonic()
        with self._lock:
            self.last_telemetry = packet
            self.device_health = packet.get("health")

            # mmwave: phase 소스가 구조적으로 완전하거나, 벤더 호흡/심박이 유효하면 valid.
            phase_ok = (
                _is_number(packet["breath_phase"])
                and _is_number(packet["ts_monotonic_ms"])
                and _is_number(packet["phase_age_ms"])
                and isinstance(packet["mmwave_sequence"], int)
            )
            mmwave_valid = phase_ok or packet["valid"]["respiration"] or packet["valid"]["heart"]
            self._set("mmwave", peer, now, mmwave_valid,
                      None if mmwave_valid else "MMWAVE_VALUES_INVALID",
                      {
                          "respiration_rate_bpm": packet["resp_rate_bpm"],
                          "heart_rate_bpm": packet["heart_rate_bpm"],
                          "breath_phase": packet["breath_phase"],
                          "phase_age_ms": packet["phase_age_ms"],
                          "mmwave_sequence": packet["mmwave_sequence"],
                          "human_detected_raw": packet["human_detected_raw"],
                          "phase_source_complete": phase_ok,
                      })

            self._set("co2", peer, now, packet["valid"]["co2"],
                      None if packet["valid"]["co2"] else "CO2_VALUE_INVALID",
                      {
                          "ppm": packet["co2_ppm"],
                          "sensor_model": packet["co2_sensor_model"],
                          "event_identity_class": packet["co2_event_identity_class"],
                          "preheat_complete": packet["co2_preheat_complete"],
                          "measurement_event_id": packet["co2_measurement_event_id"],
                          "measurement_event_valid": packet["co2_measurement_event_valid"],
                      })

            key = None
            if (packet["co2_measurement_event_valid"] is True
                    and packet["boot_id"] is not None
                    and packet["co2_measurement_event_id"]):
                key = (packet["device_id"], packet["boot_id"],
                       packet["co2_measurement_event_id"])
            if key is not None and key != self._last_co2_event_key:
                self._last_co2_event_key = key
                self.co2_events += 1
                self.records["co2"]["values"]["measurement_event_count"] = self.co2_events

            self._set("pir", peer, now, True, None, {"motion": packet["pir_motion"]})
            self._track_ai_inputs(packet, now)

    def _track_ai_inputs(self, packet: dict[str, Any], now: float) -> None:
        """Runtime 의 B23 _admit() 과 h150_model_input_eligible() 을 그대로 흉내냅니다."""
        ai = self.ai

        boot = packet["boot_id"]
        if boot is not None and self._last_boot_id is not None and boot != self._last_boot_id:
            # ESP 재부팅. Pi 는 여기서 이미 찬 창을 통째로 버립니다.
            ai["b23_boot_resets"] += 1
            ai["b23_distinct_phase_events"] = 0
            self._last_phase_seq = None
            LOG("WARN", f"boot_id 변경 감지 ({self._last_boot_id[:8]} -> {boot[:8]}) "
                        f"— mmWave B23 300-sample 창이 초기화됩니다. ESP32 가 "
                        f"재부팅했다는 뜻입니다")
        if boot is not None:
            self._last_boot_id = boot

        # --- mmWave B23 phase 창 ---
        if not _is_number(packet["breath_phase"]):
            ai["b23_phase_missing"] += 1
        elif not (_is_number(packet["phase_age_ms"])
                  and 0.0 <= float(packet["phase_age_ms"]) <= B23_PHASE_AGE_MAX_MS):
            ai["b23_phase_stale"] += 1
        elif not isinstance(packet["mmwave_sequence"], int):
            ai["b23_seq_missing"] += 1
        elif packet["mmwave_sequence"] == self._last_phase_seq:
            # 같은 phase 이벤트의 재전송. 10 Hz 로 보내도 창은 안 전진합니다.
            ai["b23_republished_skips"] += 1
        else:
            self._last_phase_seq = packet["mmwave_sequence"]
            ai["b23_distinct_phase_events"] += 1

        # --- CO2 C-B6 / H150 ---
        if packet["co2_measurement_event_valid"] is True and packet["co2_measurement_event_id"]:
            if packet["co2_preheat_complete"] is True and _is_number(packet["co2_ppm"]):
                ai["h150_eligible_events"] += 1
                if ai["h150_first_monotonic"] is None:
                    ai["h150_first_monotonic"] = now
                ai["h150_last_monotonic"] = now
            else:
                ai["h150_blocked_preheat"] += 1

    def ai_readiness(self) -> dict[str, Any]:
        with self._lock:
            ai = dict(self.ai)
        window_span = (
            0.0 if ai["h150_first_monotonic"] is None
            else ai["h150_last_monotonic"] - ai["h150_first_monotonic"]
        )
        return {
            "mmwave_b23": {
                "distinct_phase_events": ai["b23_distinct_phase_events"],
                "window_samples_required": B23_WINDOW_SAMPLES,
                "window_ready": ai["b23_distinct_phase_events"] >= B23_WINDOW_SAMPLES,
                "republished_skips": ai["b23_republished_skips"],
                "phase_missing": ai["b23_phase_missing"],
                "phase_stale": ai["b23_phase_stale"],
                "sequence_missing": ai["b23_seq_missing"],
                "boot_resets": ai["b23_boot_resets"],
            },
            "co2_c_b6": {
                "eligible_events": ai["h150_eligible_events"],
                "blocked_by_preheat_or_value": ai["h150_blocked_preheat"],
                "history_span_seconds": round(window_span, 1),
                "history_required_seconds": H150_WINDOW_SECONDS,
                "window_ready": window_span >= H150_WINDOW_SECONDS,
            },
            "thermal": {
                "frames_received": STATS.udp_frames_ok,
                "ready": self.latest_thermal is not None,
            },
        }

    def ingest_thermal(self, frame: dict[str, Any], peer: str) -> None:
        now = time.monotonic()
        with self._lock:
            self.latest_thermal = frame
            self._set("thermal", peer, now, True, None, {
                "frame_sequence": frame["frame_sequence"],
                "minimum_raw": frame["minimum_raw"],
                "maximum_raw": frame["maximum_raw"],
                "width": THERMAL_WIDTH, "height": THERMAL_HEIGHT,
            })

    def mark_disconnected(self, peer: str) -> None:
        with self._lock:
            for record in self.records.values():
                if record["peer"] == peer:
                    record["connected"] = False

    def _set(self, name: str, peer: str, now: float, valid: bool,
             error: str | None, values: dict[str, Any]) -> None:
        record = self.records[name]
        record.update({
            "connected": True, "valid": valid, "peer": peer,
            "last_monotonic": now, "error": error,
        })
        record["values"].update(values)

    def snapshot(self) -> dict[str, Any]:
        now = time.monotonic()
        with self._lock:
            sensors = {}
            for name, record in self.records.items():
                ttl = SENSOR_TTL_SECONDS[name]
                if record["last_monotonic"] is None:
                    status, age, stale = "NO_DATA", None, False
                else:
                    age = max(0.0, now - record["last_monotonic"])
                    stale = age > ttl
                    if not record["connected"]:
                        status = "DISCONNECTED"
                    elif stale:
                        status = "STALE"
                    elif not record["valid"]:
                        status = "INVALID"
                    else:
                        status = "LIVE"
                sensors[name] = {
                    "status": status, "age_seconds": age, "ttl_seconds": ttl,
                    "stale": stale, "valid": record["valid"],
                    "connected": record["connected"], "peer": record["peer"],
                    "error": record["error"], "values": dict(record["values"]),
                }
            statuses = [entry["status"] for entry in sensors.values()]
            if statuses.count("LIVE") == len(sensors):
                system = "ONLINE"
            elif any(entry["connected"] for entry in sensors.values()):
                system = "DEGRADED"
            else:
                system = "OFFLINE"
            return {
                "timestamp": time.time(), "system": system, "sensors": sensors,
                "device_health": self.device_health,
                "co2_measurement_events": self.co2_events,
                "thermal_available": self.latest_thermal is not None,
            }

    def thermal_pgm(self) -> bytes | None:
        """마지막 프레임을 8비트 PGM 으로. 눈으로 바로 확인할 수 있는 최소 형식."""
        with self._lock:
            frame = self.latest_thermal
        if frame is None:
            return None
        low, high = frame["minimum_raw"], frame["maximum_raw"]
        span = max(1, high - low)
        pixels = bytearray()
        for (value,) in struct.iter_unpack("!H", frame["pixel_bytes"]):
            pixels.append(min(255, max(0, (value - low) * 255 // span)))
        header = f"P5\n{THERMAL_WIDTH} {THERMAL_HEIGHT}\n255\n".encode("ascii")
        return header + bytes(pixels)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


# =============================================================================
# 통계
# =============================================================================
class Stats:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.tcp_connections = 0
        self.tcp_disconnects = 0
        self.telemetry_packets = 0
        self.telemetry_bytes = 0
        self.protocol_errors = 0
        self.sequence_gaps = 0
        self.sequence_errors = 0
        self.udp_datagrams = 0
        self.udp_invalid = 0
        self.udp_frames_ok = 0
        self.udp_frames_dropped = 0
        self.udp_crc_failures = 0
        self.udp_timeouts = 0
        self.udp_duplicates = 0
        self.udp_out_of_order = 0
        self.udp_bytes = 0
        self.reject_reasons: dict[str, int] = {}
        self.telemetry_arrivals: deque[float] = deque(maxlen=512)
        self.thermal_arrivals: deque[float] = deque(maxlen=256)
        self.max_telemetry_gap_ms = 0.0
        self._last_telemetry_monotonic: float | None = None

    def note_telemetry(self, size: int) -> None:
        now = time.monotonic()
        with self.lock:
            self.telemetry_packets += 1
            self.telemetry_bytes += size
            self.telemetry_arrivals.append(now)
            if self._last_telemetry_monotonic is not None:
                gap_ms = (now - self._last_telemetry_monotonic) * 1000.0
                self.max_telemetry_gap_ms = max(self.max_telemetry_gap_ms, gap_ms)
            self._last_telemetry_monotonic = now

    def note_thermal(self) -> None:
        with self.lock:
            self.udp_frames_ok += 1
            self.thermal_arrivals.append(time.monotonic())

    def note_reject(self, rule: str) -> None:
        with self.lock:
            self.protocol_errors += 1
            self.reject_reasons[rule] = self.reject_reasons.get(rule, 0) + 1

    @staticmethod
    def _rate(samples: deque[float], window: float = 5.0) -> float:
        now = time.monotonic()
        recent = [t for t in samples if now - t <= window]
        return len(recent) / window if recent else 0.0

    def rates(self) -> tuple[float, float]:
        with self.lock:
            return self._rate(self.telemetry_arrivals), self._rate(self.thermal_arrivals)


STATS = Stats()


# =============================================================================
# TCP 수신
# =============================================================================
def recv_exact(connection: socket.socket, size: int, deadline_seconds: float,
               idle_deadline_seconds: float | None) -> bytes:
    """정확히 size 바이트. 짧은 recv 타임아웃이 이미 읽은 바이트를 버리지 않습니다."""
    if size == 0:
        return b""
    buffer = bytearray()
    idle_deadline = (None if idle_deadline_seconds is None
                     else time.monotonic() + idle_deadline_seconds)
    frame_deadline: float | None = None
    while len(buffer) < size:
        now = time.monotonic()
        if not buffer:
            if idle_deadline is not None and now >= idle_deadline:
                raise ProtocolError(
                    "수신 대기 시간 초과 (한 바이트도 못 받음)",
                    "recv", f"0/{size} bytes",
                )
        elif frame_deadline is not None and now >= frame_deadline:
            raise ProtocolError(
                "필드 완성 데드라인 초과 — 반쪽 패킷이 도착했습니다. "
                "ESP 의 TCP write 가 중간에 멈췄다는 뜻입니다",
                "recv", f"{len(buffer)}/{size} bytes",
            )
        try:
            chunk = connection.recv(size - len(buffer))
        except socket.timeout:
            continue
        except OSError as exc:
            raise ConnectionClosed(f"소켓 수신 실패: {exc}", "socket") from exc
        if not chunk:
            raise ConnectionClosed(
                "peer 가 연결을 닫았습니다", "recv", f"{len(buffer)}/{size} bytes"
            )
        buffer.extend(chunk)
        if frame_deadline is None:
            frame_deadline = time.monotonic() + deadline_seconds
    return bytes(buffer)


class TCPGateway(threading.Thread):
    def __init__(self, state: SensorState, host: str, port: int, *,
                 strict: bool, packet_deadline: float, log_packets: bool,
                 jsonl: Path | None) -> None:
        super().__init__(name="safenest-tcp", daemon=True)
        self.state = state
        self.host = host
        self.port = port
        self.strict = strict
        self.packet_deadline = packet_deadline
        self.log_packets = log_packets
        self.stop_event = threading.Event()
        self._listener: socket.socket | None = None
        self._jsonl = jsonl.open("a", encoding="utf-8") if jsonl else None

    def run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
            self._listener = listener
            listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                listener.bind((self.host, self.port))
            except OSError as exc:
                LOG("ERROR", f"TCP :{self.port} 바인드 실패: {exc}")
                report_port_holder(self.port, "tcp")
                self.stop_event.set()
                return
            listener.listen(16)
            listener.settimeout(0.5)
            LOG("TCP", f"listening on {self.host}:{self.port} "
                       f"(strict={'on' if self.strict else 'off'})")
            while not self.stop_event.is_set():
                try:
                    connection, peer = listener.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                connection.settimeout(0.25)
                _enable_keepalive(connection)
                threading.Thread(
                    target=self._serve, args=(connection, peer),
                    name=f"tcp-{peer[0]}:{peer[1]}", daemon=True,
                ).start()

    def _serve(self, connection: socket.socket, peer: tuple[str, int]) -> None:
        label = f"{peer[0]}:{peer[1]}"
        started = time.monotonic()
        packets = 0
        with STATS.lock:
            STATS.tcp_connections += 1
        LOG("TCP", f"connected  peer={label}  (누적 연결 {STATS.tcp_connections}회)")
        last_sequence: dict[int, int] = {}
        try:
            while not self.stop_event.is_set():
                # 첫 바이트는 무한 대기합니다. ESP 가 스냅샷 한 번을 건너뛰었다고
                # 살아 있는 소켓을 닫으면 재접속 폭풍이 생깁니다.
                header_bytes = recv_exact(connection, HEADER.size, self.packet_deadline, None)
                packet_type, sequence, payload_length = decode_header(header_bytes)
                payload = recv_exact(connection, payload_length,
                                     self.packet_deadline, self.packet_deadline)

                previous = last_sequence.get(packet_type)
                last_sequence[packet_type] = sequence
                if previous is not None:
                    delta = (sequence - previous) & MAX_U32
                    if delta == 0:
                        with STATS.lock:
                            STATS.sequence_errors += 1
                        LOG("GAP", f"peer={label} type={packet_type} "
                                   f"중복 sequence {sequence} — Runtime 은 여기서 연결을 끊습니다")
                        if self.strict:
                            raise ProtocolError("중복 sequence", "seq", sequence)
                    elif delta >= 0x80000000:
                        with STATS.lock:
                            STATS.sequence_errors += 1
                        LOG("GAP", f"peer={label} type={packet_type} "
                                   f"sequence 역행 {previous} -> {sequence}")
                        if self.strict:
                            raise ProtocolError("sequence 역행", "seq", sequence)
                    elif delta > 1:
                        with STATS.lock:
                            STATS.sequence_gaps += delta - 1
                        LOG("GAP", f"peer={label} type={packet_type} "
                                   f"{delta - 1}개 패킷 유실 ({previous} -> {sequence})")

                if packet_type == PACKET_TELEMETRY_JSON:
                    packet = decode_telemetry(sequence, payload)
                    STATS.note_telemetry(HEADER.size + payload_length)
                    self.state.ingest_telemetry(packet, label)
                    packets += 1
                    if self._jsonl is not None:
                        self._jsonl.write(json.dumps(
                            {"received_at": time.time(), "peer": label,
                             "packet": packet["_raw"]}, ensure_ascii=False) + "\n")
                        self._jsonl.flush()
                    if self.log_packets:
                        LOG("PKT", format_packet(packet))
                else:
                    # Thermal 은 UDP 로 옵니다. TCP 로 오면 펌웨어 설정이 틀린 것.
                    LOG("WARN", f"peer={label} thermal 프레임이 TCP 로 왔습니다. "
                                f"펌웨어의 THERMAL_UDP_PORT 설정을 확인하세요")

        except ConnectionClosed as exc:
            with STATS.lock:
                STATS.tcp_disconnects += 1
            LOG("TCP", f"closed     peer={label}  session={time.monotonic() - started:.1f}s "
                       f"packets={packets}  reason={exc}")
        except ProtocolError as exc:
            STATS.note_reject(exc.rule)
            with STATS.lock:
                STATS.tcp_disconnects += 1
            LOG("REJECT", f"peer={label} 프로토콜 위반 -> {exc}")
            LOG("REJECT", f"peer={label} 이 오류가 실제 Runtime 에서는 아무 메시지 없이 "
                          f"연결만 끊깁니다. session={time.monotonic() - started:.1f}s "
                          f"packets={packets}")
        except Exception as exc:  # noqa: BLE001 - 진단 도구는 절대 죽으면 안 됩니다
            LOG("ERROR", f"peer={label} 예상치 못한 오류: {type(exc).__name__}: {exc}")
        finally:
            self.state.mark_disconnected(label)
            try:
                connection.close()
            except OSError:
                pass

    def stop(self) -> None:
        self.stop_event.set()
        if self._listener is not None:
            try:
                self._listener.close()
            except OSError:
                pass
        if self._jsonl is not None:
            self._jsonl.close()


def _enable_keepalive(connection: socket.socket, idle: int = 30) -> None:
    try:
        connection.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        if hasattr(socket, "TCP_KEEPIDLE"):
            connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle)
        if hasattr(socket, "TCP_KEEPINTVL"):
            connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 5)
        if hasattr(socket, "TCP_KEEPCNT"):
            connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
    except OSError:
        pass


def format_packet(packet: dict[str, Any]) -> str:
    def number(value: Any, digits: int = 2) -> str:
        return "null" if value is None else f"{value:.{digits}f}"

    return (
        f"seq={packet['sequence']:<7} up={packet['uptime_ms'] / 1000:7.1f}s "
        f"resp={number(packet['resp_rate_bpm']):>6} "
        f"heart={number(packet['heart_rate_bpm']):>6} "
        f"co2={'null' if packet['co2_ppm'] is None else int(packet['co2_ppm']):>5} "
        f"pir={'1' if packet['pir_motion'] else '0'} "
        f"presence={_tri(packet['human_detected_raw'])} "
        f"phase={number(packet['breath_phase'], 4):>9} "
        f"phase_age={('null' if packet['phase_age_ms'] is None else int(packet['phase_age_ms'])):>5} "
        f"mmw_seq={packet['mmwave_sequence']} "
        f"co2_evt={packet['co2_measurement_event_id']}"
        f"{'/valid' if packet['co2_measurement_event_valid'] else ''} "
        f"preheat={_tri(packet['co2_preheat_complete'])}"
    )


def _tri(value: Any) -> str:
    if value is None:
        return "null "
    return "true " if value else "false"


# =============================================================================
# Thermal UDP 수신
# =============================================================================
def decode_thermal_udp_datagram(datagram: bytes) -> dict[str, Any]:
    if len(datagram) < THERMAL_UDP_HEADER_BYTES:
        raise ThermalUDPError("datagram 이 헤더보다 짧습니다", "length", len(datagram))
    (magic, version, message_type, header_size, frame_id, chunk_index,
     chunk_count, frame_size, chunk_offset, chunk_length, reserved,
     frame_crc32) = THERMAL_UDP_HEADER.unpack_from(datagram)
    if magic != THERMAL_UDP_MAGIC:
        raise ThermalUDPError("magic 이 'SNTU' 가 아닙니다", "magic", magic)
    if version != THERMAL_UDP_VERSION:
        raise ThermalUDPError("지원하지 않는 버전", "version", version)
    if message_type != PACKET_THERMAL_U16_BE:
        raise ThermalUDPError("message type 이 2 가 아닙니다", "type", message_type)
    if header_size != THERMAL_UDP_HEADER_BYTES or reserved != 0:
        raise ThermalUDPError("헤더 필드 불일치", "header_size/reserved",
                              (header_size, reserved))
    if frame_size != THERMAL_PAYLOAD_BYTES:
        raise ThermalUDPError("frame_size 불일치", "frame_size", frame_size)
    expected_chunks = math.ceil(frame_size / THERMAL_UDP_CHUNK_BYTES)
    if (chunk_count != expected_chunks or not 1 <= chunk_count <= THERMAL_UDP_MAX_CHUNKS
            or chunk_index >= chunk_count):
        raise ThermalUDPError("chunk count/index 불일치", "chunk",
                              (chunk_index, chunk_count, expected_chunks))
    expected_offset = chunk_index * THERMAL_UDP_CHUNK_BYTES
    expected_length = min(THERMAL_UDP_CHUNK_BYTES, frame_size - expected_offset)
    payload = datagram[header_size:]
    if (chunk_offset != expected_offset or chunk_length != expected_length
            or len(payload) != chunk_length):
        raise ThermalUDPError(
            "chunk offset/length 불일치", "offset/length",
            f"got=({chunk_offset},{chunk_length},{len(payload)}) "
            f"want=({expected_offset},{expected_length})",
        )
    return {
        "frame_id": frame_id, "chunk_index": chunk_index,
        "chunk_count": chunk_count, "frame_crc32": frame_crc32, "payload": payload,
    }


class ThermalUDPGateway(threading.Thread):
    def __init__(self, state: SensorState, host: str, port: int, *,
                 frame_timeout: float = 0.5, max_pending: int = 8) -> None:
        super().__init__(name="safenest-thermal-udp", daemon=True)
        self.state = state
        self.host = host
        self.port = port
        self.frame_timeout = frame_timeout
        self.max_pending = max_pending
        self.stop_event = threading.Event()
        self._socket: socket.socket | None = None
        self._pending: dict[tuple, dict[str, Any]] = {}
        self._completed: dict[tuple, float] = {}
        self._first_datagram_logged = False

    def run(self) -> None:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            self._socket = receiver
            receiver.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                receiver.bind((self.host, self.port))
            except OSError as exc:
                LOG("ERROR", f"UDP :{self.port} 바인드 실패: {exc}")
                report_port_holder(self.port, "udp")
                self.stop_event.set()
                return
            receiver.settimeout(0.1)
            LOG("UDP", f"listening on {self.host}:{self.port} "
                       f"(프레임당 {THERMAL_UDP_EXPECTED_CHUNKS} chunk, "
                       f"재조립 타임아웃 {self.frame_timeout}s)")
            while not self.stop_event.is_set():
                try:
                    datagram, peer = receiver.recvfrom(THERMAL_UDP_DATAGRAM_BYTES + 1)
                except socket.timeout:
                    self._evict(time.monotonic())
                    continue
                except OSError:
                    break
                self._accept(datagram, peer)

    def _accept(self, datagram: bytes, peer: tuple[str, int]) -> None:
        now = time.monotonic()
        with STATS.lock:
            STATS.udp_datagrams += 1
            STATS.udp_bytes += len(datagram)
        if not self._first_datagram_logged:
            self._first_datagram_logged = True
            LOG("UDP", f"첫 datagram 도착: peer={peer[0]}:{peer[1]} bytes={len(datagram)}")
        self._evict(now)

        try:
            chunk = decode_thermal_udp_datagram(datagram)
        except ThermalUDPError as exc:
            with STATS.lock:
                STATS.udp_invalid += 1
            STATS.note_reject(exc.rule)
            LOG("REJECT", f"udp peer={peer[0]}:{peer[1]} -> {exc}")
            return

        key = (peer[0], peer[1], chunk["frame_id"])
        if key in self._completed:
            with STATS.lock:
                STATS.udp_duplicates += 1
            return

        pending = self._pending.get(key)
        if pending is None:
            if len(self._pending) >= self.max_pending:
                oldest = min(self._pending, key=lambda k: self._pending[k]["started"])
                del self._pending[oldest]
                with STATS.lock:
                    STATS.udp_frames_dropped += 1
                LOG("UDP", f"pending 한도 초과로 frame={oldest[2]} 폐기 "
                           f"(동시에 너무 많은 프레임이 반쯤 도착했습니다)")
            pending = {"chunks": {}, "count": chunk["chunk_count"],
                       "crc": chunk["frame_crc32"], "started": now, "updated": now}
            self._pending[key] = pending
        elif pending["crc"] != chunk["frame_crc32"] or pending["count"] != chunk["chunk_count"]:
            del self._pending[key]
            with STATS.lock:
                STATS.udp_frames_dropped += 1
                STATS.udp_invalid += 1
            LOG("REJECT", f"udp frame={chunk['frame_id']} 같은 frame_id 인데 CRC/chunk 수가 "
                          f"다릅니다 (frame_id 가 재사용되었거나 두 노드가 같은 포트로 보냅니다)")
            return

        index = chunk["chunk_index"]
        if index in pending["chunks"]:
            with STATS.lock:
                STATS.udp_duplicates += 1
            return
        if index != len(pending["chunks"]):
            with STATS.lock:
                STATS.udp_out_of_order += 1
        pending["chunks"][index] = chunk["payload"]
        pending["updated"] = now
        if len(pending["chunks"]) != pending["count"]:
            return

        del self._pending[key]
        payload = b"".join(pending["chunks"][i] for i in range(pending["count"]))
        if zlib.crc32(payload) & 0xFFFFFFFF != pending["crc"]:
            with STATS.lock:
                STATS.udp_crc_failures += 1
                STATS.udp_frames_dropped += 1
            LOG("REJECT", f"udp frame={chunk['frame_id']} CRC32 불일치 — 9개 chunk 는 다 왔지만 "
                          f"내용이 깨졌습니다 (Wi-Fi 품질 또는 ESP 측 버퍼 문제)")
            return
        try:
            frame = decode_thermal_payload(chunk["frame_id"], payload)
        except ProtocolError as exc:
            with STATS.lock:
                STATS.udp_frames_dropped += 1
            STATS.note_reject(exc.rule)
            LOG("REJECT", f"udp frame={chunk['frame_id']} -> {exc}")
            return

        STATS.note_thermal()
        self.state.ingest_thermal(frame, f"{peer[0]}:{peer[1]}")
        self._completed[key] = now
        while len(self._completed) > 64:
            del self._completed[next(iter(self._completed))]
        if STATS.udp_frames_ok <= 3 or STATS.udp_frames_ok % 30 == 0:
            LOG("UDP", f"frame ok  seq={frame['frame_sequence']} "
                       f"raw={frame['minimum_raw']}..{frame['maximum_raw']} "
                       f"(누적 {STATS.udp_frames_ok} 프레임)")

    def _evict(self, now: float) -> None:
        expired = [key for key, pending in self._pending.items()
                   if now - pending["updated"] >= self.frame_timeout]
        for key in expired:
            missing = sorted(set(range(self._pending[key]["count"]))
                             - set(self._pending[key]["chunks"]))
            del self._pending[key]
            with STATS.lock:
                STATS.udp_timeouts += 1
                STATS.udp_frames_dropped += 1
            LOG("UDP", f"frame={key[2]} 재조립 타임아웃: chunk {missing} 미도착 "
                       f"— UDP 유실입니다. Wi-Fi 신호나 ESP 의 chunk 간격을 보세요")
        expiry = self.frame_timeout * 4.0
        for key, completed_at in list(self._completed.items()):
            if now - completed_at >= expiry:
                del self._completed[key]

    def stop(self) -> None:
        self.stop_event.set()
        if self._socket is not None:
            try:
                self._socket.close()
            except OSError:
                pass


# =============================================================================
# 콘솔 리포터
# =============================================================================
class Reporter(threading.Thread):
    def __init__(self, state: SensorState, *, state_interval: float = 1.0,
                 rate_interval: float = 5.0) -> None:
        super().__init__(name="safenest-reporter", daemon=True)
        self.state = state
        self.state_interval = state_interval
        self.rate_interval = rate_interval
        self.stop_event = threading.Event()

    def run(self) -> None:
        last_rate = 0.0
        while not self.stop_event.wait(self.state_interval):
            snapshot = self.state.snapshot()
            LOG("STATE", self._format_state(snapshot))
            now = time.monotonic()
            if now - last_rate >= self.rate_interval:
                last_rate = now
                LOG("RATE", self._format_rates())
                LOG("AI", self._format_ai())

    def _format_state(self, snapshot: dict[str, Any]) -> str:
        parts = [f"system={snapshot['system']:<8}"]
        for name in ("mmwave", "thermal", "co2", "pir"):
            entry = snapshot["sensors"][name]
            age = "  --" if entry["age_seconds"] is None else f"{entry['age_seconds']:4.1f}s"
            parts.append(f"{name}={entry['status']:<12}({age})")
        values = snapshot["sensors"]["mmwave"]["values"]
        co2 = snapshot["sensors"]["co2"]["values"]
        parts.append(
            f"| resp={_fmt(values.get('respiration_rate_bpm'))} "
            f"heart={_fmt(values.get('heart_rate_bpm'))} "
            f"co2={_fmt(co2.get('ppm'), 0)}ppm "
            f"pir={'1' if snapshot['sensors']['pir']['values'].get('motion') else '0'}"
        )
        return "  ".join(parts)

    def _format_rates(self) -> str:
        telemetry_pps, thermal_fps = STATS.rates()
        with STATS.lock:
            reasons = ", ".join(f"{rule}×{count}"
                                for rule, count in sorted(STATS.reject_reasons.items(),
                                                          key=lambda item: -item[1])[:3])
            summary = (
                f"telemetry={telemetry_pps:5.1f} pkt/s (총 {STATS.telemetry_packets}) "
                f"gap_max={STATS.max_telemetry_gap_ms:6.0f}ms  "
                f"thermal={thermal_fps:4.1f} fps (총 {STATS.udp_frames_ok}) "
                f"udp_dg={STATS.udp_datagrams} drop={STATS.udp_frames_dropped} "
                f"crc_fail={STATS.udp_crc_failures} timeout={STATS.udp_timeouts} "
                f"reorder={STATS.udp_out_of_order}  "
                f"tcp_conn={STATS.tcp_connections} disc={STATS.tcp_disconnects} "
                f"seq_gap={STATS.sequence_gaps} reject={STATS.protocol_errors}"
            )
            if reasons:
                summary += f"  top_reject=[{reasons}]"
        return summary

    def _format_ai(self) -> str:
        """온디바이스 AI 3종의 입력이 실제로 도착하고 있는지."""
        readiness = self.state.ai_readiness()
        b23 = readiness["mmwave_b23"]
        co2 = readiness["co2_c_b6"]
        thermal = readiness["thermal"]
        return (
            f"mmwave_b23 window {b23['distinct_phase_events']}/"
            f"{b23['window_samples_required']} "
            f"{'READY' if b23['window_ready'] else 'filling'} "
            f"(skip_republish={b23['republished_skips']} "
            f"phase_null={b23['phase_missing']} stale={b23['phase_stale']} "
            f"no_seq={b23['sequence_missing']} boot_reset={b23['boot_resets']})  |  "
            f"co2_c_b6 {co2['history_span_seconds']:.0f}/"
            f"{co2['history_required_seconds']:.0f}s "
            f"{'READY' if co2['window_ready'] else 'filling'} "
            f"(eligible={co2['eligible_events']} "
            f"blocked={co2['blocked_by_preheat_or_value']})  |  "
            f"thermal frames={thermal['frames_received']} "
            f"{'READY' if thermal['ready'] else 'NO_FRAME'}"
        )

    def stop(self) -> None:
        self.stop_event.set()


def _fmt(value: Any, digits: int = 2) -> str:
    if value is None:
        return "null"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return str(value)


# =============================================================================
# 상태 웹 서버 (표준 라이브러리만)
# =============================================================================
def start_http_server(state: SensorState, host: str, port: int) -> threading.Thread | None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # noqa: A002 - 기본 stderr 로그 억제
            return

        def _send(self, code: int, content_type: str, body: bytes) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler 규약
            path = self.path.split("?", 1)[0]
            if path == "/status":
                document = state.snapshot()
                document["ai_input_readiness"] = state.ai_readiness()
                with STATS.lock:
                    document["link"] = {
                        "tcp_connections": STATS.tcp_connections,
                        "tcp_disconnects": STATS.tcp_disconnects,
                        "telemetry_packets": STATS.telemetry_packets,
                        "protocol_errors": STATS.protocol_errors,
                        "sequence_gaps": STATS.sequence_gaps,
                        "udp_datagrams": STATS.udp_datagrams,
                        "udp_frames_ok": STATS.udp_frames_ok,
                        "udp_frames_dropped": STATS.udp_frames_dropped,
                        "udp_crc_failures": STATS.udp_crc_failures,
                        "udp_timeouts": STATS.udp_timeouts,
                        "reject_reasons": dict(STATS.reject_reasons),
                        "max_telemetry_gap_ms": STATS.max_telemetry_gap_ms,
                    }
                self._send(200, "application/json; charset=utf-8",
                           json.dumps(document, ensure_ascii=False, indent=2).encode())
            elif path == "/thermal.pgm":
                pgm = state.thermal_pgm()
                if pgm is None:
                    self._send(204, "text/plain; charset=utf-8", b"")
                else:
                    self._send(200, "image/x-portable-graymap", pgm)
            elif path in ("/", "/index.html"):
                self._send(200, "text/html; charset=utf-8", STATUS_PAGE.encode())
            else:
                self._send(404, "text/plain; charset=utf-8", b"not found\n")

    try:
        server = ThreadingHTTPServer((host, port), Handler)
    except OSError as exc:
        LOG("ERROR", f"HTTP :{port} 바인드 실패: {exc} (--no-http 로 끌 수 있습니다)")
        return None
    thread = threading.Thread(target=server.serve_forever, name="safenest-http", daemon=True)
    thread.start()
    LOG("HTTP", f"status page  http://{_local_ip()}:{port}/   json  /status   "
                f"thermal  /thermal.pgm")
    return thread


STATUS_PAGE = """<!doctype html>
<meta charset="utf-8">
<title>SafeNest Pi Gateway</title>
<style>
 body{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;background:#0f1115;color:#e6e6e6;
      margin:0;padding:24px;line-height:1.5}
 h1{font-size:18px;margin:0 0 16px}
 table{border-collapse:collapse;margin-bottom:20px;width:100%;max-width:900px}
 td,th{border:1px solid #2a2f3a;padding:6px 10px;text-align:left;font-size:13px}
 th{background:#1a1e26}
 .LIVE{color:#4ade80}.STALE{color:#fbbf24}.INVALID{color:#f87171}
 .NO_DATA{color:#6b7280}.DISCONNECTED{color:#f87171}
 pre{background:#1a1e26;padding:12px;border-radius:6px;overflow:auto;font-size:12px;
     max-width:900px}
</style>
<h1>SafeNest Raspberry Pi 수신 게이트웨이</h1>
<div id="summary"></div>
<table id="sensors"><thead><tr><th>센서</th><th>상태</th><th>age</th><th>ttl</th>
<th>주요 값</th></tr></thead><tbody></tbody></table>
<h1>링크</h1><pre id="link"></pre>
<h1>마지막 열화상 프레임</h1>
<img id="thermal" width="320" height="248" style="image-rendering:pixelated;
     border:1px solid #2a2f3a">
<script>
async function tick(){
  try{
    const r = await fetch('/status'); const d = await r.json();
    document.getElementById('summary').textContent =
      'system = ' + d.system + '   thermal_frame = ' + (d.thermal_available?'yes':'no')
      + '   co2_events = ' + d.co2_measurement_events;
    const body = document.querySelector('#sensors tbody'); body.innerHTML='';
    for (const [name, s] of Object.entries(d.sensors)) {
      const tr = document.createElement('tr');
      const age = s.age_seconds==null ? '--' : s.age_seconds.toFixed(1)+'s';
      tr.innerHTML = '<td>'+name+'</td><td class="'+s.status+'">'+s.status+'</td>'
        + '<td>'+age+'</td><td>'+s.ttl_seconds+'s</td>'
        + '<td>'+JSON.stringify(s.values)+'</td>';
      body.appendChild(tr);
    }
    document.getElementById('link').textContent = JSON.stringify(d.link, null, 2);
    document.getElementById('thermal').src = '/thermal.pgm?t=' + Date.now();
  }catch(e){ document.getElementById('summary').textContent = 'gateway 응답 없음: '+e; }
}
tick(); setInterval(tick, 1000);
</script>
"""


def _local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
            probe.connect(("8.8.8.8", 80))
            return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"


# =============================================================================
# 시작 전 점검
# =============================================================================
def report_port_holder(port: int, protocol: str) -> None:
    """포트를 이미 쥔 프로세스를 알려줍니다. 대부분 run_safenest.sh 입니다."""
    flag = "-ltnp" if protocol == "tcp" else "-lunp"
    try:
        output = subprocess.run(["ss", flag], capture_output=True, text=True,
                                timeout=3).stdout
    except (OSError, subprocess.SubprocessError):
        LOG("WARN", f"포트 {port} 점유 프로세스를 확인하지 못했습니다 "
                    f"(`sudo ss {flag} | grep :{port}` 를 직접 실행해 보세요)")
        return
    matches = [line for line in output.splitlines() if f":{port} " in line]
    if matches:
        LOG("ERROR", f"{protocol}/{port} 을 이미 쓰고 있는 프로세스:")
        for line in matches:
            LOG("ERROR", "  " + line.strip())
        LOG("ERROR", "run_safenest.sh 가 떠 있으면 먼저 Ctrl+C 로 내리고 다시 실행하세요.")
    else:
        LOG("ERROR", f"{protocol}/{port} 이 사용 중인데 소유자를 못 찾았습니다 "
                     f"(sudo 없이 실행하면 프로세스명이 안 보일 수 있습니다)")


def preflight(args: argparse.Namespace) -> None:
    LOG("INFO", "=" * 78)
    LOG("INFO", "SafeNest Raspberry Pi 수신 게이트웨이 (브링업/통신 진단)")
    LOG("INFO", f"python={sys.version.split()[0]}  pid={os.getpid()}  "
                f"cwd={Path.cwd()}")
    LOG("INFO", f"내 IP = {_local_ip()}   <- ESP32 secrets.h 의 RPI_HOST 와 "
                f"같아야 합니다")
    LOG("INFO", f"TCP :{args.sensor_port} (telemetry)   UDP :{args.thermal_port} (thermal)"
                + ("" if args.no_http else f"   HTTP :{args.http_port} (상태 페이지)"))
    LOG("INFO", f"프레임 크기: telemetry 헤더 {HEADER.size}B, thermal payload "
                f"{THERMAL_PAYLOAD_BYTES}B = {THERMAL_UDP_EXPECTED_CHUNKS} chunk × "
                f"최대 {THERMAL_UDP_DATAGRAM_BYTES}B")
    LOG("INFO", "=" * 78)


# =============================================================================
# main
# =============================================================================
def main() -> int:
    global LOG

    parser = argparse.ArgumentParser(
        description="SafeNest Pi 수신 게이트웨이 (통신 진단)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--sensor-port", type=int, default=9000)
    parser.add_argument("--thermal-port", type=int, default=5005)
    parser.add_argument("--http-port", type=int, default=8001)
    parser.add_argument("--no-http", action="store_true", help="상태 웹 페이지 끄기")
    parser.add_argument("--strict", action="store_true",
                        help="Runtime 과 동일하게 sequence 위반 시 연결을 끊습니다")
    parser.add_argument("--packet-deadline", type=float, default=5.0,
                        help="한 필드를 다 받는 데 허용하는 초 (Runtime 기본 5.0)")
    parser.add_argument("--thermal-frame-timeout", type=float, default=0.5,
                        help="UDP 프레임 재조립 타임아웃 초 (Runtime 기본 0.5)")
    parser.add_argument("--quiet-packets", action="store_true",
                        help="[pkt] 줄을 끕니다 (10 Hz 면 화면이 빨리 흐릅니다)")
    parser.add_argument("--no-jsonl", action="store_true",
                        help="telemetry 원본 JSONL 저장 끄기")
    parser.add_argument("--log-dir", default="safenest_logs")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args()

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    LOG = Logger(log_dir / f"gateway-{stamp}.log",
                 use_color=not args.no_color and sys.stdout.isatty())
    jsonl = None if args.no_jsonl else log_dir / f"telemetry-{stamp}.jsonl"

    preflight(args)

    state = SensorState()
    tcp = TCPGateway(state, args.host, args.sensor_port, strict=args.strict,
                     packet_deadline=args.packet_deadline,
                     log_packets=not args.quiet_packets, jsonl=jsonl)
    udp = ThermalUDPGateway(state, args.host, args.thermal_port,
                            frame_timeout=args.thermal_frame_timeout)
    reporter = Reporter(state)

    tcp.start()
    udp.start()
    reporter.start()
    if not args.no_http:
        start_http_server(state, args.host, args.http_port)

    # 바인드 실패는 스레드 안에서 나므로 잠깐 기다렸다가 확인합니다.
    time.sleep(0.4)
    if tcp.stop_event.is_set() or udp.stop_event.is_set():
        LOG("ERROR", "포트 바인드에 실패해서 종료합니다.")
        LOG.close()
        return 2

    LOG("INFO", "대기 중입니다. ESP32 를 켜고 시리얼 로그의 "
                "[network] Raspberry Pi connected 줄을 확인하세요. Ctrl+C 로 종료.")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        LOG("INFO", "종료 중...")
    finally:
        reporter.stop()
        tcp.stop()
        udp.stop()
        with STATS.lock:
            LOG("INFO", f"최종: telemetry={STATS.telemetry_packets} "
                        f"thermal_frames={STATS.udp_frames_ok} "
                        f"tcp_conn={STATS.tcp_connections} "
                        f"reject={STATS.protocol_errors} "
                        f"udp_drop={STATS.udp_frames_dropped}")
            if STATS.reject_reasons:
                LOG("INFO", "거부 사유 집계:")
                for rule, count in sorted(STATS.reject_reasons.items(),
                                          key=lambda item: -item[1]):
                    LOG("INFO", f"  {count:6d}  {rule}")
        LOG("INFO", f"로그 저장 위치: {log_dir.resolve()}")
        LOG.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
