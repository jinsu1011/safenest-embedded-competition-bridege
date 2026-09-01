# M-C0 Capture Checklist

이 문서는 실제 측정 때 작성한다. 정상적인 자발 호흡 관찰만 수행하며, 숨 참기·과호흡·극단적 동작·밀폐/가스 환경을 시험 조건으로 사용하지 않는다.

## 시작 전

- [ ] **기하를 캡처 전에 줄자로 실측한다.** 캡처가 끝날 때까지 센서를 움직이거나
      기울기를 바꾸지 않는다. 2026-08-18 에 세션을 다 찍은 뒤 실측하면서 기울기를
      함께 바꿔, 그 4개 세션의 캡처 당시 각도를 확정할 수 없게 된 사례가 있다
- [ ] 실측 항목 세 가지: 바닥→안테나 면 높이 / 센서→가슴 직선거리 / 기울기.
      거리는 센서 앞면에서 복장뼈까지 곧게 잇는 사선으로 재고, 앉은 자세는 캡처 때와 같게 한다
- [ ] `distance_cm_raw` 는 5.74 cm 간격으로 양자화되어 있어 장치값의 해상도가 ±2.87 cm 다.
      세션 간 한 칸 차이를 실제 이동으로 해석하지 않는다

- [ ] `subject_id`와 `operator_id`는 이름이 아닌 pseudonym으로 정함
- [ ] MR60BHA2 model, device id, ESP firmware, sensor firmware, config hash를 기록함
- [ ] MR60BHA2 → ESP32 UART2 → USB serial 경로를 확인함
- [ ] 거리, 높이, 각도, 방향, 대상 자세, 의복/이불을 기록함
- [ ] 주변인 유무, 센서 시야 내 여부, 대략적 거리와 움직임을 기록함
- [ ] 영상·얼굴·이름을 수집하지 않음
- [ ] 독립 respiration reference의 종류와 동기화 여부를 기록함. 없으면 `none/not_collected`로 명시함

## 기록 중

- [ ] 정상 자발 호흡 상태를 관찰함
- [ ] raw JSONL을 수정·필터링·보간하지 않고 저장함
- [ ] serial timeout, packet error, presence loss, 주변 움직임을 시간과 함께 메모함
- [ ] reference가 있으면 센서 timestamp와 동기화함

## 종료 후

- [ ] raw 파일을 immutable 원본으로 보관함
- [ ] raw 파일 SHA-256, byte count, record count를 계산함
- [ ] `templates/session_manifest.planned.json`을 실제 값으로 채움
- [ ] `templates/environment_metadata.template.json`을 실제 값으로 채움
- [ ] `python3 validators/validate_contract.py --strict-warnings ...` 실행
- [ ] phase 단위·스케일을 확인하지 못했으면 `UNKNOWN`으로 남김
- [ ] `heart_verified`, `apnea_verified`, `deployment_ready`를 reference 없이 true로 바꾸지 않음

## CAP-2 / CAP-3 실행 조건 (2026-08-18 추가)

M-N4 계약(`MMWAVE_MR60_COMPAT_INPUT_DATASET_V1`)과 펌웨어 1.2.0 실측에서 나온 조건이다.

- [ ] 대상이 자리를 잡은 뒤 **60 초 이상** 기다린 다음 기록을 시작한다
      (`kWarmupMs = 60000`; 그 전 구간은 `TARGET_WARMUP` 이라 상태 판정이 무의미하다)
- [ ] 세션 길이는 `60 s + N × 30 s` 로 잡는다. 기본값 **4 분 = 창 6개**
- [ ] 거리는 `kDistanceMinCm 40` / `kDistanceMaxCm 150` 안에 둔다.
      PR18 파일럿의 45.9 cm 는 하단이며 `BREATH_PHASE_LOW_AMPLITUDE` 가 지배적이었다.
      CAP-3 기하 변형은 **80–100 cm** 를 우선 시도한다
- [ ] 기록 중 `sensor_state` / `error_code` 를 눈으로 확인한다.
      `BREATH_PHASE_LOW_AMPLITUDE` 가 계속 뜨면 `breath_phase_std` 가
      `kBreathMinPhaseStd = 0.2` 아래라는 뜻이다. 세션을 버리지 말고 **그대로 보존**한 뒤
      조건을 바꾼 재시도를 별도 세션으로 추가한다
- [ ] 0.4 s 이상 끊김이 생기면 해당 30 s 창 전체가 M-N4 에서 폐기된다.
      USB 케이블·터미널 스크롤·절전을 건드리지 않는다
- [ ] 종료 후 `python3 tools/cap0_m_n4_feasibility.py <raw.jsonl>` 을 실행하고
      `windows_accepted`, `windows_rejected`, `producer_non_valid_fraction` 을 세션 노트에 남긴다
- [ ] CAP-3 재부팅 세션은 재부팅 **전/후를 각각 별도 세션 ID** 로 기록한다
      (M-N4 `boot.window_may_cross_boot_or_restart: false`)

## M-N10 조건 (나중 정식 측정 · 지금 수행하지 않음)

`m_n10_capture_protocol_lock.json` (`LOCKED_BEFORE_HUMAN_CAPTURE`) 기준.
팀 PR #32 에서 전문을 읽을 것. 지금은 6명 모집·레퍼런스 구매·숨 참기를 하지 않는다.

- [ ] 조건 A 편안한 정지 호흡 — 사용 가능 구간 120초 이상
- [ ] 조건 B 빠른 호흡 또는 짧은 가벼운 움직임 후 회복 — 120초 이상.
      **큐는 정답이 아니다**
- [ ] 조건 C 자리를 옮기거나 기하를 리셋한 뒤 최소 한 조건 반복 — 120초 이상
- [ ] 조건 이름을 클래스로 매핑하지 않는다 (`intent_is_not_label: true`)
- [ ] 숨 참기를 강제하지 않는다. 짧은 pause 는 별도 안전 승인 + 독립 레퍼런스 확인이 있을 때만
- [ ] `subject_id` 는 `MN10-S001` 체계를 쓴다. `SUBJ-001` 은 새 피험자가 아니다
- [ ] `session_id` / `trial_id` / `boot_id` / `condition_intent` /
      `actual_reference_availability` 를 manifest 에 채운다
- [ ] 레퍼런스는 near-raw 파형 + 타임스탬프여야 한다. **BPM 전용 장비는 안 된다**
- [ ] 시계 동기는 같은 호스트 공통 시계가 1순위. 눈대중 정렬 금지.
      미검증이면 `AVAILABLE_ALIGNMENT_UNVERIFIED` 로 기록한다
- [ ] Pi 를 로거로 쓸 경우, 인간 측정 전에 M-N9 isolated smoke 를 먼저 통과시킨다
