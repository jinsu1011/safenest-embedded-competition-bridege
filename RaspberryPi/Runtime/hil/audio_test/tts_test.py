#!/usr/bin/env python3
"""Offline Korean TTS validation for each SafeNest alert profile."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from safenest_audio import (
    AudioTestError,
    available_tts_engines,
    load_profiles,
    play_wav,
    resolve_device,
    synthesize_tts,
)


ROOT = Path(__file__).resolve().parent
PROFILES = ROOT / "audio_profiles.json"
GENERATED = ROOT / "generated"


def main() -> int:
    parser = argparse.ArgumentParser(description="SafeNest 위험도별 오프라인 한국어 TTS 테스트")
    parser.add_argument("--list-engines", action="store_true")
    parser.add_argument("--device", help="speaker_test.py --list에 표시된 ALSA target")
    parser.add_argument("--level", choices=("warning", "danger", "emergency"), default="warning")
    parser.add_argument("--text", help="프로필 기본 문구 대신 사용할 문장")
    parser.add_argument("--engine", choices=("auto", "piper", "espeak-ng", "espeak"), default="auto")
    parser.add_argument("--piper-model", type=Path, help="Piper 한국어 .onnx 모델")
    parser.add_argument("--allow-non-usb", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="설정만 표시하고 TTS 생성/재생하지 않음")
    args = parser.parse_args()

    if args.list_engines:
        engines = available_tts_engines()
        print("Available offline TTS engines:", ", ".join(engines) if engines else "없음")
        return 0 if engines else 2

    profiles = load_profiles(PROFILES)
    profile = profiles[args.level]
    text = args.text or str(profile["tts_text"])
    print(
        f"프로필={args.level}, speed={profile['tts_speed']}, "
        f"pitch={profile['tts_pitch']}, volume={profile['tts_volume']}"
    )
    print(f"문구: {text}")
    if args.dry_run:
        print("DRY RUN: TTS를 생성하거나 재생하지 않음")
        return 0
    if not args.device:
        parser.error("재생 시 --device가 필요합니다.")
    resolve_device(args.device, require_usb=not args.allow_non_usb)
    output, selected = synthesize_tts(
        text,
        GENERATED / f"tts_{args.level}.wav",
        profile,
        engine=args.engine,
        piper_model=args.piper_model,
    )
    print(f"TTS 생성: {output} (engine={selected})")
    if selected in {"espeak", "espeak-ng"}:
        print("참고: eSpeak 계열의 한국어 음질은 하드웨어 경로 검증용이며 자연스러움이 낮을 수 있습니다.")
    play_wav(output, args.device)
    print("재생 명령 성공. 실제 음성 청취 여부는 사람이 확인해야 합니다.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AudioTestError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
    except KeyboardInterrupt:
        raise SystemExit(130)
