# CAP-6 착수 요청 — M-N10 측정 프로토콜 조회

발신: mmWave 센서 담당(물리 데이터 획득 트랙)
수신: mmWave 모델 개발 담당
일자: 2026-08-18
Team main 기준: 8e4c729 (PR #31 머지 시점)

---

## 요약

센서 트랙의 CAP-0~CAP-3 을 마쳤습니다. MR60 캡처 경로는 M-N4 계약을 충족하며,
2026-08-18 에 4개 세션(canonical window 29개, 폐기 0)을 확보했습니다.

다음 단계인 CAP-6(정식 측정)는 **M-N10 이 지목한 결손**을 채우는 작업인데,
착수 전에 확인이 필요한 항목이 있어 요청드립니다.

저희가 M-N10 에 대해 가진 정보는 아래 한 문장이 전부입니다.

> 현장에서 MR60+독립 호흡센서로 새 사람 최소 6명을 측정한 뒤 같은 PR에
> 두 번째 evidence commit 을 추가하면 된다.

M-N10 산출물은 Team main 과 열린 PR 어디에도 없어 내용을 확인하지 못했습니다.

---

## 1. 가장 먼저 필요한 답 — APNEA 를 어떻게 얻을 계획인가

`m_n4_canonical_input_dataset_contract.json` 의 클래스 정의는 다음과 같습니다.

```text
APNEA = "voluntary breath-hold overlap >= 6 s and event duration >= 8 s"
```

자발적 숨 참기를 전제합니다.

센서 트랙 지시는 숨 참기·무호흡 시뮬레이션을 담당자가 자율적으로 설계·수행하는 것을
금지하고 있으며, 수행하려면 참가자 안전 규칙을 포함한 별도 검토·승인이 필요합니다.

따라서 다음 중 어느 쪽인지 알려주십시오.

- (A) MR60 측정에서도 숨 참기를 수행해 APNEA 를 직접 확보한다
  → 참가자 안전 규칙·동의 절차를 포함한 프로토콜과 별도 승인이 필요합니다
- (B) APNEA 는 공개 110명 데이터로 충당하고, MR60 측정은 NORMAL/RAPID 만 다룬다
  → 센서 트랙이 현재 권한 범위에서 바로 진행할 수 있습니다
- (C) 그 외

이 답에 따라 CAP-6 착수 가능 여부 자체가 갈립니다.

---

## 2. M-N10 측정 프로토콜 문서 요청

"측정 규칙을 미리 잠갔다"고 들었습니다. 해당 문서(또는 규칙이 담긴 JSON/스크립트)를
공유해 주시면 저희 캡처 절차를 거기에 맞추겠습니다. 특히 아래 항목이 필요합니다.

| 항목 | 왜 필요한가 |
|---|---|
| 피험자당 세션 길이·횟수 | 현재 저희 기본값은 60 s 워밍업 후 4분(창 6~7개)입니다 |
| 측정 조건 목록 | 자연호흡만인지, 추가 조건이 있는지 |
| 레퍼런스 동기화 방법 | 시각 정렬 방법이 정해져야 라벨을 30 s 창에 붙일 수 있습니다 |
| 거리·자세·기하 규격 | 현재 저희는 앉은 자세, 장치 기준 52~57 cm 입니다 |
| 라벨 생성 주체와 규칙 | 누가 어느 시점에 라벨을 확정하는지 |
| 동의·개인정보 처리 절차 | 6명 대상이므로 사전 확정이 필요합니다 |

문서가 아직 없다면, 위 항목만 간단히 회신해 주셔도 착수 가능합니다.

---

## 3. 독립 레퍼런스 장비 사양 확인

M-N4 는 공개 데이터의 정답원을 `MOVESENSE_CHEST_ACC` 로 기록하고 있습니다.

- MR60 측정 쪽 레퍼런스도 **가슴 가속도계 계열**이어야 클래스 의미가 맞습니까?
- Movesense 가 아닌 대체 장비(예: ESP32+IMU 가슴 스트랩, 호흡 벨트)도 허용됩니까?
- 필요한 샘플링 레이트·저장 형식 요건이 있습니까?

센서 트랙은 이 태스크 범위에서 레퍼런스 장비를 임의 선정·구매하지 않습니다.
사양을 알려주시면 프로젝트 리드에게 구매/제작을 요청하겠습니다.

---

## 4. "새 사람 6명" 의 정의 확인

- `SUBJ-001`(기존 팀 측정 74건 및 2026-08-18 세션의 피험자)은 "새 사람"에 포함되지 않는 것으로
  이해하고 있습니다. 맞습니까?
- 레퍼런스 없이 먼저 측정한 피험자를, 나중에 레퍼런스를 달고 재측정하면 "새 사람"으로
  인정됩니까? (사람을 두 번 부르지 않으려면 순서를 정해야 합니다)
- 6명은 최소값입니까, 목표값입니까?

---

## 5. 참고 — 저희가 이미 확인해 드릴 수 있는 것

### 5.1 캡처 경로는 M-N4 계약을 충족합니다

`required_live_fields` 3개(`breath_phase`, `ts_monotonic_ms`, `phase_age_ms`) 전부 확보됩니다.
2026-08-18 세션 4건 기준:

```text
telemetry 10 Hz   accepted event rate 9.99 Hz
8 ms advancement 규칙으로 폐기된 행 0
phase_age_ms 최대 18 ms (kPhaseMaxAgeMs=500 에 근접조차 안 함)
0.4 s 초과 간격 0,  uart/checksum 오류 0,  seq 누락 0
canonical window 29개 생성, 폐기 0
```

`phase_update_seq` 는 펌웨어에 없지만, 파생 `ts_monotonic_ms - phase_age_ms` 가 텔레메트리 행과
1:1(rows_per_distinct_update = 1.000)이라 실질 손실이 없습니다. provenance 전용 펌웨어 패치는
실익이 없다고 판단해 제안하지 않았습니다.

### 5.2 재부팅은 phase 스케일을 바꾸지 않습니다

| 세션 | breath_phase 범위 | pstdev |
|---|---|---|
| CAP2-01 | −0.65 … +0.72 | 0.204 |
| CAP2-02 | −0.82 … +0.66 | 0.230 |
| REBOOT | −0.82 … +0.85 | 0.295 |

재부팅 후 값이 세션 간 자연 변동 범위 안에 있습니다(n=3 관찰).
`boot.window_may_cross_boot_or_restart: false` 는 타이밍 리셋 때문이지
스케일 변화 때문은 아닌 것으로 보입니다.

### 5.3 presence gate 근거를 장치 쪽에서 확보했습니다

M-N7 의 `NO_PERSON_INFERENCE_GATING_HAZARD` 를 빈 방 세션으로 재현했습니다.

```text
M-C0-20260818-CAP3-EMPTY-01 (240 s, 2400 records)

breath_phase      전부 정확히 0.0 (고유값 1종)
distance_cm_raw   전부 null
presence          전부 false
sensor_state      전부 UNKNOWN / PRESENCE_NOT_DETECTED  (예외 0건)

M-N4 창 8개 → 전부 채택, MAD=0, mad_collapsed=true
```

M-N4 는 빈 방 입력을 거르지 않고 zero tensor 를 그대로 내보냅니다.
반면 producer 의 presence 신호는 예외 없이 깨끗하므로, gate 구현에 바로 쓸 수 있습니다.

### 5.4 M-N4 에 진폭 게이트가 없다는 점

producer 가 `BREATH_PHASE_LOW_AMPLITUDE`(임계 `kBreathMinPhaseStd = 0.2`)로 표시한 구간도
M-N4 는 그대로 채택합니다. 저희 세션에서 저진폭 비율은 43 % / 29 % / 1 % 로 편차가 컸습니다.

거리가 51.7 cm 로 고정된 구간에서도 진폭만 내려갔다 회복하는 현상이 관찰돼,
기하 문제라기보다 호흡 깊이를 반영하는 것으로 보입니다.

세션·창 단위 `producer_non_valid_fraction` 을 산출해 두었으니,
학습에 쓰실 때 필요하시면 창 선별 기준으로 사용하실 수 있습니다.
(`tools/cap0_m_n4_feasibility.py` 로 재현 가능)

---

## 6. 현재 확보 자료

| Session | Subject | Condition | Duration | Windows | Use |
|---|---|---|---:|---:|---|
| M-C0-20260818-CAP2-S001-01 | SUBJ-001 | 자연호흡·정지 52 cm | 239.9 s | 7 | DEVICE_DOMAIN_REFERENCE |
| M-C0-20260818-CAP2-S001-02 | SUBJ-001 | 동일조건 반복 57 cm | 239.9 s | 7 | DEVICE_DOMAIN_REFERENCE |
| M-C0-20260818-CAP3-S001-REBOOT-01 | SUBJ-001 | ESP 재부팅 후 52 cm | 239.9 s | 7 | DEVICE_DOMAIN_REFERENCE |
| M-C0-20260818-CAP3-EMPTY-01 | SUBJ-NONE | 빈 방 | 240.0 s | 8 | FAILURE_QA_EVIDENCE |

전부 `validate_contract.py --check-files --strict-warnings` PASS.
독립 레퍼런스가 없으므로 supervised 학습 후보로 올리지 않았습니다.

상세: `reports/MR60_SENSOR_OWNER_ACQUISITION_ROADMAP.md`
