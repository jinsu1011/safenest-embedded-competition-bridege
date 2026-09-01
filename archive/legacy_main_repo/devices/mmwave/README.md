# `devices/mmwave/`

## 1. 디렉터리 목적
MR60BHA2 mmWave 레이더 기기의 ESP 펌웨어, Python 어댑터, 기기 설정, 실측 로그·분석, M-C0 물리 측정 증거, 운용 문서, 기기 단독 테스트를 담당자가 관리한다.

## 2. 시스템에서 담당하는 기능
MR60 UART 프레임을 수집·검증해 재실·거리·호흡·심박·phase 원시 텔레메트리를 JSONL로 내보내고, Python 어댑터가 이를 `SensorReading` 계약으로 변환한다.

## 3. 포함해야 하는 파일 유형
PlatformIO 설정과 C/C++ 소스·헤더, 기기 설정 JSON, Python 어댑터·mock, 재현 가능한 캡처·분석 도구, 원본 실측 로그와 분석 요약, M-C0 manifest/schema/QA, mmWave 단독 테스트를 포함한다.

## 4. 포함하면 안 되는 파일 유형
`.pio/`와 `.venv/` 같은 빌드·환경 산출물, 장치별 비밀값, TFLite 모델·데이터셋·위험도 융합 로직(`ondevice_ai/`), 공용 계약(`shared/contracts/`), 그리고 사람이 읽는 인수인계·운용 문서(`docs/mmwave/`)는 포함하지 않는다.

## 5. 주요 하위 구성
| 경로 | 역할 |
|---|---|
| `firmware/` | ESP-WROOM-32 PlatformIO 프로젝트, 캡처·분석 도구, `logs/`, `analysis/`, `csv/` |
| `device_measurements/` | M-C0 physical evidence의 protocol contract, schema, manifest, QA, pilot/formal 산출물 |
| `src/` | `mr60_esp_adapter.py`, `mmwave_stream_adapter.py`, `mmwave_csv_adapter.py`, `mmwave_adapter.py`, `run_mr60_serial_adapter.py`, `mock_sensor.py` |
| `config/` | `mmwave_processing.json` — mmWave 신호 처리 설정 |
| `tests/` | 입력 어댑터, 스트림 어댑터, ESP 어댑터, manifest 검증 4종 |
| (문서) | 인수인계·튜닝·운용·M-C0 protocol 문서는 팀 규칙에 따라 [`docs/mmwave/`](../../docs/mmwave/)에 있다 |

## 6. 입력과 출력 인터페이스
입력은 MR60BHA2의 UART 프레임(115200bps, GPIO16 RX2 / GPIO17 TX2)과 리플레이용 JSONL 로그다. 출력은 USB/UART JSONL 텔레메트리, 분석 요약 JSON, `SensorReading` 계약을 따르는 판독값이다. 결측·0·NaN·timeout을 정상값이나 무호흡으로 변환하지 않는다.

## 7. 다른 기능 영역과의 관계
`shared/contracts/base_sensor.py`를 구현하고, `ondevice_ai/src/inference/mmwave_interpreter.py`와 `ondevice_ai/src/integrated_node/run_mr60_usb_node.py`가 이 기기의 출력을 소비한다. 설치 각도·거리는 `hardware/3d_models/`와 `docs/operations/HARDWARE_RUNBOOK.md`에 맞춘다. 이 기기의 인수인계·튜닝·운용 문서는 `docs/mmwave/`에 있다.

## 8. 실행·학습·추론 또는 활용 방법
펌웨어 빌드:
```bash
cd devices/mmwave/firmware
pio run
pio run --target upload
```
직렬 어댑터 실행과 로그 리플레이:
```bash
python3 devices/mmwave/src/run_mr60_serial_adapter.py --port /dev/cu.usbserial-XXX
python3 devices/mmwave/src/run_mr60_serial_adapter.py \
  --replay devices/mmwave/firmware/logs/breath/2026-07-28_breath_paced_15rpm_explicit_full_v3.jsonl
```
기기 단독 테스트:
```bash
python3 -m unittest discover -s devices/mmwave/tests -p 'test_*.py'
```
MR60 펌웨어 업데이트는 벽돌 위험이 있으므로 승인 없이 수행하지 않는다.

## 9. 현재 개발 상태 및 버전
MR60 schema 1.2, 펌웨어 v1.2.0. 기존 장치 로그·어댑터의 검증 근거는 `firmware/analysis/final/2026-08-01_mr60_final_validation_manifest.json`이고, M-C0 physical device evidence는 `device_measurements/`에서 별도 관리한다. 의료 수준 정확도, 심박 정확도, 무호흡 검출 완료 또는 deployment-ready로 발표하지 않는다. 기기 단독 테스트 19개가 통과한다.

## 10. 향후 파일 추가 및 관리 규칙
장치 설정 변경은 헤더·JSON·문서·검증 로그를 함께 갱신한다. 원본 JSONL은 절대 덮어쓰거나 재생성하지 않고, M-C0 raw evidence는 manifest·QA·SHA-256과 함께 immutable로 보관한다. 필터·임계값은 한 번에 하나만 바꿔 같은 원본 로그로 전후를 비교한다.

## 11. 주요 기여자와 원본 브랜치·커밋 추적 정보
담당: Jinsu Kim (`@jinsu1011`) — mmWave 기기 및 통합.
원본 ref는 `origin/main` 계보와 `codex/mmwave-phase-integration` (`b0d3c95`)이며, 원본 경로는 `firmware/esp_wroom32_mr60_monitor/`와 `src/sensors/mmwave/`다. 2026-08-03 이동 커밋 `38274c0`에서 현재 경로로 옮겼고, 실행 경로는 `3313f4b`와 `32cdd1d`에서 갱신했다.
