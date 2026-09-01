# SafeNest 대상 수상형 팀 운영 모델

> [!NOTE]
> **구조 표기 안내 (2026-08-03 추가)**
> 이 문서의 "코드 경계"와 디렉터리 트리는 팀 운영 모델을 설계할 당시의 **계획안**이며,
> 실제로 구현된 저장소 구조가 아니다. 현재 구조는 기기·책임 영역 중심이며
> 루트 [`README.md`](../../README.md)의 Repository layout과 [`.github/CODEOWNERS`](../../.github/CODEOWNERS)가 기준이다.
> 역할 배분과 승인 원칙(2절 이하)은 계속 유효하다.

## 1. 지휘 원칙

- 이 기본 채팅을 `00_COMMAND_CENTER`로 유지한다.
- 여기서는 범위, 우선순위, 아키텍처, 인터페이스, KPI 합격/불합격, 제출물만 결정한다.
- 긴 컴파일 로그와 단일 센서 디버깅은 담당 채팅에서 처리하고, 증거와 결론만 기본 채팅으로 올린다.
- 한 산출물에는 최종 책임자 1명만 둔다. 협업자는 있어도 승인자는 중복하지 않는다.
- 기능 완료는 “코드 작성”이 아니라 테스트 증거, 로그, 사진, 재현 절차까지 포함한다.

## 2. 5인 역할 배분

| 사람 | 단일 최종 책임 | 핵심 산출물 | 교차검수 |
|---|---|---|---|
| 김진수(조장) | 시스템 아키텍처·통합 릴리스·심사 전략 | 인터페이스 계약, 통합 빌드, 일정/리스크, 발표·보고서 | 모든 KPI와 PR 최종 승인 |
| 유승하 | ESP 센서 노드·전원·배선 | XIAO 펌웨어, SCD40/PIR, 배선도/BOM, HIL 테스트 | 강유나가 배선·PIR 검수 |
| 김태균 | Thermal-44 파이프라인 | Pi 드라이버, 보정, 프레임/인체 blob 특징, 성능 로그 | 한준우가 fusion 입력 검수 |
| 한준우 | mmWave·센서 융합·엣지 모델 | 레이더 로거/필터, 위험도 엔진, AI 1종, KPI 분석 | 김진수가 안전 로직 검수 |
| 강유나 | 대시보드·경보·하우징/시연 UX | 실시간 UI, 설명 가능한 경보, PIR 보조시험, 하우징·부스 UX | 김진수가 정보전달력 검수 |

김진수는 mmWave를 직접 주 구현하지 않고 한준우의 결과를 요구사항·안전·심사 관점에서 승인한다. 그래야 조장이 통합과 발표를 놓치지 않는다.

## 3. 채팅/코드 작업 분리

### 00_COMMAND_CENTER - 현재 기본 채팅

- 소유자: 김진수 + 총괄 어드바이저
- 입력: 각 작업 채팅의 주간/일일 요약, 테스트 증거, 변경 제안.
- 출력: 다음 우선순위, 인터페이스 승인, 합격/불합격, 범위 삭제 결정.
- 금지: 단일 컴파일 오류를 수십 메시지 동안 디버깅하기.

### 01_ESP_HARDWARE

- 소유자: 유승하, 검수: 강유나.
- 범위: XIAO ESP32-C6, MR60 kit 연결 유지, SCD40, PIR, 전원, 배선, 센서 텔레메트리.
- 책임 경계: ESP에서는 위험도·AI 판정을 하지 않고 원시값, 타임스탬프, 유효성, 오류상태만 Pi로 전송.
- 코드 경계: `firmware/xiao_esp32c6/`, `hardware/wiring/`, `tests/hil/esp/`.
- 완료 정의: `HARDWARE_RUNBOOK.md` Gate A~E 통과, 30분 무재부팅, Pi 패킷 누락률 1% 미만.

### 02_THERMAL_PIPELINE

- 소유자: 김태균, 검수: 한준우.
- 범위: Thermal-44 Pi 직결, I2C 설정/SPI 프레임, 내부온도 보정, blob/특징 추출.
- 코드 경계: `gateway/thermal/`, `tests/hil/thermal/`.
- 완료 정의: 30분 프레임 드롭 측정, 사람/히터/빈 공간 데이터셋, 지연·FPS·보정 오차 보고.

### 03_MMWAVE_FUSION_AI

- 소유자: 한준우, 검수: 김진수.
- 범위: mmWave 원시 로그, UNKNOWN 상태, 시간필터, 위험도 R, AI 후보 1종, 룰 폴백.
- 코드 경계: `gateway/mmwave/`, `gateway/fusion/`, `models/`, `tests/kpi/`.
- 완료 정의: `MMWAVE_TUNING.md` KPI 표, confusion matrix, 지연, 모델 없는 폴백 시험.

### 04_DASHBOARD_ALERT_ENCLOSURE

- 소유자: 강유나, 검수: 김진수.
- 범위: 실시간 대시보드, 경보 근거 표시, 센서 장애 표시, 부저/경광등 구동 UX, 하우징·시연 동선.
- 코드 경계: `web/dashboard/`, `gateway/alerts/`, `hardware/enclosure/`.
- 완료 정의: 정상/주의/위험/UNKNOWN 4상태를 3초 안에 설명할 수 있는 화면, 경보 로그와 UI 일치.

### 05_INTEGRATION_QA_DEMO

- 소유자: 김진수, 참여: 전원.
- 범위: 통합, 회귀시험, 8시간/24시간 로그, 시연 스크립트, 백업 플랜.
- 코드 경계: `contracts/`, `gateway/app/`, `tests/e2e/`, `docs/evidence/`.
- 완료 정의: 한 명이 새 Pi에서 문서만 보고 30분 이내 실행, 3분 시연 10회 연속 성공.

### 06_SUBMISSION_PITCH

- 소유자: 김진수, 증거 제공: 전원.
- 범위: 20P 개발완료보고서, 3분 영상, 2P 작품소개서, 발표/Q&A, 라이선스 목록.
- 파일 경계: `docs/submission/`, `docs/evidence/`, `LICENSES/`.
- 완료 정의: 공식 필수항목·분량·파일명·URL·720p 요건 체크리스트 전부 통과.

## 4. 각 새 채팅의 첫 프롬프트 템플릿

아래를 복사하고 대괄호만 바꾼다.

```text
너는 SafeNest 프로젝트의 [작업명] 전담 엔지니어다.
최종 책임자: [이름], 검수자: [이름].
담당 디렉터리: [경로].
성공 기준: [정량 완료 정의].

반드시 지킬 것:
1) PROJECT_PROGRESS.md, HARDWARE_RUNBOOK.md, MMWAVE_TUNING.md와 contracts/를 먼저 읽는다.
2) 담당 디렉터리 밖 파일은 읽을 수 있지만, 인터페이스 변경이나 수정은 00_COMMAND_CENTER 승인 전 하지 않는다.
3) 한 번에 센서/기능 하나만 구현하고 테스트 증거를 남긴다.
4) 센서 결측을 0이나 정상으로 치환하지 않는다.
5) 매 작업 종료 시 아래 형식으로 보고한다.

STATUS: PASS / FAIL / BLOCKED
DONE: 완료한 것
EVIDENCE: 명령, 로그, 측정값, 사진/파일 경로
FILES: 수정 파일
INTERFACE_CHANGE: 없음 / 제안 내용
RISKS: 남은 위험
NEXT: 다음 1개 행동
```

## 5. 저장소 구조

```text
contracts/
  telemetry.schema.json
  risk_event.schema.json
firmware/xiao_esp32c6/
gateway/
  app/
  thermal/
  mmwave/
  fusion/
  alerts/
web/dashboard/
models/
hardware/
  wiring/
  enclosure/
tests/
  hil/esp/
  hil/thermal/
  kpi/
  e2e/
docs/
  evidence/
  submission/
data/
  samples/
src/tools/
LICENSES/
```

`data/raw/`의 대용량 원본과 개인정보 가능 데이터는 Git에 올리지 않는다. 익명화된 최소 샘플만 `data/samples/`에 둔다.

## 6. 인터페이스 계약 우선

코딩 전에 `telemetry.schema.json`과 `risk_event.schema.json`을 동결한다.

최소 텔레메트리 필드:

- `schema_version`, `device_id`, `seq`, `ts_utc`, `ts_monotonic_ms`
- `mmwave`, `thermal`, `pir`, `environment` 객체
- 센서마다 `value`, `valid`, `state`, `error_code`, `source_ts`
- `firmware_version`, `config_hash`

최소 위험 이벤트 필드:

- `event_id`, `risk_level`, `reason_codes`, `confidence`
- `sensor_evidence`, `rule_version`, `model_version`
- `started_at`, `acknowledged_at`, `cleared_at`

계약 변경은 김진수가 승인하고 모든 채팅에 동일하게 전달한다.

## 7. Git 작업 규칙

- `main`은 항상 시연 가능 상태로 유지한다.
- 작업 브랜치: `feat/esp-node`, `feat/thermal`, `feat/fusion`, `feat/dashboard`, `test/kpi`.
- 한 PR은 한 기능과 한 검증 증거만 포함한다.
- PR 필수 항목: 목적, 인터페이스 영향, 실행 명령, 테스트 결과, 롤백 방법, 관련 증거 경로.
- 작성자 외 1명 검수 + 김진수 통합 승인 후 병합한다.
- KPI 시험 중 사용한 커밋 해시를 데이터 파일과 함께 기록한다.

## 8. 매일 15분 운영

각 담당자는 아래 5줄만 00_COMMAND_CENTER에 올린다.

1. 어제 완료와 증거.
2. 오늘 끝낼 단 하나의 결과.
3. 현재 숫자(KPI/오류 수/프레임률 등).
4. 막힘과 필요한 결정.
5. 인터페이스 변경 여부.

조장은 당일 범위를 추가하기보다 `통과할 게이트 1개`를 지정한다. 금요일에는 통합 브랜치에서 전체 시연을 실행하고 실패를 다음 주 최우선으로 올린다.

## 9. 즉시 실행 순서

1. 01 채팅: Gate A 부품 식별표·사진 완성.
2. 03 채팅: 현재 MR60 펌웨어/라이브러리 버전과 5분 기준 로그 확보.
3. 00 채팅: 위 두 증거를 검수해 전원/핀 확정.
4. 01 채팅: Gate B→C→D→E 순서로 진행.
5. 동시에 02 채팅은 Thermal-44를 Pi 단독으로 실행하되 ESP 배선에는 손대지 않음.
6. 두 센서 경로가 각각 PASS 후에만 05 통합 작업 시작.
