# 08_PAGE_PLAN — 표지 + 콘텐츠 20p (공식 3+10+5+2)

배지 표기: `구현 완료` `SW 검증` `오프라인 AI 검증` `실기기 검증` `통합 HIL` `미검증` `향후 검증`

---
## 표지 (콘텐츠 미포함)
제24회 임베디드SW경진대회 개발완료보고서 / 자유공모 부문 / SafeNest — 엣지 AI 기반 밀폐공간·차량 생명감지 및 위험도 자동경보 시스템 / `[팀번호 확인 필요]_가만있어도SANDI` / 경희대학교

---
# SECTION 1 · 개발 개요 (3P)

## P1 — 「밀폐공간 사고는 '사람이 쓰러진 뒤'에 발견된다」
- 결론: 사고를 못 막는 이유는 감지 수단이 없어서가 아니라, **사람의 상태를 상시 확인할 수단이 없기 때문**.
- 근거: 2014~2023 밀폐공간 질식재해 174건 / 재해자 338명 / 사망 136명(치명률 약 42%) — 각주 "고용노동부 보도자료(2024) 인용, **원문 확인 필요**"
- 산업안전보건법 제619조: 농도 측정 + 감시인 배치 의무 → 소규모 사업장은 상시 배치가 현실적으로 어려움
- 시각: 문제 다이어그램(작업자 진입 → 이상 발생 → 발견 지연 → 사고)
- 심사: 독창성(동기·배경)
- 상태: 통계 `[출처 원문 확인 필요]`

## P2 — 「단일 센서는 '값'은 주지만 '사람이 안전한지'는 답하지 못한다」
- 비교표 (○/△/×): 가스감지기 / CCTV / PIR / 웨어러블 / 단일 mmWave / 단일 열화상 × 축(정지 인체 / 사생활 / 미착용 / 환경 / 오탐 구분)
- 각 한계는 단정 대신 조건부(△) 사용
- **SafeNest 관점 도입**: 문제는 센서 개수가 아니라 "이 증거를 지금 믿어도 되는가"
- 심사: 독창성(차별성)

## P3 — 「SafeNest: 카메라 없이, 증거의 유효성까지 판단하는 엣지 안전 노드」
- 개발 목표 ①~④ (중간계획서 기준, **초기 개발 목표**로 명시)
- 개념도: 4채널 증거 → 유효성/신선도 → 규칙+엣지AI → 위험도(정상 R<30 / 주의 30–65 / 위험 R≥65 / 판단 보류) → 경보/표시/기록
- **소스코드**: `https://github.com/jinsu1011/safenest-embedded-competition` (실제 URL)
- **시연동영상**: `[최종 시연동영상 URL 입력 필요]` — 하이퍼링크 생성 금지
- 심사: 독창성 / 공식 필수(링크)

---
# SECTION 2·3·4 · 개발 환경 + 프로그램 설명 + 장애요인 (10P)

## P4 — 「SafeNest는 3계층 엣지 구조로 동작한다」
- 계층: 감지(4센서) → 수집·검증(ESP32) → 판단(Raspberry Pi 5) → 대응(부저/LCD/Web/로그)
- 개발환경 표: Arduino/PlatformIO(ESP32), Python 3(Pi, 표준 라이브러리 중심), Node.js Express 5(Web), TensorFlow 2.19.1(학습), TFLite INT8(추론), macOS/Pi OS
- **주의: FastAPI·SQLite·WebSocket은 정본 미구현 → 등장 금지 (C1)**
- 심사: 기술성

## P5 — 「4개 센서를 서로 다른 버스로 한 노드에 통합했다」
- 인터페이스 표: MR60BHA2 **UART2** 115200 (RX16/TX17) / SCD4x **I2C** 0x62 (SDA21·SCL22) / PIR **GPIO13** / Thermal-44 **I2C 0x40·0x41 제어 + SPI 데이터** (SCLK18·MISO19·MOSI23·CS27·READY26·**RESET25**)
- 사진 A1(회전 보정) + 3D 개구부 렌더 A8
- 캡션: "CO₂ 검증용 벤치 구성 — **최종 통합 4센서 완제품 아님** `[최종 통합 하드웨어 사진 교체 필요]`"
- 심사: 기술성

## P6 — 「저장소는 기기·책임 영역 기준으로 나뉜다」
- 주요 모듈 표 (경로 / 역할 / 입력 / 출력): `devices/esp32_node/firmware/esp32_sensor_node.ino`, `devices/{mmwave,co2,pir,thermal}/src/`, `shared/contracts/base_sensor.py`, `ondevice_ai/{inference,risk,integrated_node}/`, `integration/pi_lcd/server.py`, `integration/web/`, `hardware/3d_models/`
- 외부 OSS/데이터셋 고지 (규정 제10조③): Zenodo CC BY 4.0 / UCI CC-BY-4.0 / SDT(라이선스 확인 필요) / TFLite / Express
- 심사: 기술성, 정보전달력

## P7 — 「센서에서 게이트웨이까지: SafeNest TCP protocol v1」
- 16바이트 헤더 도해: `SNST`(4) · version 1 · type(1 JSON / 2 thermal) · flags(2) · sequence u32 · payload_length u32, network byte order
- TCP는 경계를 보존하지 않음 → `recv_exact()` 길이 접두 프레이밍
- 주기: PIR 20 ms / CO₂ 250 ms / telemetry 1,000 ms
- 코드 스니펫(3~5줄): `formatNullableFloat()` — **invalid → `null`**
- 심사: 기술성(임베디드SW)

## P8 — 「0은 측정값이지만, 결측은 측정값이 아니다」 ★핵심
- 판정 흐름도: 수신 → magic/version/length 검사 → 스키마 검사 → `valid{}` 확인 → TTL 검사 → LIVE / STALE / INVALID / DISCONNECTED
- 이중 신선도: ESP32(mmWave 5 s · CO₂ 15 s · Thermal 30 s) + Pi(5 s) 독립 판정
- 열화상 무결성: **CRC-16/CCITT-FALSE**(poly 0x1021, init 0xFFFF) + 헤더 min/max 재계산 대조 + 내외부 sequence 일치 + 사용 가능 화소 ≥32 → 불일치 프레임 폐기
- 30 s 무프레임 → GPIO RESET 재초기화
- 배지: `구현 완료` `SW 검증`(본 세션 13 tests 통과)
- 심사: 기술성 + 독창성

## P9 — 「온디바이스 AI는 '모델이 있다'와 '검증됐다'를 구분한다」
- 모델 3종 표: 입력 / 출력 / 양자화 / 검증등급 / 배포상태
  - Thermal `thermal_fall_int8_v0.1.0` (62×80×1 INT8 → 3class) — **실기기 E2E 검증**, 단 `HUMAN_FALL` = **눕기(LYING) 정적 자세 프록시**
  - CO₂ `co2_occupancy_int8_v0.1.0` (3특징 → 2class) — 합성/오프라인 한정
  - mmWave `mmwave_resp_int8` (300샘플 30 s 창 → 3class) — **v0.1.0 배포 차단**, v0.2.0 후보는 **합성 한정**
- 실측(열화상 채널, Pi 5): p50 162.70 / p95 173.90 ms, 4.6 FPS, 유효 97.8% — **범위 명시**
- 차트 CH2 또는 열화상 스팟체크 A9
- 심사: 기술성

## P10 — 「NORMAL과 UNKNOWN은 다르다」 ★최강 페이지
- 정본: `RaspberryPi/Runtime/risk/formula_v1.py` + `risk_formula_v1.json` (`SAFENEST_RISK_V1`)
- 상세 정책: `docs/09_SAFETY_CRITERIA_V1.md`
- R = 100 × (0.25·mmWave + 0.30·CO₂ + 0.15·PIR + 0.30·Thermal)
- 정상 R<30 / 주의(WARNING) 30–65 / 위험 R≥65. 구 V4 CAUTION·R≥60 사용 금지
- 채널 플로어: CO₂ ≥1,500 ppm 주의(별표2 기계환기 예외) 또는 밀실 기준값 \(B\)+700. ≥5,000 ppm 즉시 위험. occupancy는 점수 제외
- 열화상 `HUMAN_FALL_PROXY`는 점수 0.4·비상 없음. mmWave 신경망은 관측 전용, 하드웨어 확인 apnea만 즉시 위험
- 유효 센서만으로 가중치 재정규화. 유효 가중치 <0.5 이면 정상을 INDETERMINATE로 내림
- 전 센서 무효 → `risk_score=None`, `risk_level=None`, `system_health=FAILED`
- 계산 예시(엔진 실행): CO₂ 1,500 ppm + 평온 인체 → R=9.75 정상, 플로어로 주의
- occupancy 로컬라이징은 본 식에서 제외
- 배지: `SW 검증` (`tests/test_risk_formula_v1.py`)
- 심사: 기술성 + 독창성

## P11 — 「실제로 어디까지 돌아가는가」
- 런타임: `integration/start_all.sh` → TCP 9000 수신 + HTTP 8080(`/display` `/control` `/api/state` `/health`) + 부저 GPIO18 880 Hz + 6개 상태
- **차트 CH1**: 실측 CO₂ 6분 세션 (호기 상승 1,493 ppm → 복귀 634 ppm) + **결측 구간을 잇지 않고 공백 표시**
- 검증 매트릭스(요약): 채널별 구현/SW검증/실기기/통합HIL
- 미확보 항목 명시: 실센서 대시보드·LCD 캡처 `[추가 증거 필요]`, 4센서 동시 수신 `미검증`
- 심사: 기술성, 정보전달력

## P12 — 「열화상 스트리밍이 telemetry를 밀어내 전송 구조를 바꿨다」 (장애요인 ①)
- 문제: type 2 프레임 9,952 B × 약 6.25 fps ≈ 60 KB/s를 ESP32 Wi-Fi 단일 TCP로 전송 → 1초 telemetry 주기 붕괴
- 시도 5가지: FreeRTOS 태스크 분리 / 큐 1칸 `xQueueOverwrite` / 512 B 청크 / divider 4→8 / SPI 8 MHz→1 MHz
- **실패 인정**: 구조 개선은 지연을 감췄을 뿐 링크 총 바이트를 줄이지 못함
- 최종: `THERMAL_STREAM_FRAMES = false` — 송신측에서 요약(가장 뜨거운 16화소 중 최저값)만 1초 telemetry에 포함
- 잃은 것: LCD 열화상 영상 제외 (정직하게 명시)
- 별도 열화상 리그는 UDP 분리 경로로 검증됨(범위 구분)
- 심사: 기술성(난이도·문제해결)

## P13 — 「나머지 세 가지 실제 임베디드 문제」 (장애요인 ②)
- ① **GPIO 자원**: XIAO ESP32-C6 외부 11핀 중 D6/D7(내부 UART), D3(레이더 부트/리셋), D1(RGB LED 공유) 제약 → nRESET 미연결 시 카메라 부팅 시퀀스·자동복구 불가 → **ESP32 DevKit V1 교체**, 10신호선 단독 배정, RESET D25 확보
- ② **신호 무결성**: 브레드보드·점퍼에서 SPI 8 MHz·I2C 400 kHz 판독 누락 → **SPI 1 MHz / I2C 100 kHz**, 프레임당 약 81 ms로 divider 8의 160 ms 예산 내 → `READOUT_TOO_SLOW` 해소
- ③ **AI 재현성**: mmWave v0.1.0 재현 검증에서 **클래스 붕괴**(468/468 NORMAL, abnormal·apnea recall 0.0) → **배포 차단(`deployment_allowed:false`)** 후 후보 재수립
- 메시지: 실패를 지우지 않고 차단·기록한 것이 안전 시스템의 요건
- 심사: 기술성

---
# SECTION 5·6 · 차별성 + 파급력 (5P)

## P14 — 「SafeNest의 기술적 차별성 5가지」
① 이종 센서 **증거 융합**(값 수집 아님) ② 카메라 없는 프라이버시 보존 감지 ③ **유효성·신선도를 1급 상태로 관리** ④ **fail-closed: NORMAL≠UNKNOWN** ⑤ 규칙+엣지 AI 하이브리드와 **검증 등급에 따른 배포 통제**
- 각 항목에 근거 파일 경로 + 배지

## P15 — 「기존 방식과의 비교」
- 카테고리 비교표: 사생활 / 정지 인체 증거 / 환경 감시 / 로컬 처리 / 다중 증거 / 무효 데이터 인지 / 이벤트 로그 / 확장성
- 마케팅 체크박스 금지, △ 적극 사용, SafeNest 미구현 항목도 △/× 표기

## P16 — 「현재 완성도: 무엇이 검증됐고 무엇이 남았는가」
- 표: 구성요소 / 구현 / 검증 / 증거 / 남은 과제
  - ESP32 4센서 노드 ● / SW / `.ino` / 4센서 동시 실측
  - SNST v1 송수신 ● / SW(13) / `server.py` / —
  - 유효성·신선도 ● / SW / `fallback.py` / 통합 HIL
  - Risk 엔진 ● / SW(22) / `risk_engine.py` / 실입력 HIL
  - mmWave 채널 ● / **실기기** / 9.990 Hz·오류 0 / 통합
  - CO₂ 채널 ● / **실기기(부분)** / 4세션 CSV / 분리 로그
  - Thermal 채널 ● / **실기기 E2E** / p95 173.9 ms / 정본 노드 경유
  - Web/LCD ● / SW / 13 tests / 실센서 캡처
  - 하우징 ◐ / 설계 / STL 4종 / 출력·조립
- 본 세션 실행: **57 passed / 2 failed** + 소스 내 테스트 함수 1,483개(실행 결과 아님)

## P17 — 「1차 적용처는 밀폐공간, 확장은 차량·창고」
- 주 적용: 맨홀·정화조·집수정 등 밀폐공간 무인 감시 (산안법 제619조 대응 보조)
- 확장 가능성: 통학차량 잔류 감지 / 냉동·양생 창고 (저장소 QR 3종 실재: 밀폐공간 A-01, 통학차량 B-02, 창고 C-03)
- 기대효과는 "가능성"으로 서술, 매출·시장규모 단정 금지

## P18 — 「프로토타입에서 현장까지: 단계형 로드맵」
- 현재(프로토타입, 채널별 검증) → 통합 HIL → 하우징 출력·조립 → 현장 데이터 수집·보정 → 다중 노드 → 인증·평가
- 3D CAD 렌더 A5/A6/A7 배치 + 치수(센서 137×80×60 mm, LCD 240×140 mm, 슬롯 3.5 mm, 편측 유격 0.25 mm)
- 완료된 것/미완료를 시각적으로 명확히 구분

---
# SECTION 7 · 일정 + 업무 분장 (2P)

## P19 — 「실제 개발 일정과 주요 설계 변경」
- 계획 대비 실제: 7월 설계·부품 → 8/1 mmWave 장시간 로그 → 8/2~8/3 저장소 통합·책임영역 재편(`38274c0`) → 8/8 mmWave 라이브 검증·리플레이 벤치 → 8/11 열화상 v5 실기기 E2E → 8/12 CO₂ 실측 4세션 → 8/16~8/21 mmWave M-C0 정합·스냅샷(`3f22fb1`)
- 주요 설계 결정 3개 표시: 보드 교체 / 열화상 전송 구조 전환 / 모델 배포 차단
- **미완료 구간도 표시** (통합 HIL, 시연영상)

## P20 — 「5인 책임 영역과 인터페이스」
- 근거: `.github/CODEOWNERS` (2026-08-03 collaborator 권한 확인 기재) + 실제 산출물
  - **김진수**(팀장, @jinsu1011): mmWave 펌웨어·어댑터·실측, 저장소 통합·구조, 문서 — `devices/mmwave/`, `docs/`
  - **유승하**(@yuseungha): CO₂(SCD40) 연동·실측 4세션, ESP32 4센서 노드, Pi LCD/부저 서버, 회로 — `devices/co2/`, `devices/esp32_node/`, `integration/`
  - **김태균**(@rla1729): Thermal-44 드라이버·프레임 파서·전처리, 열화상 온디바이스 AI 실기기 검증 — `devices/thermal/`
  - **한준우**(@sheepmeat): 데이터셋 출처·분할, 모델 학습·비교·재현, Pi AI 준비, 위험 판단 연계 — `ondevice_ai/`, `shared/contracts/`
  - **강유나**(@yuname121): PIR 어댑터, 3D 하우징 CAD 4종·설계사양, LCD/Web 초기 골격 — `devices/pir/`, `hardware/3d_models/`
- 인터페이스: 센서 계약(`shared/contracts/base_sensor.py`) → 텔레메트리 스키마 `safenest.telemetry.v1` → Risk 입력 계약
- **내부 주의**: 강유나 최종 산출물 상당수가 `yuname121/integration` @ `9e4ddfe…`에 있으며 정본 미병합 → `[팀장 확인 필요]`

---
## 페이지 배분 검증
1(3) + 2·3·4(10: P4–P13) + 5·6(5: P14–P18) + 7(2: P19–P20) = **20** ✅ 표지 제외
