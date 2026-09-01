"""Standalone SafeNest speaker HIL helpers.

This module intentionally does not import or modify the production runtime.
It mirrors the canonical risk contract for hardware validation only.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import shutil
import struct
import subprocess
import time
from typing import Any, Iterable, Mapping, Sequence
import wave


SAMPLE_RATE = 48_000
MAX_TEST_AMPLITUDE = 0.20
MAX_ALARM_SECONDS = 5.0
PROFILE_NAMES = ("normal", "warning", "danger", "emergency")


class AudioTestError(RuntimeError):
    """Expected, user-actionable HIL error."""


@dataclass(frozen=True)
class PlaybackDevice:
    card_number: int
    card_id: str
    card_name: str
    device_number: int
    device_name: str
    usb_audio: bool

    @property
    def target(self) -> str:
        return f"plughw:CARD={self.card_id},DEV={self.device_number}"

    @property
    def numeric_target(self) -> str:
        return f"plughw:{self.card_number},{self.device_number}"

    @property
    def aliases(self) -> tuple[str, ...]:
        return (
            self.target,
            self.numeric_target,
            f"hw:CARD={self.card_id},DEV={self.device_number}",
            f"hw:{self.card_number},{self.device_number}",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "card_number": self.card_number,
            "card_id": self.card_id,
            "card_name": self.card_name,
            "device_number": self.device_number,
            "device_name": self.device_name,
            "usb_audio": self.usb_audio,
            "recommended_target": self.target,
        }


def run_capture(command: Sequence[str], timeout: float = 8.0) -> tuple[int | None, str]:
    if not command or shutil.which(command[0]) is None:
        return None, f"명령 없음: {command[0] if command else '(empty)'}"
    try:
        result = subprocess.run(
            list(command),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
        )
        return result.returncode, result.stdout.rstrip()
    except subprocess.TimeoutExpired as error:
        output = error.stdout.decode(errors="replace") if isinstance(error.stdout, bytes) else (error.stdout or "")
        return 124, f"{output.rstrip()}\n시간 초과: {' '.join(command)}".strip()


def _usb_card_numbers(proc_cards: str) -> set[int]:
    found: set[int] = set()
    current: int | None = None
    for line in proc_cards.splitlines():
        match = re.match(r"^\s*(\d+)\s+\[", line)
        if match:
            current = int(match.group(1))
        if current is not None and "USB-Audio" in line:
            found.add(current)
    return found


def parse_aplay_devices(aplay_output: str, proc_cards: str = "") -> list[PlaybackDevice]:
    pattern = re.compile(
        r"^card\s+(?P<card>\d+):\s+(?P<card_id>[^\s]+)\s+"
        r"\[(?P<card_name>[^\]]+)\],\s+device\s+(?P<device>\d+):\s+"
        r"(?P<device_name>[^\[]+?)(?:\s+\[[^\]]*\])?\s*$",
        re.IGNORECASE,
    )
    usb_cards = _usb_card_numbers(proc_cards)
    devices: list[PlaybackDevice] = []
    for raw_line in aplay_output.splitlines():
        match = pattern.match(raw_line.strip())
        if not match:
            continue
        card_number = int(match.group("card"))
        combined = " ".join(match.groups()).lower()
        devices.append(
            PlaybackDevice(
                card_number=card_number,
                card_id=match.group("card_id"),
                card_name=match.group("card_name").strip(),
                device_number=int(match.group("device")),
                device_name=match.group("device_name").strip(),
                usb_audio=card_number in usb_cards or "usb" in combined,
            )
        )
    return devices


def list_playback_devices() -> tuple[list[PlaybackDevice], str, str]:
    _, aplay_output = run_capture(("aplay", "-l"))
    try:
        proc_cards = Path("/proc/asound/cards").read_text(encoding="utf-8", errors="replace")
    except OSError:
        proc_cards = ""
    return parse_aplay_devices(aplay_output, proc_cards), aplay_output, proc_cards


def detect_audio_stack() -> str:
    wpctl_code, wpctl_output = run_capture(("wpctl", "status"))
    if wpctl_code == 0 and wpctl_output:
        return "PipeWire (wpctl 사용 가능)"
    pactl_code, pactl_output = run_capture(("pactl", "info"))
    if pactl_code == 0:
        if "PipeWire" in pactl_output:
            return "PipeWire (PulseAudio 호환 계층)"
        return "PulseAudio"
    if shutil.which("aplay"):
        return "ALSA only 또는 사용자 오디오 서버 미실행"
    return "식별 불가"


def resolve_device(device_arg: str, *, require_usb: bool = True) -> PlaybackDevice:
    devices, raw, _ = list_playback_devices()
    for device in devices:
        if device_arg in device.aliases:
            if require_usb and not device.usb_audio:
                raise AudioTestError(
                    f"선택 장치 {device_arg}가 USB 오디오 장치로 확인되지 않았습니다. "
                    "--allow-non-usb 옵션 없이 재생하지 않습니다."
                )
            return device
    raise AudioTestError(
        f"현재 aplay -l에서 {device_arg!r}를 찾지 못했습니다. "
        f"먼저 --list를 실행하세요.\n\n{raw}"
    )


def load_profiles(path: str | Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise AudioTestError("audio_profiles.json 최상위 값은 객체여야 합니다.")
    for name in PROFILE_NAMES:
        profile = payload.get(name)
        if not isinstance(profile, dict):
            raise AudioTestError(f"필수 프로필 누락: {name}")
        amplitude = profile.get("amplitude")
        if not isinstance(amplitude, (int, float)) or isinstance(amplitude, bool):
            raise AudioTestError(f"{name}.amplitude는 숫자여야 합니다.")
        if not 0.0 <= float(amplitude) <= MAX_TEST_AMPLITUDE:
            raise AudioTestError(f"{name}.amplitude는 0~{MAX_TEST_AMPLITUDE} 범위여야 합니다.")
        segments = profile.get("alarm_segments")
        if not isinstance(segments, list):
            raise AudioTestError(f"{name}.alarm_segments는 배열이어야 합니다.")
        total_ms = 0
        for segment in segments:
            if not isinstance(segment, Mapping):
                raise AudioTestError(f"{name} 알람 구간 형식 오류")
            frequency = segment.get("frequency_hz")
            duration = segment.get("duration_ms")
            if not isinstance(frequency, (int, float)) or not 0 <= float(frequency) <= 4_000:
                raise AudioTestError(f"{name} 주파수 범위 오류")
            if not isinstance(duration, int) or isinstance(duration, bool) or not 1 <= duration <= 2_000:
                raise AudioTestError(f"{name} 구간 길이 범위 오류")
            total_ms += duration
        if total_ms > int(MAX_ALARM_SECONDS * 1_000):
            raise AudioTestError(f"{name} 알람이 {MAX_ALARM_SECONDS}초 제한을 초과합니다.")
        cooldown = profile.get("cooldown_seconds")
        if not isinstance(cooldown, (int, float)) or float(cooldown) < 0:
            raise AudioTestError(f"{name}.cooldown_seconds 값 오류")
    return payload


def resolve_profile_from_publication(publication: Mapping[str, Any]) -> str:
    risk_value = publication.get("risk", publication)
    risk = risk_value if isinstance(risk_value, Mapping) else {}
    emergency_value = publication.get("emergency")
    emergency = emergency_value if isinstance(emergency_value, Mapping) else {}
    level = risk.get("risk_level")
    is_emergency = bool(risk.get("is_emergency")) or bool(emergency.get("active"))
    if bool(emergency.get("active")):
        return "emergency"
    if level == "DANGER" and is_emergency:
        return "emergency"
    if level == "DANGER":
        return "danger"
    if level == "WARNING":
        return "warning"
    if level == "NORMAL":
        return "normal"
    return "normal"


class TransitionController:
    """One-shot transitions with optional rate-limited DANGER repeats."""

    def __init__(self, profiles: Mapping[str, Mapping[str, Any]]) -> None:
        self.profiles = profiles
        self.current = "normal"
        self.last_played: dict[str, float] = {}

    def decide(self, profile_name: str, *, now: float | None = None, force: bool = False) -> dict[str, Any]:
        if profile_name not in self.profiles:
            raise AudioTestError(f"알 수 없는 프로필: {profile_name}")
        timestamp = time.monotonic() if now is None else float(now)
        previous = self.current
        self.current = profile_name
        if profile_name == "normal":
            return {
                "action": "silence" if previous != "normal" else "none",
                "from": previous,
                "to": profile_name,
                "reason": "NORMAL 진입: 재생 중인 경보가 있다면 정지",
            }
        if force or profile_name != previous:
            self.last_played[profile_name] = timestamp
            return {
                "action": (
                    "interrupt_and_play"
                    if severity(previous) > 0 and severity(profile_name) > severity(previous)
                    else "play"
                ),
                "from": previous,
                "to": profile_name,
                "reason": "상태 진입 1회 재생",
            }
        profile = self.profiles[profile_name]
        if not bool(profile.get("repeat_after_cooldown")):
            return {
                "action": "none",
                "from": previous,
                "to": profile_name,
                "reason": "동일 상태 유지: 반복 TTS 금지",
            }
        last = self.last_played.get(profile_name, timestamp)
        cooldown = float(profile.get("cooldown_seconds", 0.0))
        elapsed = timestamp - last
        if elapsed >= cooldown:
            self.last_played[profile_name] = timestamp
            return {
                "action": "play",
                "from": previous,
                "to": profile_name,
                "reason": f"쿨다운 {cooldown:g}초 경과 후 재알림",
            }
        return {
            "action": "none",
            "from": previous,
            "to": profile_name,
            "reason": f"쿨다운 중: {max(0.0, cooldown - elapsed):.1f}초 남음",
        }


def severity(profile_name: str) -> int:
    return {"normal": 0, "warning": 1, "danger": 2, "emergency": 3}.get(profile_name, -1)


def _channel_scales(channel: str) -> tuple[float, float]:
    if channel == "left":
        return 1.0, 0.0
    if channel == "right":
        return 0.0, 1.0
    if channel == "both":
        return 1.0, 1.0
    raise AudioTestError(f"지원하지 않는 채널: {channel}")


def generate_alarm_wav(
    path: str | Path,
    segments: Iterable[Mapping[str, Any]],
    *,
    amplitude: float,
    channel: str = "both",
    sample_rate: int = SAMPLE_RATE,
) -> Path:
    amplitude = float(amplitude)
    if not 0.0 <= amplitude <= MAX_TEST_AMPLITUDE:
        raise AudioTestError(f"진폭은 0~{MAX_TEST_AMPLITUDE} 범위여야 합니다.")
    left_scale, right_scale = _channel_scales(channel)
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    phase = 0.0
    frames = bytearray()
    total_samples = 0
    for segment in segments:
        frequency = float(segment["frequency_hz"])
        count = round(sample_rate * float(segment["duration_ms"]) / 1_000.0)
        fade_samples = min(round(sample_rate * 0.01), max(1, count // 4))
        for index in range(count):
            if frequency <= 0:
                sample = 0.0
            else:
                edge = min(1.0, (index + 1) / fade_samples, (count - index) / fade_samples)
                sample = amplitude * edge * math.sin(phase)
                phase += 2.0 * math.pi * frequency / sample_rate
            value = int(max(-1.0, min(1.0, sample)) * 32_767)
            frames.extend(struct.pack("<hh", int(value * left_scale), int(value * right_scale)))
        total_samples += count
    if total_samples / sample_rate > MAX_ALARM_SECONDS + 0.001:
        raise AudioTestError("생성된 알람이 안전 시간 제한을 초과했습니다.")
    with wave.open(str(output), "wb") as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(frames)
    return output


def play_wav(path: str | Path, device_target: str, *, timeout: float = 10.0) -> None:
    if shutil.which("aplay") is None:
        raise AudioTestError("aplay가 없습니다. 먼저 alsa-utils 설치 여부를 확인하세요.")
    result = subprocess.run(
        ["aplay", "-q", "-D", device_target, str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
        timeout=timeout,
        check=False,
    )
    if result.returncode != 0:
        raise AudioTestError(f"aplay 실패({result.returncode}): {result.stdout.strip()}")


def available_tts_engines() -> list[str]:
    return [name for name in ("piper", "espeak-ng", "espeak") if shutil.which(name)]


def synthesize_tts(
    text: str,
    output_path: str | Path,
    profile: Mapping[str, Any],
    *,
    engine: str = "auto",
    piper_model: str | Path | None = None,
) -> tuple[Path, str]:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    engines = available_tts_engines()
    selected = engine
    if selected == "auto":
        selected = "piper" if piper_model and "piper" in engines else (
            "espeak-ng" if "espeak-ng" in engines else ("espeak" if "espeak" in engines else "")
        )
    if selected not in {"piper", "espeak-ng", "espeak"}:
        raise AudioTestError("오프라인 TTS 엔진을 찾지 못했습니다. piper 또는 espeak-ng를 확인하세요.")
    if shutil.which(selected) is None:
        raise AudioTestError(f"선택한 TTS 엔진이 설치되어 있지 않습니다: {selected}")
    if selected == "piper":
        if piper_model is None or not Path(piper_model).is_file():
            raise AudioTestError("Piper 사용 시 한국어 모델 파일을 --piper-model로 지정해야 합니다.")
        command = [selected, "--model", str(piper_model), "--output_file", str(output)]
        result = subprocess.run(
            command,
            input=text,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=30.0,
            check=False,
        )
    else:
        command = [
            selected,
            "-v", "ko",
            "-s", str(int(profile["tts_speed"])),
            "-p", str(int(profile["tts_pitch"])),
            "-a", str(int(profile["tts_volume"])),
            "-w", str(output),
            text,
        ]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            errors="replace",
            timeout=30.0,
            check=False,
        )
    if result.returncode != 0 or not output.is_file() or output.stat().st_size <= 44:
        raise AudioTestError(f"TTS 생성 실패({selected}): {result.stdout.strip()}")
    return output, selected


def diagnostic_sections() -> list[tuple[str, str]]:
    commands: tuple[tuple[str, ...], ...] = (
        ("uname", "-a"),
        ("lsusb",),
        ("cat", "/proc/asound/cards"),
        ("cat", "/proc/asound/devices"),
        ("aplay", "-l"),
        ("aplay", "-L"),
        ("arecord", "-l"),
        ("pactl", "info"),
        ("pactl", "list", "short", "sinks"),
        ("wpctl", "status"),
        ("dmesg", "--level=err,warn,notice", "-T"),
        ("journalctl", "--user", "-u", "pipewire", "--no-pager", "-n", "50"),
    )
    sections: list[tuple[str, str]] = []
    for command in commands:
        code, output = run_capture(command, timeout=12.0)
        sections.append((f"$ {' '.join(command)} [exit={code}]", output))
    return sections
