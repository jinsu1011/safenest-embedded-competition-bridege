# SafeNest CO₂ C-C1R SCD40 실측 운영 안내서

- 문서 버전: `02`
- 작성 에이전트: `Codex` (CO₂ C-C1T Acquisition Tooling Readiness Agent)
- 작성일: `2026-08-15`
- 단계: `C-C1R → C-C1T — Acquisition Tooling Readiness and Pre-Collection Compliance Gate`
- 문서 상태: `FORMAL_PROTOCOL_APPENDIX_HOLD_EXPLORATORY_HANDOFF_READY`
- C-C1R predecessor machine status: `HOLD_PENDING_ACQUISITION_TOOLING_CORRECTION`
- 프로토콜 ID: `CO2_C_C1R_REDUCED_MEASUREMENT_PROTOCOL_001`
- 프로토콜 버전: `1.0.0`

> 이 문서는 C-C1R의 **정식 protocol-controlled measurement appendix**입니다. 정식 실측은 producer fresh-event 배포와 live C-C1T 검증 전까지 보류합니다. 지금 가능한 1차 exploratory 실측은 [두 단계 통합 안내서](20260815_SafeNest_CO2_SCD40_Physical_Measurement_Guide_KO_01.md)의 Mode 1을 따르십시오. Exploratory evidence는 보존하지만 자동으로 C-C2 formal evidence가 되지 않습니다.

## 1. 이번 실측에서 필요한 AI 입력

```text
AI용 필수 센서값: CO2
AI용 필수 파생값: CO2_slope
온도: AI 필수값 아님
습도: AI 필수값 아님
CO2_slope: 운영자가 직접 계산하지 않음
```

새 후보 모델은 `CO2 + CO2_slope`만 사용합니다. 온도와 습도는 장치가 제공하면 별도 진단 정보로 보존할 수 있지만, 이 후보의 AI 검증 필수값은 아닙니다. 이는 온도·습도가 의미 없다는 뜻이 아닙니다.

`CO2_slope`는 SCD40이나 ESP32에서 계산하지 않습니다.

```text
SCD40 / ESP32
  → 새 CO2 측정 이벤트
  → 측정 freshness/시간 정보와 함께 전송
  → Raspberry Pi
  → Pi에서 ENDPOINT_H150 방식으로 CO2_slope 계산
```

## 2. 정식 protocol-controlled 측정을 지금 시작하지 않는 이유

현재 팀의 `devices/co2/firmware/capture_scd40.py`는 Pi `/health`를 주기적으로 읽어 CO₂ 값, transport 상태, host 시간, raw 응답을 저장합니다. 하지만 다음을 현재 경로만으로는 증명할 수 없습니다.

- 해당 값이 새 SCD40 측정 이벤트인지;
- 새 측정마다 증가하는 fresh-read sequence인지;
- 실제 센서 측정 이벤트와 연결된 chronology인지;
- frozen protocol/session/candidate ID인지;
- 독립적인 VACANT/OCCUPIED 시간표시 ground truth인지;
- 세션별 raw checksum bundle인지.

따라서 다음 조건이 충족되기 전까지는 **정식 protocol-controlled 측정**의
`PHYSICAL_ACQUISITION = HOLD`입니다. 이것은 pre-deployment exploratory
real-device collection까지 금지한다는 뜻은 아닙니다.

1. fresh CO₂ 이벤트 marker와 그 이벤트의 chronology를 제공하는 capture adapter가 준비될 것.
2. 프로토콜/세션/후보 ID와 실패·누락 상태를 저장할 것.
3. 독립 ground-truth 이벤트 파일과 최종 SHA-256 파일을 만들 수 있을 것.
4. C-C1R 사전검증기가 실제 배포 경로에 대해 PASS할 것.

이번 C-C1T에서는 팀 저장소의 AI/model/runtime를 변경하지 않고, SCD40 성공 읽기 event 관측성만 별도 팀 PR로 제안했습니다. 팀 PR은 이 작업에서 merge하지 않았습니다. PR #19가 검토·merge·배포되고 나면 동일한 capture contract와 precollection validator를 다시 실행해야 합니다.

standalone 도구의 dry-run은 실제 센서 검증이 아닙니다. 현재 formal
precollection 결과는 다음과 같습니다.

```text
C_C1T: BLOCKED
DRY_RUN_VALIDATION: PASS
TEAM_PRODUCER_OBSERVABILITY: IMPLEMENTED_ON_FEATURE_BRANCH_ONLY
TEAM_PR: #19 OPEN
FORMAL_PHYSICAL_ACQUISITION: HOLD
EXPLORATORY_PHYSICAL_ACQUISITION: ALLOWED
```

## 3. 연결과 시작 전 확인

사용할 장비는 팀이 선언한 SCD40–ESP32–Raspberry Pi 경로입니다. 배선과 장치 설정은 별도의 팀 wiring 문서와 승인된 capture adapter를 따릅니다. 현재 legacy capture script를 그대로 사용하면 안 됩니다.

시작 전에 운영 담당자와 capture 담당자는 다음을 함께 확인합니다.

- SCD40/ESP32/Pi의 장치 ID와 capture software/firmware/library 버전이 기록되어 있는가;
- 측정 mode와 SCD40 native 설정 간격이 기록되어 있는가;
- `CO2_C_C1R_REDUCED_MEASUREMENT_PROTOCOL_001` / `1.0.0`이 session manifest에 들어가는가;
- C-B6 후보 ID `C_B6_REDUCED_CO2_SLOPE_CANDIDATE_001`이 manifest에 들어가는가;
- 새 측정이 생길 때만 증가하는 `fresh_read_sequence` 또는 동등한 marker가 있는가;
- 센서 이벤트 시간과 Pi 수신 시간이 분리되어 있는가;
- 오류·누락 row를 저장할 수 있는가;
- 새 세션 디렉터리와 checksum 파일을 만들 수 있는가;
- ground-truth 이벤트를 센서값과 별도로 기록할 수 있는가.

하나라도 확인할 수 없으면 실측을 시작하지 말고 `OPERATOR_HANDOFF_BLOCKED_BY_ACQUISITION_TOOLING`으로 보고합니다.

### 3.1 정식 Mode 2 capture 도구와 사전검증 명령

팀 PR #19가 team `main`에 반영·배포되고, 아래 validator가 다시 통과하기
전에는 이 명령으로 **정식 bundle**을 수집하지 않습니다. 지금 가능한
exploratory 명령은 새 통합 안내서의 Mode 1에 있습니다.

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

이 도구가 생성하는 session ID와 bundle 파일은 수동으로 만들지 않습니다. `raw_measurements.jsonl`에는 원본 `/health` payload, packet sequence, Pi transport 상태, producer event ID/monotonic 시각을 함께 보존합니다. 동일한 producer event ID는 새 측정이 아니라 `CACHED_RETRANSMISSION`으로 분류됩니다.

사전검증은 dry-run bundle을 포함해 다음처럼 실행합니다.

```bash
python3 scripts/validate_co2_c_c1t_precollection.py \
  --bundle-dir datasets/co2/manifests/c_c1t_acquisition_tooling/fixtures/CO2C1R-20260815-CODEX-S001
```

현재 기대 결과는 `C_C1T_BLOCKED`와 `DRY_RUN_VALIDATION: PASS`입니다. 팀 PR merge/deploy 이후에만 `C_C1T_ACQUISITION_TOOLING_READY`로 바뀔 수 있습니다.

## 4. 60초 기록 규칙

정상적인 SafeNest 모델 입력/CO₂ export 기회는 **약 60초 간격**을 기준으로 합니다. 이것은 SCD40 native 측정 간격이 60초라는 뜻이 아닙니다.

계약상의 `effective_model_input_interval_sec`와 `normal_co2_export_interval_sec`는 `60`초로 고정되어 있습니다. capture 도구의 실제 polling interval은 raw event 관측을 위한 logger 설정이며, native SCD40 cadence나 60초 model-input/export 계약을 대체하지 않습니다.

각 60초 기회에:

- 새롭고 유효한 CO₂ 측정 이벤트가 확인되면 실제 값과 실제 시간을 저장합니다.
- 새 fresh CO₂가 확인되지 않으면 누락/실패 상태를 저장합니다.
- 이전 CO₂를 다시 쓰지 않습니다.
- 빈칸을 보간하거나 정상값으로 채우지 않습니다.
- 시간을 60초에 맞추도록 나중에 고치지 않습니다.

```text
STALE_REUSE = 금지
FORWARD_FILL = 금지
SYNTHETIC_FILL = 금지
```

새 packet, 새 logger row, `transport_fresh`, 최근 `age_seconds`, 숫자로 보이는 cached CO₂만으로는 새 SCD40 물리 측정이라고 판단하지 않습니다. `TRANSPORT_FRESHNESS`와 `SENSOR_MEASUREMENT_FRESHNESS`는 별도로 보존합니다.

## 5. CO2_slope와 warm-up

고정된 slope 계약은 다음과 같습니다.

```text
profile: CO2_SLOPE_FEATURE_PROFILE_001
method: ENDPOINT_H150
history: 150초
chronology: 과거값만 사용
minimum samples: 2
gap reset: 90초 초과
```

운영자는 slope를 직접 계산하지 않습니다. 첫 기록 직후, 또는 90초 초과 gap 뒤에는 slope가 아직 없을 수 있습니다. 이 warm-up/재시작 상태도 raw 기록으로 남깁니다.

예를 들어 정상 기록이 약 `60초 → 180초`로 이어지면 gap은 약 120초입니다. 90초를 넘으므로 H150 history를 초기화하고, 충분한 새 history가 쌓일 때까지 `CO2_slope unavailable` 상태로 둡니다. 중간 기록을 만들어 넣거나 오래된 값을 복사하지 않습니다.

## 6. 세션과 시나리오

세션마다 새 ID를 만들고 다른 세션의 slope history를 이어 붙이지 않습니다. 권장 형식은 다음과 같습니다.

```text
CO2C1R-YYYYMMDD-OPCODE-SNNN
```

허용 시나리오:

- `VACANT_STABLE`: 사람이 없는 상태를 독립적으로 확인
- `OCCUPIED_STABLE`: 사람이 있는 상태를 독립적으로 확인
- `VACANT_TO_OCCUPIED`: 사람 입장 전환을 시간표시
- `OCCUPIED_TO_VACANT`: 사람 퇴장 전환을 시간표시

각 stable 구간은 warm-up 뒤 최소 150초의 같은 세션 fresh chronology가 쌓이도록 합니다. 전환 세션은 가능하면 전환 전·후 각각 150초를 확보합니다. 전체 세션 수는 별도 승인된 수집 계획이 정하며, 이 안내서가 통계적 검정력을 보장한다고 해석하지 않습니다.

장치/수집기 재시작, 위치·설정 변경, 또는 90초 초과 chronology gap이 생기면 세션을 닫고 새 세션으로 시작합니다.

## 7. 독립 ground truth 기록

사람이 실제로 방에 있는지 여부를 별도 기록합니다.

```text
VACANT = 실제로 사람이 없는 시간 구간
OCCUPIED = 실제로 사람이 있는 시간 구간
```

ground-truth 파일에는 최소한 다음을 기록합니다.

- `ground_truth_event_id`
- `session_id`
- `VACANT` 또는 `OCCUPIED`
- 시작·종료 또는 전환 시각
- 기록자 ID
- `CONTROLLED_EMPTY_ROOM`, `CONTROLLED_PERSON_PRESENT`, `RECORDED_ENTRY`, `RECORDED_EXIT` 중 source
- 불확실/충돌 상태

다음으로 label을 정하지 않습니다.

- CO₂가 높아서 occupied라고 적기;
- CO₂_slope가 올라가서 occupied라고 적기;
- 모델 출력이나 threshold crossing을 보고 label을 바꾸기;
- `breath` 같은 파일명으로 자동 label 만들기;
- 모델이 약해 보이는 장면만 추가로 수집하기.

전환 중 애매한 구간은 애매한 상태로 남기고, 나중 C-C2가 정한 규칙에 따라 처리합니다.

## 8. raw 파일과 제출물

세션마다 별도 bundle을 만들고 기존 파일을 덮어쓰지 않습니다.

```text
raw_measurements.jsonl
session_manifest.json
ground_truth_events.jsonl
failure_events.jsonl
deviation_events.jsonl
checksums.sha256
operator_notes.md
```

raw row에는 가능한 범위에서 protocol/version, session ID, candidate ID, CO₂/ppm, sensor freshness/status, transport freshness/status, 실제 시간, monotonic 시간, raw payload, 장치·소프트웨어 설정 ID를 보존합니다. 온도·습도가 없다고 CO₂를 무효화하지 않지만, 현재 도구가 요구된 freshness/event evidence를 못 만들면 세션 전체를 protocol-compliant로 선언하지 않습니다.

센서 끊김, fresh 값 없음, transport error, missing sample, logger error가 발생해도 row나 failure event를 삭제하거나 정상값으로 덮어쓰지 않습니다. 실패한 세션도 제출물에 포함합니다.

capture를 끝낸 뒤 파일을 닫고 byte size/row count를 기록한 다음 SHA-256을 계산합니다. checksum 이후 raw 값을 수정하거나 timestamp/label을 고치면 안 됩니다.

## 9. 모델 결과 사용 금지

수집 중 모델 결과를 볼 필요가 없습니다. 도구에 모델 결과가 표시되더라도:

- ground truth를 바꾸지 않습니다.
- 시나리오와 시간을 바꾸지 않습니다.
- 약한 결과만 골라 추가 수집하지 않습니다.
- threshold, scaler, model, feature, H150을 바꾸지 않습니다.

이번 단계의 목적은 고정된 후보를 공정하게 검증할 수 있는 raw evidence를 모으는 것이지 모델을 현장에서 조정하는 것이 아닙니다.

## 10. C-B6 INT8 limitation

C-B6에서 `CO2_slope` INT8 input saturation이 낮은 빈도로 관측됐지만 Float/INT8 equivalence gate는 PASS였습니다. 현재 disposition은 다음과 같습니다.

```text
KNOWN_NONBLOCKING_LIMITATION_FOR_DEVICE_DOMAIN_OBSERVATION
```

이 문제를 이번 안내서에서 고친 것이 아닙니다. C-C2에서 실제 장치의 saturation/clipping rate와 prediction effect를 관찰해야 합니다. 운영자가 quantization range나 모델을 바꾸면 안 됩니다.

## 11. 현재 배포 상태

```text
프로토콜: FROZEN
운영자 handoff: HOLD_PENDING_TEAM_PRODUCER_OBSERVABILITY_PR_DEPLOYMENT
정식 실측 시작: NO
1차 exploratory 실측: ALLOWED
C-C2: NOT_STARTED
팀 producer 관측성 PR: #19 OPEN / merge·deploy 안 됨
```

팀 producer 변경의 merge/deploy와 C-C1T precollection validator PASS가
확인된 뒤에만 이 appendix를 정식 운영자에게 배포합니다. 현재 exploratory
운영자에게는 새 통합 안내서를 공유합니다. 그때도 별도 승인 없이 C-C2를
시작하지 않습니다.
