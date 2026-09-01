# SafeNest USB 스피커 HIL 전달 패키지

이 폴더는 Raspberry Pi 5에서 USB 스피커 경로와 위험도별 알람·한국어 TTS를 검증하기 위한 **독립 테스트 패키지**입니다. SafeNest 운영 Risk Engine, 센서 통신, AI 모델, 임계값을 변경하지 않습니다.

## SafeNest 상태 매핑

저장소의 실제 계약에는 `EMERGENCY`라는 별도 `risk_level` 값이 없습니다.

| 시험 단계 | SafeNest 조건 | 동작 |
| --- | --- | --- |
| 정상 | `risk_level=NORMAL` | 무음, 경보 정지 |
| 주의 | `risk_level=WARNING` | 880 Hz 주의음 + 느리고 낮은 한국어 TTS, 진입 시 1회 |
| 위험 | `risk_level=DANGER`, `is_emergency=false` | 900/1400 Hz 교대음 + 빠른 위험 TTS, 30초 쿨다운 |
| 긴급 | `risk_level=DANGER`, `is_emergency=true` 또는 emergency latch 활성 | 더 빠른 1000/1500 Hz 교대음 + 높은 우선순위 TTS, 15초 쿨다운 |

긴급은 저장소 `risk/engine.py`의 검증된 무호흡 또는 신뢰도 0.8 이상 낙상 override와 대응합니다.
이미 활성화된 emergency latch는 센서 입력이 일시적으로 사라져 `risk_level=null`이 되어도 긴급으로 유지합니다.

## 안전 원칙

- 최초 테스트 진폭은 최대 18%이며 프로그램이 믹서 볼륨을 변경하지 않습니다.
- 모든 알람은 5초 이내에 자동 종료됩니다.
- `aplay -l`에 USB 오디오 장치가 없으면 즉시 중단합니다.
- 명령 성공은 실제 소리가 났다는 증거가 아닙니다. 왼쪽/오른쪽/실제 청취 여부를 사람이 기록해야 합니다.
- 처음부터 `alsamixer` 볼륨을 100%로 올리지 마세요.

## 1. 저장소에서 실행

SafeNest 저장소를 Raspberry Pi에 받은 뒤 저장소 루트에서 이 폴더로 이동합니다.

```bash
cd RaspberryPi/Runtime/hil/audio_test
python3 -m unittest -v tests/test_safenest_audio.py
```

Python 표준 라이브러리만 사용합니다. 재생에는 Raspberry Pi OS의 `aplay`가 필요합니다.

## 2. 하드웨어 진단 — 가장 먼저 실행

```bash
python3 detect_audio.py --verbose --save diagnostics.txt
```

종료 코드 의미:

- `0`: USB 오디오 재생 장치가 감지됨
- `2`: ALSA 재생 장치가 없음
- `3`: 재생 장치는 있지만 USB 오디오로 확인되지 않음

종료 코드가 `2` 또는 `3`이면 나머지 재생/TTS 테스트를 하지 마세요. 패시브 AUX-to-USB 케이블은 DAC가 아닙니다.

필요한 구성:

```text
Raspberry Pi USB → USB Audio DAC/USB 사운드카드 → 3.5 mm → inkel AUX 입력
Raspberry Pi 별도 USB 포트 → 스피커 USB 전원
```

## 3. ALSA 장치와 믹서 확인

```bash
python3 speaker_test.py --list
amixer -c <card_number>
alsamixer -c <card_number>
```

아래 예시의 장치명은 반드시 `--list`에 실제로 출력된 값으로 교체합니다.

```bash
DEVICE='plughw:CARD=Device,DEV=0'
```

## 4. 낮은 진폭 톤과 좌우 채널

```bash
python3 speaker_test.py --device "$DEVICE" --tone --channel both
python3 speaker_test.py --device "$DEVICE" --tone --channel left
python3 speaker_test.py --device "$DEVICE" --tone --channel right
```

각 명령 뒤에 어떤 물리 스피커에서 소리가 났는지 기록합니다.

## 5. 위험도별 알람

```bash
python3 speaker_test.py --device "$DEVICE" --alarm warning
python3 speaker_test.py --device "$DEVICE" --alarm danger
python3 speaker_test.py --device "$DEVICE" --alarm emergency
```

## 6. 오프라인 한국어 TTS

설치된 엔진부터 확인합니다.

```bash
python3 tts_test.py --list-engines
```

엔진이 있을 때:

```bash
python3 tts_test.py --device "$DEVICE" --level warning
python3 tts_test.py --device "$DEVICE" --level danger
python3 tts_test.py --device "$DEVICE" --level emergency
python3 tts_test.py --device "$DEVICE" --level warning --text "스피커 출력 테스트입니다."
```

`espeak-ng`는 하드웨어 검증에는 충분하지만 한국어 자연스러움이 낮을 수 있습니다. 최종 시스템에는 한국어 Piper 모델 검토를 권장합니다. 클라우드 TTS는 사용하지 않습니다.

Piper가 이미 설치되고 한국어 모델이 있을 때:

```bash
python3 tts_test.py --device "$DEVICE" --level danger \
  --engine piper --piper-model /absolute/path/to/ko_model.onnx
```

## 7. 상태 전이·중복 방지·쿨다운 논리 시험

소리 없이 먼저 확인합니다.

```bash
python3 risk_audio_test.py --sequence --dry-run
```

기본 시퀀스는 다음과 같습니다.

```text
NORMAL → WARNING → WARNING → DANGER → DANGER → EMERGENCY → EMERGENCY → NORMAL
```

동일한 WARNING은 다시 재생되지 않아야 하며, 위험·긴급 반복은 각 프로필 쿨다운 전에는 차단되어야 합니다.

각 상태를 실제로 한 번씩 시험:

```bash
python3 risk_audio_test.py --device "$DEVICE" --level warning
python3 risk_audio_test.py --device "$DEVICE" --level danger
python3 risk_audio_test.py --device "$DEVICE" --level emergency
```

SafeNest `/api/status`와 같은 publication JSON 파일로 상태를 판정할 수도 있습니다.

```bash
python3 risk_audio_test.py --publication status.json --dry-run
python3 risk_audio_test.py --publication status.json --device "$DEVICE"
```

## 8. 음성 설정 변경

`audio_profiles.json`에서 단계별로 다음 값을 바꿀 수 있습니다.

- `tts_text`: 한국어 문구
- `tts_speed`: eSpeak 말하기 속도
- `tts_pitch`: 음높이
- `tts_volume`: TTS 합성 볼륨
- `alarm_segments`: 주파수와 구간 길이
- `amplitude`: 알람 PCM 진폭, 안전상 `0.20` 초과 금지
- `cooldown_seconds`: 위험/긴급 재알림 최소 간격
- `repeat_after_cooldown`: 같은 상태 재알림 허용 여부

설정 검증은 스크립트가 자동 수행합니다. 알람 총 길이 5초 또는 진폭 20%를 넘으면 실행을 거부합니다.

## 시험 결과 기록

```text
=== SafeNest Speaker HIL Result ===

USB power detected:
USB audio device detected:
ALSA device:
Audio stack:
Left speaker:
Right speaker:
Stereo test:
WARNING alarm:
DANGER alarm:
EMERGENCY alarm:
Korean TTS WARNING:
Korean TTS DANGER:
Korean TTS EMERGENCY:
Physical audible confirmation:

Overall: PASS / PARTIAL / FAIL
Root cause of any failures:
Recommended next hardware/software action:
```

`diagnostics.txt`와 이 결과를 담당 팀원에게 전달해 주세요. 진단 로그와 생성 WAV는 로컬 HIL 산출물이므로 Git에 커밋하지 않습니다.
