#!/usr/bin/env python3
"""Collect non-mutating Raspberry Pi USB/audio diagnostics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from safenest_audio import detect_audio_stack, diagnostic_sections, list_playback_devices


def main() -> int:
    parser = argparse.ArgumentParser(description="SafeNest USB/ALSA 오디오 장치 진단")
    parser.add_argument("--json", action="store_true", help="장치 요약을 JSON으로 출력")
    parser.add_argument("--verbose", action="store_true", help="전체 진단 명령 출력")
    parser.add_argument("--save", type=Path, help="전체 텍스트 결과 저장 경로")
    args = parser.parse_args()

    devices, aplay_output, proc_cards = list_playback_devices()
    payload = {
        "audio_stack": detect_audio_stack(),
        "playback_devices": [device.to_dict() for device in devices],
        "usb_audio_devices": [device.to_dict() for device in devices if device.usb_audio],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Audio stack: {payload['audio_stack']}")
        print("Detected playback devices:")
        if not devices:
            print("  없음")
        for index, device in enumerate(devices):
            usb = "USB AUDIO" if device.usb_audio else "non-USB/unknown"
            print(
                f"[{index}] card={device.card_number} ({device.card_id}), "
                f"device={device.device_number}, name={device.card_name} / {device.device_name}, {usb}"
            )
            print(f"    권장 ALSA target: {device.target}")
        if not any(device.usb_audio for device in devices):
            print()
            print("[STOP] aplay -l에서 실제 USB 오디오 재생 장치를 확인하지 못했습니다.")
            print("패시브 AUX-to-USB 케이블은 USB DAC가 아닙니다. 재생 테스트를 진행하지 마세요.")

    sections: list[tuple[str, str]] = []
    if args.verbose or args.save:
        sections = diagnostic_sections()
        if args.verbose:
            for title, output in sections:
                print(f"\n{title}\n{output}")
    if args.save:
        lines = [json.dumps(payload, ensure_ascii=False, indent=2)]
        lines.extend(f"\n{title}\n{output}" for title, output in sections)
        args.save.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\n저장 완료: {args.save}")

    if not devices:
        return 2
    if not any(device.usb_audio for device in devices):
        return 3
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("중단됨", file=sys.stderr)
        raise SystemExit(130)
