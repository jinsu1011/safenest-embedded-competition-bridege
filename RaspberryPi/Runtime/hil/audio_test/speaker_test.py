#!/usr/bin/env python3
"""Generate and play bounded, conservative SafeNest HIL tones."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from safenest_audio import (
    AudioTestError,
    generate_alarm_wav,
    list_playback_devices,
    load_profiles,
    play_wav,
    resolve_device,
)


ROOT = Path(__file__).resolve().parent
PROFILES = ROOT / "audio_profiles.json"
GENERATED = ROOT / "generated"


def print_devices() -> int:
    devices, raw, _ = list_playback_devices()
    print("Detected playback devices:")
    for index, device in enumerate(devices):
        marker = "USB AUDIO" if device.usb_audio else "non-USB/unknown"
        print(f"[{index}] {device.card_name} / {device.device_name} ({marker})")
        print(f"    {device.target}")
    if not devices:
        print(raw)
        return 2
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SafeNest 스피커 톤/알람 HIL 테스트")
    parser.add_argument("--list", action="store_true", help="ALSA 재생 장치 목록")
    parser.add_argument("--device", help="--list에 표시된 권장 ALSA target")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--tone", action="store_true", help="440 Hz, 1초, 12%% 테스트 톤")
    group.add_argument("--alarm", choices=("warning", "danger", "emergency"))
    parser.add_argument("--channel", choices=("left", "right", "both"), default="both")
    parser.add_argument("--allow-non-usb", action="store_true", help="명시적으로 비USB 장치 테스트 허용")
    parser.add_argument("--dry-run", action="store_true", help="WAV만 생성하고 재생하지 않음")
    args = parser.parse_args()

    if args.list:
        return print_devices()
    if not args.tone and not args.alarm:
        parser.error("--tone 또는 --alarm을 지정하세요.")
    if not args.device and not args.dry_run:
        parser.error("재생 시 --device가 필요합니다. 먼저 --list를 실행하세요.")

    profiles = load_profiles(PROFILES)
    if args.tone:
        name = "tone_440hz"
        segments = [{"frequency_hz": 440, "duration_ms": 1_000}]
        amplitude = 0.12
    else:
        name = str(args.alarm)
        profile = profiles[name]
        segments = profile["alarm_segments"]
        amplitude = float(profile["amplitude"])
    output = generate_alarm_wav(
        GENERATED / f"{name}_{args.channel}.wav",
        segments,
        amplitude=amplitude,
        channel=args.channel,
    )
    print(f"생성: {output} (진폭 {amplitude * 100:.0f}%, 채널 {args.channel})")
    if args.dry_run:
        print("DRY RUN: 실제 재생하지 않음")
        return 0

    assert args.device is not None
    resolve_device(args.device, require_usb=not args.allow_non_usb)
    print("주의: 볼륨을 자동 변경하지 않습니다. 현재 믹서 볼륨을 먼저 확인하세요.")
    play_wav(output, args.device)
    print("재생 명령 성공. 실제 소리가 들렸는지는 사람이 별도로 확인해야 합니다.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AudioTestError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
    except KeyboardInterrupt:
        raise SystemExit(130)
