#!/usr/bin/env python3
"""Exercise NORMAL/WARNING/DANGER/EMERGENCY transition audio behavior."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from safenest_audio import (
    AudioTestError,
    TransitionController,
    generate_alarm_wav,
    load_profiles,
    play_wav,
    resolve_device,
    resolve_profile_from_publication,
    synthesize_tts,
)


ROOT = Path(__file__).resolve().parent
PROFILES = ROOT / "audio_profiles.json"
GENERATED = ROOT / "generated"
DEFAULT_SEQUENCE = "normal,warning,warning,danger,danger,emergency,emergency,normal"


def execute_profile(
    name: str,
    profile: dict,
    *,
    device: str,
    no_tone: bool,
    no_tts: bool,
    engine: str,
    piper_model: Path | None,
) -> None:
    if not no_tone and profile["alarm_segments"]:
        alarm = generate_alarm_wav(
            GENERATED / f"sequence_{name}.wav",
            profile["alarm_segments"],
            amplitude=float(profile["amplitude"]),
        )
        play_wav(alarm, device)
    if not no_tts and profile["tts_text"]:
        tts_file, selected = synthesize_tts(
            str(profile["tts_text"]),
            GENERATED / f"sequence_tts_{name}.wav",
            profile,
            engine=engine,
            piper_model=piper_model,
        )
        print(f"  TTS engine: {selected}")
        play_wav(tts_file, device)


def main() -> int:
    parser = argparse.ArgumentParser(description="SafeNest 위험도 전이 오디오 독립 HIL")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--level", choices=("normal", "warning", "danger", "emergency"))
    source.add_argument("--sequence", nargs="?", const=DEFAULT_SEQUENCE, help="쉼표 구분 상태 전이")
    source.add_argument("--publication", type=Path, help="SafeNest publication/risk JSON 파일")
    parser.add_argument("--device", help="검증된 ALSA target")
    parser.add_argument("--time-step", type=float, default=1.0, help="시퀀스 논리 시간 간격(초)")
    parser.add_argument("--pause", type=float, default=0.5, help="실제 단계 사이 대기(초, 최대 3초)")
    parser.add_argument("--engine", choices=("auto", "piper", "espeak-ng", "espeak"), default="auto")
    parser.add_argument("--piper-model", type=Path)
    parser.add_argument("--no-tone", action="store_true")
    parser.add_argument("--no-tts", action="store_true")
    parser.add_argument("--allow-non-usb", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="전이/중복/쿨다운 판단만 출력")
    args = parser.parse_args()

    if args.time_step < 0:
        parser.error("--time-step은 0 이상이어야 합니다.")
    if not 0 <= args.pause <= 3:
        parser.error("--pause는 0~3초 범위여야 합니다.")
    if not args.dry_run and not args.device:
        parser.error("실제 재생 시 --device가 필요합니다.")
    if not args.dry_run:
        assert args.device is not None
        resolve_device(args.device, require_usb=not args.allow_non_usb)

    profiles = load_profiles(PROFILES)
    if args.publication:
        publication = json.loads(args.publication.read_text(encoding="utf-8"))
        if not isinstance(publication, dict):
            raise AudioTestError("publication JSON은 객체여야 합니다.")
        names = [resolve_profile_from_publication(publication)]
        force_first = True
    elif args.level:
        names = [args.level]
        force_first = True
    else:
        names = [item.strip().lower() for item in str(args.sequence).split(",") if item.strip()]
        force_first = False
    invalid = [name for name in names if name not in profiles]
    if invalid:
        raise AudioTestError(f"지원하지 않는 상태: {invalid}")

    controller = TransitionController(profiles)
    logical_now = 0.0
    for index, name in enumerate(names, start=1):
        decision = controller.decide(name, now=logical_now, force=force_first and index == 1)
        print(
            f"[{index}] {decision['from']} -> {decision['to']} | "
            f"action={decision['action']} | {decision['reason']}"
        )
        if decision["action"] in {"play", "interrupt_and_play"}:
            profile = profiles[name]
            print(
                f"  {profile['label_ko']} TTS: {profile['tts_text']} "
                f"(speed={profile['tts_speed']}, pitch={profile['tts_pitch']}, volume={profile['tts_volume']})"
            )
            if not args.dry_run:
                assert args.device is not None
                execute_profile(
                    name,
                    profile,
                    device=args.device,
                    no_tone=args.no_tone,
                    no_tts=args.no_tts,
                    engine=args.engine,
                    piper_model=args.piper_model,
                )
        elif decision["action"] == "silence":
            print("  NORMAL: 추가 음원 재생 없음")
        logical_now += args.time_step
        if not args.dry_run and index < len(names) and args.pause:
            time.sleep(args.pause)
    print("완료. 명령 성공과 실제 가청 출력은 별도로 기록하세요.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AudioTestError, OSError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(2)
    except KeyboardInterrupt:
        raise SystemExit(130)
