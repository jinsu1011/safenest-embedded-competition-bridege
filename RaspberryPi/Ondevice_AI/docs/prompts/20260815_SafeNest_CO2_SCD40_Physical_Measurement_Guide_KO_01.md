# SafeNest CO₂ SCD40 실측 안내서

이 문서는 SCD40과 SafeNest 장치로 CO₂ 데이터를 실제로 수집하는 담당자를 위한 현장 안내서입니다. 다른 AI 보고서를 먼저 읽지 않아도 오늘 무엇을 켜고, 어떤 상태를 기록하고, 문제가 생겼을 때 무엇을 보존해야 하는지 알 수 있도록 작성했습니다.

현재는 **1차 탐색 실측을 바로 진행할 수 있습니다.** 이 실측은 실제 센서 범위와 변화, 통신 문제, 수집 절차를 알아보는 데 사용합니다. **정식 검증용 실측은 아직 시작하지 않습니다.** ESP32가 “새 SCD40 측정”과 “이전 측정값 재전송”을 구분해 보내는 기능이 실제 장치에 반영되고 live 확인된 뒤에 시작합니다.

| 실측 종류 | 지금 가능한가 | 목적 |
|---|---|---|
| 1차 탐색 실측 | 가능 | 실제 센서·환경·통신·수집 흐름 확인 |
| 정식 검증용 실측 | 아직 대기 | 나중에 실제 장치 모델 성능을 평가할 자료 수집 |

## 처음 하는 사람은 이것만 읽으세요

1. ESP32, SCD40, Raspberry Pi가 켜져 있는지 확인합니다.
2. Pi의 `/health` 주소에서 CO₂ payload가 들어오는지 확인합니다.
3. 이번 세션을 처음부터 끝까지 사람이 없는 상태(`VACANT`)로 할지, 사람이 있는 상태(`OCCUPIED`)로 할지 먼저 정합니다.
4. 팀 저장소의 현재 capture utility로 원본 CSV를 수집합니다.

   ```bash
   cd <team-repository-root>
   python3 devices/co2/firmware/capture_scd40.py \
     --url http://<pi-host>:8080/health \
     --duration-sec 300 \
     --interval-sec 1 \
     --scenario VACANT_STABLE \
     --output <output-root>/<YYYYMMDD_HHMM>_VACANT_<session-id>.csv
   ```

   사람이 있는 세션은 `--scenario OCCUPIED_STABLE`로 바꾸고, 실제 장면을 메모합니다.
5. 측정하는 동안 같은 CO₂ 값이 반복되거나 오류가 생겨도 raw 파일을 고치지 않습니다. 오류와 중단은 그대로 기록하고 메모합니다.
6. 측정이 끝나면 capture 파일, 실제 장면 기록, operator note와 가능한 경우 checksum을 함께 보냅니다.
7. 오늘의 파일은 “1차 탐색 실측”으로 표시합니다. 이 데이터를 바로 모델 정확도 자료라고 부르지 않습니다.

이 순서가 오늘 할 일의 전부입니다. 아래 내용은 각 단계가 왜 필요한지와 문제가 생겼을 때의 처리 방법을 설명합니다.

## 1. 측정 전에 확인할 것

실측을 시작하기 전에 다음을 준비합니다.

- 실제 사용할 SCD40–ESP32–Pi 장치와 장치 ID
- Pi `/health` URL
- capture를 실행할 컴퓨터 또는 Pi의 출력 경로
- operator ID, 위치, 세션 이름
- 이번 세션의 실제 상태와 메모를 기록할 문서

처음에는 한 세션 안에서 상태가 바뀌지 않는 간단한 측정을 권장합니다. 사람이 없는 방을 처음부터 끝까지 유지하는 `VACANT_STABLE` 세션이나, 사람이 있는 상태를 끝까지 유지하는 `OCCUPIED_STABLE` 세션이 좋습니다.

### VACANT — 사람 없음

측정 시작부터 종료까지 해당 공간에 사람이 없는 상태입니다. CO₂가 이미 높거나 측정 중에도 높게 남아 있어도, 실제로 사람이 없었다면 `VACANT`입니다.

### OCCUPIED — 사람 있음

측정 시작부터 종료까지 한 명 이상의 사람이 실제로 공간에 있는 상태입니다. 사람이 있는데 CO₂가 아직 낮거나 바로 오르지 않아도 `OCCUPIED`입니다.

라벨은 CO₂ 숫자, CO₂가 올라가는 시각, threshold crossing, 모델 prediction으로 결정하지 않습니다. 실제 장면을 기준으로 operator가 기록합니다.

## 2. 처음에는 단순한 세션부터 수집하기

현재 운영 권고는 한 세션을 최소 300초, 즉 5분 동안 진행하고 capture interval은 1초로 두는 것입니다. 300초는 통계적 sample-size 보장이 아닙니다. 측정 시작 직후의 warm-up과 최근 약 150초 history가 쌓이는 모습을 확인하기 위한 실무적인 최소 권고입니다.

측정 시작 직후 몇 개의 값만 보고 세션을 끝내지 마십시오. 초반에는 CO₂ slope를 만들 과거 값이 부족할 수 있습니다. 이 초기 row도 버리지 않고 raw 파일에 남깁니다.

처음에는 다음과 같이 각각 여러 세션을 모으는 것이 좋습니다.

```text
세션 A: 사람이 없는 방을 5분 이상 유지 → VACANT_STABLE
세션 B: 사람이 있는 방을 5분 이상 유지 → OCCUPIED_STABLE
```

상태가 단순한 세션은 실제 장치 range와 통신 상태를 먼저 이해하기 쉽습니다. 사람이 들어오고 나가는 전환 세션은 이 기본 세션을 확인한 뒤에 진행합니다.

## 3. 60초를 운영자가 어떻게 이해하면 되는가

측정 담당자가 스톱워치를 보고 정확히 60초마다 숫자를 직접 만들 필요는 없습니다. Pi가 `/health`를 1초 간격으로 확인하더라도, SCD40이 1초마다 새 measurement를 만든다는 뜻은 아닙니다.

현재 AI 계약에서 약 60초는 모델 입력을 만들 기회에 대한 nominal interval입니다. SCD40의 실제 측정 주기, ESP32/Pi의 polling·transport 주기와는 별개입니다. raw 데이터는 실제 발생한 timestamp와 상태 그대로 기록하고, 모델에 사용할 수 있는 chronology인지는 나중에 후처리에서 판단합니다.

따라서 이전 CO₂ 값을 복사해 60초마다 새 sample처럼 만들지 않습니다. 실제 새 값이 없으면 missing 또는 failure 상태를 남깁니다.

## 4. 최근 150초와 측정 시작 직후의 warm-up

현재 후보는 최근 약 150초의 과거 측정으로 CO₂ 변화량을 계산합니다. 현재 값과 약 150초 전 값의 관계를 볼 수 있어야 하므로, 측정 시작 직후에는 slope가 비어 있을 수 있습니다.

유효한 새 측정 event 사이에 90초를 넘는 gap이 생기면 history를 다시 시작합니다. 중간 값을 만들어 gap을 숨기거나, stale 값을 새 측정처럼 복사하지 않습니다. 초반 warm-up row, missing row, stale/error row 모두 raw evidence로 보존합니다.

이 계산은 운영자가 하는 일이 아닙니다. Pi 또는 승인된 후처리 경로가 담당합니다. 이 안내서에서 측정 담당자에게 필요한 일은 실제 측정 시간과 상태, 오류를 정확히 남기는 것입니다.

## 5. 지금 진행하는 1차 탐색 실측

### 이 실측의 목적

1차 탐색 실측은 실제 프로젝트 evidence입니다. 다음을 확인하기 위해 사용합니다.

- 실제 SCD40 CO₂ range와 시간에 따른 변화
- 사람이 없거나 있을 때의 qualitative pattern
- CO₂ 상승과 회복 양상
- ESP32–Pi transport 안정성
- stale, missing, error, reconnect 상태
- capture 절차와 운영자가 겪는 불편
- 앞으로 정식 수집을 시작할 때 필요한 준비

다만 현재 경로에서는 모든 packet이 실제 새 SCD40 측정인지 완전히 확인할 수 없습니다. 그러므로 이 데이터는 실제 장치 동작을 이해하는 데 쓰되, 이 데이터만으로 공식 모델 Accuracy, F1, precision, recall을 확정하지 않습니다.

### 탐색 capture 명령

팀 저장소의 현재 legacy capture utility를 실행합니다. 이 utility는 `/health` 응답, host wall-clock/monotonic timestamp, CO₂ 값, packet 정보, `valid`, `connected`, `fresh`, age, status, error를 CSV에 남깁니다.

```bash
cd <team-repository-root>
python3 devices/co2/firmware/capture_scd40.py \
  --url http://<pi-host>:8080/health \
  --duration-sec 300 \
  --interval-sec 1 \
  --scenario VACANT_STABLE \
  --output <output-root>/<YYYYMMDD_HHMM>_VACANT_<session-id>.csv
```

파일이 이미 있으면 덮어쓰지 않습니다. 새 session 경로를 만들고, output 파일은 수집 후 Excel이나 편집기로 열어 저장하지 않습니다.

### 측정 중 눈으로 확인할 것

모델 prediction을 모니터링하는 것이 아니라 수집 상태를 봅니다.

- CO₂ payload가 계속 들어오는가?
- capture 파일 크기와 row가 계속 늘어나는가?
- 연결 끊김이나 timeout이 반복되는가?
- `fresh`, `age`, `status`, `valid`가 어떻게 바뀌는가?
- 사람이 실제로 들어오거나 나간 시각이 있는가?

값이 이상해 보여도 현장에서 숫자를 고치지 않습니다. 어떤 시각에 어떤 상태였는지를 operator note에 적습니다.

### 탐색 ground truth 기록

stable session은 다음처럼 기록합니다.

```text
VACANT: 13:50:00부터 13:55:00까지 사람이 없음
OCCUPIED: 14:00:00부터 14:05:00까지 사람이 있음
```

최소한 session ID, operator ID, 위치와 장치, 실제 시작·종료 시각, VACANT/OCCUPIED, 센서 끊김·stale·error·missing 관찰을 남깁니다.

전환 session에서는 사람의 실제 입장·퇴장 시각을 별도로 기록합니다. CO₂가 상승한 시각을 입장 시각으로 바꾸지 않습니다. 실제 시각을 확실히 모르면 transition 또는 uncertain이라고 적습니다.

### 예시: 사람 없는 방 측정

1. `13:50`에 장치와 Pi를 켜고 `/health` 응답을 확인합니다.
2. 방에서 모든 사람이 나간 뒤, 세션 메모에 `VACANT`를 기록합니다.
3. capture를 실행하고 최소 5분 동안 방을 비워 둡니다.
4. 같은 CO₂ 값이 반복되어도 raw CSV를 수정하지 않습니다.
5. 연결이 끊기면 시각과 화면에 보인 상태를 operator note에 적습니다.
6. capture를 종료하고 CSV와 note를 확인합니다.
7. 원본 파일을 닫은 뒤 가능한 경우 checksum을 생성해 함께 제출합니다.

사람이 있는 세션도 같은 절차를 따르되, 실제 사람이 측정 내내 공간에 있었는지 확인하고 `OCCUPIED`로 기록합니다.

## 6. 문제가 생겼을 때

### CO₂ 값이 안 들어올 때

값을 임의로 만들거나 이전 값을 복사하지 않습니다. timeout, 연결 끊김, missing response를 그대로 남기고, 발생 시각과 재연결 시각을 note에 기록합니다. 부분적으로 끝난 session도 삭제하지 말고 incomplete session으로 보존합니다.

### 같은 값이 계속 나올 때

곧바로 센서 고장이라고 결론 내리지 않습니다. 같은 값이 cached telemetry인지, 실제로 변화가 없는 것인지, transport가 멈춘 것인지 현재 exploratory path만으로는 항상 구분할 수 없습니다. raw response와 상태를 그대로 보존하고 관찰 내용을 적습니다.

### ESP32 또는 Pi가 재연결될 때

끊긴 시각, 복구된 시각, 화면의 상태와 session 조건을 적습니다. 장치가 다시 시작되거나 위치가 바뀌면 앞뒤 데이터를 하나의 연속 세션인 것처럼 조용히 붙이지 않습니다. 필요하면 새 session으로 시작합니다.

### `valid=false`, stale, error가 생길 때

해당 row를 삭제하거나 정상값으로 대체하지 않습니다. raw 파일에는 실패 상태가 남아야 나중에 장치 문제와 모델 문제를 구분할 수 있습니다.

## 7. 측정이 끝나면 무엇을 보내야 하는가

### 탐색 실측

현재 팀 utility는 원본 CSV를 만듭니다. 담당자는 여기에 실제 장면과 운영 상황을 설명하는 note를 함께 보냅니다.

```text
<session-directory>/
  capture.csv                 센서에서 실제로 받은 raw /health 기록
  ground_truth.md             사람이 있었는지에 대한 독립적인 장면 기록
  operator_notes.md           오류·중단·재연결·환경 메모
  checksums.sha256            파일이 이후 바뀌지 않았는지 확인하는 지문
```

현재 legacy utility가 자동으로 생성하는 파일명이나 팀 제출 양식이 따로 있으면 그 양식을 우선합니다. 중요한 것은 raw capture를 수정하지 않고, 실제 장면 기록과 오류 메모를 함께 보존하는 것입니다.

checksum을 만들 수 있는 환경에서는 파일을 닫은 뒤 실행합니다.

```bash
cd <session-directory>
shasum -a 256 capture.csv ground_truth.md operator_notes.md > checksums.sha256
```

### 정식 검증 실측

정식 도구가 활성화된 뒤에는 raw measurement JSONL, session manifest, ground-truth event log, failure/deviation log, operator notes와 checksums가 하나의 bundle로 보존됩니다. 이 단계에서는 담당자가 JSONL을 손으로 만들어내는 것이 아니라, 제공된 capture tool을 실행하고 실제 장면과 예외를 정확히 기록합니다.

## 8. 나중에 사용하는 정식 검증용 실측

> **현재 이 부분은 아직 실행하지 않습니다.**
>
> 팀 장치에서 새 SCD40 measurement event와 cached retransmission을 구분하는 기능이 배포되고, 실제 payload에서 확인되며, live readiness 검사가 통과한 뒤에만 이 모드를 엽니다.

정식 모드를 시작하려면 다음을 확인해야 합니다.

- producer fresh-event 정보가 team `main`에 반영되고 실제 장치에 배포됨
- event ID가 새 SCD40 읽기 성공 때만 증가함
- 같은 event ID가 반복되면 cached retransmission으로 보임
- 그 event와 연결된 measurement chronology가 보존됨
- protocol ID/version과 후보 ID가 session manifest에 남음
- 독립적인 VACANT/OCCUPIED ground truth를 기록할 수 있음
- raw bundle과 checksum을 닫은 뒤 검증할 수 있음

정식 도구가 release된 후의 실행 예시는 다음과 같습니다. 이 명령은 standalone repository의 capture tool 기준이며, 현재 exploratory 측정에서 임의로 실행하지 않습니다.

```bash
python3 scripts/capture_co2_c_c1t_session.py \
  --output-root <session-output-root> \
  --operator-id <operator-id> \
  --location-id <location-id> \
  --scenario-id VACANT_STABLE \
  --ground-truth VACANT \
  --ground-truth-source CONTROLLED_EMPTY_ROOM \
  --source-url http://<pi-host>:8080/health \
  --duration-sec 300 \
  --interval-sec 1
```

전환 세션은 도구가 지원하는 `--ground-truth-event LABEL@UTC_TIMESTAMP@SOURCE[@NOTE]` 형식으로 실제 입장·퇴장 사건을 별도로 기록합니다. 같은 event ID가 여러 packet에서 반복되면 여러 packet을 여러 physical measurement로 세지 않습니다.

정식 데이터를 모은다고 바로 Accuracy/F1을 계산하는 것도 아닙니다. 먼저 protocol compliance, freshness, chronology, raw immutability와 독립 ground truth를 확인하고, 별도 승인 후에야 실제 장치의 formal device-domain validation으로 넘어갑니다.

## 9. 절대 하지 말아야 할 것

- CO₂ 숫자를 보고 `VACANT`/`OCCUPIED`를 결정하지 않습니다.
- 모델 prediction이나 threshold crossing을 ground truth로 쓰지 않습니다.
- 누락된 값을 이전 값으로 채우지 않습니다.
- stale 값을 새 센서 측정처럼 복제하지 않습니다.
- 오류 row를 삭제하지 않습니다.
- raw CSV/JSONL을 Excel 등으로 열어 저장 덮어쓰기 하지 않습니다.
- 두 개의 물리적으로 분리된 session을 임의로 이어 붙이지 않습니다.
- 60초 간격을 맞추려고 가짜 sample이나 timestamp를 만들지 않습니다.
- ESP32에서 slope 계산이나 AI inference를 임의로 추가하지 않습니다.
- 수집 중 feature, scaler, threshold, model을 바꾸지 않습니다.

## 부록 A. 담당자가 자주 묻는 말

### “60초마다 제가 값을 적어야 하나요?”

아닙니다. capture utility가 실제로 받은 payload와 timestamp를 기록합니다. 60초는 AI가 입력을 내보낼 기회에 대한 계약이지, 담당자가 센서값을 수기로 만드는 주기가 아닙니다.

### “측정 시작 직후 slope가 없으면 앞의 row를 지워도 되나요?”

아닙니다. 약 150초 history가 쌓이기 전의 warm-up row도 보존합니다. 후처리에서 feature unavailable로 분류할 수 있지만 raw evidence는 삭제하지 않습니다.

### “사람이 있는데 CO₂가 낮으면 VACANT인가요?”

아닙니다. 실제로 사람이 있었다면 `OCCUPIED`입니다. 반대로 사람이 없는데 CO₂가 높게 남아 있어도 실제 장면이 비어 있었다면 `VACANT`입니다.

### “같은 CO₂ 값이 몇 번 반복되면 고장인가요?”

탐색 실측만으로는 바로 판단하지 않습니다. raw response, packet 상태와 시간을 보존하고 note를 남깁니다. 정식 모드에서는 event ID로 새 측정과 재전송을 구분합니다.

### “모델이 OCCUPIED를 내면 정답으로 기록하면 되나요?”

아닙니다. 모델 output은 관찰값이고, ground truth는 실제 사람이 있었는지에 대한 독립적인 기록입니다.

## 부록 B. 내부 기술 용어 대응표

현장에서는 아래 한국어 표현을 사용하고, 저장소의 manifest나 audit를 확인할 때만 영어 식별자를 참고합니다.

| 현장 표현 | 내부 추적 이름 |
|---|---|
| 1차 탐색 실측 | `PRE_DEPLOYMENT_EXPLORATORY_REAL_DEVICE_EVIDENCE` |
| 정식 검증용 실측 | `PROTOCOL_CONTROLLED_REAL_DEVICE_EVIDENCE` |
| 새 센서 event가 아직 증명되지 않음 | `UNVERIFIED_ALLOWED_AS_EXPLICIT_LIMITATION` |
| 정식 수집 대기 | `HOLD_PENDING_PRODUCER_DEPLOYMENT_AND_LIVE_C_C1T_VERIFICATION` |
| 최근 150초 endpoint difference | `ENDPOINT_H150` / `ENDPOINT_DIFFERENCE` |
| formal validation 이전 단계 | `C-C2 NOT_STARTED` |

전체 시스템 설명과 모델 사용 원칙은 [SafeNest CO₂ 인수인계 문서](../handoff/20260815_SafeNest_CO2_AI_and_Measurement_Handoff_KO_01.md)를 참고합니다.

## 문서 정보

- 문서 버전: `02`
- 작성일: `2026-08-16`
- 단계: `C-C1T — Human-First Physical Measurement Field Guide`
- 작성 에이전트: `Codex (CO2 Human-First Field Guide Documentation Agent)`
- 문서 상태: `EXPLORATORY_READY_FORMAL_HOLD`
