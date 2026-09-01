# Thermal-44 V5 Real Validation — 실행 매뉴얼 (v2)

## 🎯 목표

**실제 Thermal-44 열화상 센서**의 프레임을 라즈베리파이 5에서 수신하여, 기존 V5 On-Device AI 파이프라인(전처리 → INT8 TFLite 추론 → InferenceResult → Provider)이 **실기기에서 정상 동작하는지** 검증합니다.

> [!IMPORTANT]
> 이번 작업에서는 **모델 재학습을 하지 않습니다.** 기존 `thermal_fall_int8_v0.1.0.tflite` 모델을 그대로 사용합니다.

---

## 📊 현재 프로젝트 상태 분석

### 리포지토리 현황
| 항목 | 상태 |
|------|------|
| 현재 브랜치 | `main` (HEAD: `9839061`) |
| 로컬 브랜치 | `main`, `feature/thermal-update` |
| 최근 머지 | PR #19 feature/thermal-update (TCP/SNST 전환) |
| Working Tree | Clean (변경 없음) |

### 이미 있는 것 ✅

#### 하드웨어/통신 계층
| 구성요소 | 위치 | 설명 |
|----------|------|------|
| ESP32 펌웨어 | [`esp32_sensor_node.ino`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/devices/thermal/thermal_integration/esp32_sensor_node.ino) | SNST 프로토콜 TCP 포트 9000, I2C+SPI 센서 통신 |
| RPi TCP 수신기 | [`tcp_thermal_receiver_rpi.py`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/devices/thermal/thermal_integration/tcp_thermal_receiver_rpi.py) | FPN + 드리프트 보정, OpenCV Jet colormap 시각화 |
| Frame Parser | [`frame_parser.py`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/devices/thermal/src/frame_parser.py) | 4960 float → (62,80) 변환, NaN/Inf 검출, INT8 정규화 |
| SNST 프로토콜 | [`snst.py`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/shared/protocols/snst.py) | 헤더 파싱, CRC16, 센서 타입 정의 |
| 캘리브레이션 | [`thermal_calibration.npz`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/devices/thermal/thermal_sensor_test/thermal_calibration.npz) | FPN 오프셋 맵 + 칩온도 베이스라인 |

#### AI 추론 계층
| 구성요소 | 위치 | 설명 |
|----------|------|------|
| **TFLite 모델** | [`thermal_fall_int8_v0.1.0.tflite`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/ondevice_ai/models/thermal/thermal_fall_int8_v0.1.0.tflite) | **318,184 bytes**, INT8 양자화, **3-class** |
| 모델 매니페스트 | [`model_manifest.json`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/ondevice_ai/models/model_manifest.json) | input: [1,62,80,1] int8 / output: [1,3] int8 |
| ThermalInterpreter | [`thermal_interpreter.py`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/ondevice_ai/inference/thermal_interpreter.py) | SHA-256 검증, 멀티 프레임워크 TFLite import, INT8 양자화/역양자화 |
| InferenceResult | [`inference_result.py`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/ondevice_ai/inference/inference_result.py) | sensor_id, valid, state, score, confidence, latency_ms, metadata |
| Provider 계약 | [`provider_contract.py`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/ondevice_ai/sensors/provider_contract.py) | `SensorProvider` Protocol: connect/read/close + 결과 검증 |
| BaseSensor | [`base_sensor.py`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/shared/contracts/base_sensor.py) | `SensorState` enum (NORMAL, NOT_CONNECTED, NAN_OR_INF 등) |
| 단위 테스트 | [`test_thermal_interpreter.py`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/ondevice_ai/tests/test_thermal_interpreter.py), [`test_v5_release.py`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/ondevice_ai/tests/test_v5_release.py) | SHA-256 검증, NaN 거부, fail-closed, 합성 프레임 테스트 |

### 모델 상세 사양 🔬

```
model_id       : thermal_fall_int8
version        : 0.1.0
file           : thermal_fall_int8_v0.1.0.tflite
size           : 318,184 bytes
sha256         : 5b56da8d127ccef85f30b6459cc0cfe2d86490e41f3caa5bd2a7b70bbc46ae84
input_shape    : [1, 62, 80, 1]  (INT8, scale=0.003921568859368563, zero_point=-128)
output_shape   : [1, 3]          (INT8, scale=0.00390625, zero_point=-128)
class_map      : 0=NOT_HUMAN, 1=HUMAN_NORMAL, 2=HUMAN_FALL
quantization   : Full INT8
```

### Mock/Simulated 프레임 패턴 (제거/격리 대상) ⚠️

| 파일 | 패턴 |
|------|------|
| [`thermal44_driver.py`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/devices/thermal/src/thermal44_driver.py) | 배경 `24.0°C` + 인체 블록 `33.5°C` (20:40, 30:50) |
| [`mock_sensor.py`](file:///c:/Users/KIM TAEGYUN/Desktop/safenest-embedded-competition/devices/thermal/src/mock_sensor.py) | 배경 `22.0°C` + 낙상 블록 `34.5°C` (45:60) / 정상 블록 `33.0°C` (15:50) |

> [!CAUTION]
> 이 합성 프레임이 **Real Validation의 PASS 근거로 사용되면 안 됩니다.** 검증 시 실기기 데이터와 명확히 분리해야 합니다.

### 아직 없는 것 / 검증 필요 ❌
| 항목 | 상태 |
|------|------|
| **실기기 프레임 → AI 추론** E2E 파이프라인 | 미검증 |
| 실제 센서 프레임으로 TFLite 추론 | 합성 프레임만 테스트됨 |
| Fail-closed 동작 (단선/손상 프레임) | 체계적 테스트 없음 |
| 성능 지표 (p50/p95 지연시간) | 미측정 |
| 안전 시나리오별 예측 분포 | 미기록 |
| 실기기 재연결(reconnect) 테스트 | 미구현 |

### 센서 하드웨어 사양
| 항목 | 값 |
|------|-----|
| 센서 | Heimann HTPA (Thermal-90 모듈 / FOV 44° → "Thermal-44") |
| 해상도 | **62 × 80** (4,960 픽셀) |
| 1프레임 크기 | 5,040 words = **10,080 bytes** |
| 헤더 | Words 0~79 (160B): Frame Counter, VDD, Die Temp, CRC |
| 픽셀 데이터 | Words 80~5,039 (9,920B): uint16 RAW ADC 값 |
| 설정 인터페이스 | I2C (주소 0x40, 400kHz) — 모드/프레임레이트/방사율 설정 |
| 데이터 인터페이스 | SPI (Mode 0, D_READY 핀 동기화) — 고속 프레임 수신 |
| 통신 방식 | ESP32 → **TCP 포트 9000** → RPi (SNST 프로토콜) |
| 보정 | FPN 보정 + 열적 드리프트 보정 (계수 **-1.02**) |
| 온도 변환 | `raw_value / 100.0` (°C) |

---

## 🗺️ 단계별 실행 매뉴얼 (6단계)

### Step 1. 환경 구축 및 감사(Audit) — Phase 0~1
> 📍 **작업 위치**: PC(로컬) + 라즈베리파이 5

**내가 (AI) 하는 일:**
- `feature/thermal-v5-real-validation` 브랜치 생성 (**승인 후**)
- `Embedded_대회/Thermal_V5_Validation/` 폴더 생성 (**승인 후**)
- Phase 0 읽기전용 감사(Audit) 14개 항목 보고서 작성
- 검증 스크립트 템플릿 준비

**태균님이 하실 일 (하드웨어 확인):**
1. ESP32 + Thermal-90 센서가 올바르게 연결되어 있는지 확인
   - I2C (SDA/SCL) + SPI (MOSI/MISO/SCK/CS) + D_READY 핀
2. ESP32에 `esp32_sensor_node.ino` 펌웨어가 업로드되어 있는지 확인
3. 라즈베리파이 5 전원 ON
4. ESP32와 RPi가 같은 Wi-Fi 네트워크에 있는지 확인
5. SSH 접속 테스트: `ssh sandi@192.168.1.44`

**결과물**: Phase 0 감사 보고서 + 환경 구축 완료

---

### Step 2. 실기기 Raw 프레임 수신 및 파싱 검증 — Phase 2~3
> 📍 **작업 위치**: 라즈베리파이 5 (SSH)

**내가 (AI) 하는 일:**
- 실기기 TCP 프레임 캡처 스크립트 작성
- SNST 프로토콜 파싱 → 62×80 온도 행렬 추출
- `ThermalFrameParser` 실기기 프레임 통과 테스트

**검증 체크리스트:**
- [✅] 전체 프레임 바이트 수 = 10,080 bytes
- [✅] `ThermalFrameParser.parse_raw_buffer()` 성공 (어댑터 적용)
- [✅] 출력 shape = `(62, 80)`, dtype = `float32`
- [✅] 온도 min/max/mean 현실적인 범위 (예: 15~40°C)
- [✅] NaN/Inf 픽셀 = 0개
- [✅] 프레임 간격 / 실측 FPS
- [✅] 연속 10+ 프레임 캡처 성공
- [✅] SNST CRC16 검증 통과

**태균님이 하실 일:**
- RPi에서 제가 알려주는 명령어 실행
- 캡처 로그를 저에게 공유

**결과물**: Raw 프레임 검증 보고서

---

### Step 3. 시각화 + 실기기 TFLite 추론 — Phase 4~6
> 📍 **작업 위치**: 라즈베리파이 5

**내가 (AI) 하는 일:**
- 실제 온도값 기반 **터미널 ASCII 히트맵** 시각화 코드 작성
  - frame #, min/max/mean 온도, FPS, valid pixel ratio 표시
- **실제 프레임 → INT8 양자화 → TFLite 추론** E2E 스크립트 작성
- 모델 SHA-256 검증: `5b56da8d127ccef85f30b6459cc0cfe2d86490e41f3caa5bd2a7b70bbc46ae84`
- 매니페스트 일치 확인

**핵심 PASS 기준:**
- [✅] **실제** 열화상 프레임으로 추론 (합성 24°C/33.5°C 프레임 ❌)
- [✅] `fallback_used = false`
- [✅] 추론 결과: class_index (0~2), class_name, probabilities[3], latency_ms

**모델 경계 선언 (Phase 6):**
| 사실 | 진술 |
|------|------|
| 모델 출력 | `NOT_HUMAN` / `HUMAN_NORMAL` / `HUMAN_FALL` |
| 의미 | 열화상 패턴 기반 자세 분류일 뿐, **의료적 진단 아님** |
| "따뜻한 물체 = 사람" | ❌ 그렇게 주장할 수 없음 |
| 최종 위험 판정 | Risk Engine(센서 퓨전)에서 수행 |

**결과물**: 실기기 TFLite 추론 보고서 + 시각화 스크린샷

---

### Step 4. InferenceResult & Provider + 안전 시나리오 — Phase 7~10
> 📍 **작업 위치**: 라즈베리파이 5

**내가 (AI) 하는 일:**
- V5 InferenceResult 필드 검증 (`sensor_id == "thermal44"` 등)
- `SensorProvider` 계약 검증: `connect()` → `read()` → `close()`
- 기존 데이터셋 탐색 (`processed_thermal_80x62.npz` 등) → REAL/SYNTHETIC 분류
- 안전 시나리오 테스트 스크립트 작성

**안전 시나리오 (위험한 낙상 재현 ❌):**
| 코드 | 시나리오 | 태균님 동작 |
|------|----------|-------------|
| A | 빈 장면 | 센서 앞에 아무도 없는 상태 |
| B | 서 있는 사람 | 센서 앞에 서 계세요 |
| C | 앉아 있는 사람 | 의자에 앉으세요 |
| D | 안전하게 누워 있는 사람 | 바닥에 천천히 눕으세요 |
| E | 시야 진입/이탈 | 천천히 들어왔다 나가세요 |
| F | 부분적으로 보이는 사람 | 센서 시야 가장자리에 서세요 |

**결과물**: Provider 검증 + 시나리오별 예측 분포 보고서

---

### Step 5. Fail-Closed & 성능 벤치마크 — Phase 11~12
> 📍 **작업 위치**: 라즈베리파이 5

**내가 (AI) 하는 일:**
- 장애 시나리오 테스트 스크립트:

| 테스트 | 기대 결과 |
|--------|----------|
| 센서 연결 해제 | `valid=false`, `state=NOT_CONNECTED` |
| 불완전 프레임 (바이트 부족) | `valid=false`, `state=INVALID_FORMAT` |
| 손상 프레임 | `valid=false`, 명시적 에러 |
| NaN/Inf 온도 | `valid=false`, `state=NAN_OR_INF` |
| 반복된(stale) 프레임 | `valid=false`, `state=STALE` |
| connect() 전 read() | `valid=false`, 에러 |
| close() 후 read() | `valid=false`, 에러 |
| reconnect | 정상 복구 |

- 성능 측정:
  - 실측 FPS, 유효 프레임 %, Parser 에러 %
  - TFLite 추론 지연시간 (**p50 / p95 / max**)
  - Provider 지연시간
  - CPU/RAM 사용량 (가능 시)

**태균님이 하실 일:**
- 제가 지시할 때 센서 전원 케이블 분리 → 재연결

**결과물**: Fail-closed 보고서 + 성능 벤치마크

---

### Step 6. 테스트 코드 & 최종 보고서 — Phase 13 + Final
> 📍 **작업 위치**: PC (로컬)

**내가 (AI) 하는 일:**
- `feature/thermal-v5-real-validation` 브랜치에 테스트 코드 추가
  - 유효 프레임 파싱 / 잘못된 크기 / 손상 데이터 / NaN·Inf
  - stale 프레임 / disconnect / Provider 계약
  - **Mock/합성 테스트와 실기기 검증 명확히 분리**
- **최종 보고서 작성 (한국어)**: `Thermal-44 실기기 V5 On-Device AI 검증`

**최종 판정 기준 (10개 모두 충족 시 PASS):**

```
┌──────────────────────────────────────────────────┬────────┐
│ 항목                                              │ 상태   │
├──────────────────────────────────────────────────┼────────┤
│ 1. 실제 Thermal-44 하드웨어 프레임 수신            │  ✅    │
│ 2. 실제 프레임 Parser 동작                         │  ✅    │
│ 3. 합성 24°C/33.5°C 프레임을 PASS 근거로 미사용    │  ✅    │
│ 4. 실제 온도 행렬이 V5 전처리에 도달                │  ✅    │
│ 5. 실제 INT8 TFLite 추론 실행                      │  ✅    │
│ 6. fallback = false                               │  ✅    │
│ 7. V5 InferenceResult 통과                        │  ✅    │
│ 8. Provider 통과                                  │  ✅    │
│ 9. 손상/단선 프레임 Fail-closed                    │  ✅    │
│ 10. 관련 테스트 통과                               │  ✅    │
├──────────────────────────────────────────────────┼────────┤
│ 최종: 모두 ✅ → PASS / 하나라도 ❌ → INCOMPLETE     │  ✅ PASS │
└──────────────────────────────────────────────────┴────────┘
```

---

## ⚙️ Git 규칙

| 규칙 | 내용 |
|------|------|
| 작업 브랜치 | `feature/thermal-v5-real-validation` |
| 수정 금지 | mmWave, PIR, CO2, Risk Engine, 대시보드, TFLite 학습/모델 |
| 자동 Push/Merge | ❌ (태균님 승인 후에만) |
| 모델 재학습 | ❌ 절대 불가 |

## 📁 작업 폴더 구조 (예정)

```
Embedded_대회/Thermal_V5_Validation/
├── scripts/               # 검증 스크립트 (프레임 캡처, 추론, 시각화 등)
├── captured_data/          # 캡처된 실기기 프레임 데이터
├── reports/               # 단계별 보고서
├── tests/                 # 실기기 검증 테스트 코드
└── README.md              # 검증 작업 개요
```

---

## User Review Required

> [!IMPORTANT]
> **승인이 필요한 사항 3가지:**
> 1. `feature/thermal-v5-real-validation` 브랜치를 생성해도 될까요?
> 2. `Embedded_대회/Thermal_V5_Validation/` 폴더를 생성해도 될까요?
> 3. 현재 하드웨어 상태를 알려주세요:
>    - ESP32 + Thermal-90 센서가 연결되어 있나요?
>    - 라즈베리파이 5가 켜져 있고, SSH 접속(`ssh sandi@192.168.1.44`)이 가능한가요?
>    - ESP32와 RPi가 같은 Wi-Fi 네트워크에 있나요?

## Open Questions

> [!NOTE]
> **확인 질문:**
> 1. 기존 `Embedded_대회/Thermal_Test/`나 `Thermal_Streaming_System/`에 **실제 센서에서 수집한 데이터**가 있나요? 있다면 `REAL_REPLAY` 데이터로 활용할 수 있습니다.
> 2. 라즈베리파이에 **TFLite Runtime**이 설치되어 있나요? (RPi 터미널에서 `pip list | grep tflite` 확인)
> 3. `ondevice_ai/thermal/processed_thermal_80x62.npz` 파일은 실제 센서 데이터인가요, 합성/Zenodo 데이터셋인가요?
