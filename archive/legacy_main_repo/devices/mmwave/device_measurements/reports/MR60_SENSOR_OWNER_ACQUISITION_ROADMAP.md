# MR60 SENSOR-OWNER ACQUISITION ROADMAP (MR60-CAP)

작성일: 2026-08-18 (CAP-2/CAP-3 실측 반영)
상태: CAP-0/1/2/3 완료 · CAP-5 부분 · **CAP-6 DEFERRED**(모델 트랙 결정, 2026-08-18)
범위: 센서 담당자(물리 데이터 획득) 트랙 전용.
이 문서는 canonical 모델 로드맵이 아니다. Phase A/B/M-C/M-D/M-N ID 를 재사용하지 않는다.

---

## 0. 이 로드맵이 종속되는 상위 계약

모델 트랙은 이미 입력 계약을 **동결**했다.

- `RaspberryPi/Ondevice_AI/config/mmwave/m_n4_canonical_input_dataset_contract.json`
- `contract_id: MMWAVE_MR60_COMPAT_INPUT_DATASET_V1`, `status: FROZEN_FOR_M_N5`
- 실행 구현: `RaspberryPi/Ondevice_AI/scripts/mmwave_m_n4_canonical.py`

센서 트랙에 직접 걸리는 조항:

| 항목 | M-N4 계약 값 | 센서 트랙 의미 |
|---|---|---|
| `source_mr60.required_live_fields` | `breath_phase`, `ts_monotonic_ms`, `phase_age_ms` | 이 3개만 있으면 캡처는 계약 충족 |
| `timing.phase_update_estimate_ms` | `ts_monotonic_ms - phase_age_ms` | 파생 provenance 를 계약이 **공식 채택**함 |
| `timing.update_advancement_tolerance_ms` | 8.0 (마지막 **채택** 이벤트 기준) | 8 ms 이내 재게시는 폐기 |
| `gap` | 채택 간격이 `max(0.40 s, 4 × median)` 초과 시 창 전체 폐기 | 캡처 중 0.4 s 이상 끊김 금지 |
| `resampling` | 30 s 창, 8 Hz, 240 샘플, `[1,240,1]` | 세션 길이는 30 s 배수로 계획 |
| `team_mr60.supervised_training` | `DISALLOWED` (`physical_subjects: 1`) | 지금 우리 데이터는 학습 금지 상태 |
| `target.independent_reference_source` | `MOVESENSE_CHEST_ACC` | 프로젝트의 독립 reference 표준이 이미 정해져 있음 |

즉 **§37 Case B 의 `phase_update_seq` 부재는 모델 계약상 결함이 아니다.** 계약이 파생식을
정식 경로로 지정했다. 세션 분류는 `TEMPORAL_PROVENANCE_LIMITED` 대신
`TEMPORAL_PROVENANCE_DERIVED_CONTRACT_CONFORMING` 으로 둔다.

---

## 1. CAP-0 결과 — 캡처 스택 실측 (센서 없이 완료)

기존 PR18 파일럿 raw JSONL 2건을 **동결된 M-N4 로직에 그대로 통과**시켜 측정했다.
도구: `tools/cap0_m_n4_feasibility.py` (신규, read-only).

```bash
python3 tools/cap0_m_n4_feasibility.py pilot/M-C0-PILOT-STATIONARY-001.raw.jsonl
```

### 1.1 Capture readiness matrix

| 필드 | 상태 | 근거 |
|---|---|---|
| `breath_phase` | AVAILABLE (1799/1799, 전부 유한) | 파일럿 실측 |
| `ts_monotonic_ms` | AVAILABLE, 비감소 | 실측 |
| `seq` | AVAILABLE, 엄격 증가, gap 0 | 실측 |
| `phase_age_ms` | AVAILABLE (median 12 ms, p95 15 ms) | 실측 |
| `phase_update_ms` | **DERIVABLE**, M-N4 가 정식 채택 | 계약 |
| `phase_update_seq` | NOT_AVAILABLE | 계약상 불필요 (아래 1.3) |
| `presence` / `distance_cm_raw` | AVAILABLE | 실측 |
| `breath_rate_raw` | AVAILABLE (진단 전용, `breath_rate_raw_trusted: false`) | 실측 |
| `sensor_state` / `error_code` | AVAILABLE | 실측 |
| `firmware_version` / `config_hash` | AVAILABLE, 세션 내 단일값 | 실측 |

`firmware_version = safenest-mr60-esp/1.2.0`,
`config_hash = b817e8bf…c987834` — 사전 검증값과 일치.
원복 바이너리 `firmware_mr60_v1.2.0.bin` SHA-256 `3a80040e…7707cb` 도 실물 대조 일치.

### 1.2 M-N4 창 수율 — 실측

| 세션 | 길이 | 채택 이벤트 | 8 ms 규칙 폐기 | 0.4 s 초과 간격 | 30 s 창 채택 | 창 폐기 |
|---|---:|---:|---:|---:|---:|---:|
| STATIONARY-001 | 179.9 s | 1799 (9.999 Hz) | 0 | 0 | **5 / 5** | 0 |
| DESKWORK-001 | 179.9 s | 1798 (9.994 Hz) | 1 | 0 | **5 / 5** | 0 |

→ **3 분 세션 = 정확히 M-N4 창 5개.** 캡처 계획의 환산식:
`필요 창 수 N → 세션 길이 ≥ 60 s(warmup) + N × 30 s`.

### 1.3 phase_update_seq 부재의 실제 비용 ≈ 0

`rows_per_distinct_update_estimate = 1.000 / 1.001`.
파생 `phase_update_ms` 가 텔레메트리 행과 거의 1:1 이고, 8 ms 규칙이 폐기한 행은
3598 행 중 **1 행**뿐이다. `phase_age_ms` max 는 정지 세션에서 17 ms 로,
`kPhaseMaxAgeMs = 500` 에 한 번도 근접하지 않았다.
따라서 provenance 전용 펌웨어 패치의 실익은 현재 측정 근거상 미미하다 → **제안 보류**
(§11 절차는 유지하되, 실측이 필요성을 지지하지 않으므로 지금 올리지 않는다).

### 1.4 발견된 실제 문제 2건

**(a) LOW_AMPLITUDE 가 M-N4 를 그냥 통과한다 — 최우선 이슈**

| 세션 | `sensor_state != VALID` | error_code |
|---|---:|---|
| STATIONARY-001 | 87 % (1568/1799) | `BREATH_PHASE_LOW_AMPLITUDE` |
| DESKWORK-001 | 53 % (961/1799) | `BREATH_PHASE_LOW_AMPLITUDE` |

원인: `ESP32/reference/mmwave_platformio/include/mmwave_config.h`
`kBreathMinPhaseStd = 0.2F`, 30 s 창 표준편차가 그 아래면 DEGRADED
(`src/main.cpp:290`). 파일럿의 `breath_phase_std` 중앙값은 0.15–0.19 로 임계 바로 아래에서
계속 진동했다.

그런데 **M-N4 계약에는 진폭 게이트가 없다.** freshness/gap/MAD-epsilon 만 본다.
실제로 위 10개 창은 producer 가 DEGRADED 로 표시한 비율이 84–100 % 인데도 **전부 채택**됐고
MAD collapse 도 0건이었다. 즉 지금 방식대로 더 찍으면, 저진폭 데이터가 아무 표시 없이
학습 데이터에 들어간다.

→ 대응: (1) 창 단위 `producer_non_valid_fraction` 을 핸드오프에 **필수 동봉**한다
(도구가 이미 산출), (2) CAP-3 에서 진폭이 회복되는 거리/자세를 찾는다.
파일럿 거리는 45.9 cm 로 펌웨어 유효범위 `kDistanceMinCm = 40` 의 하단이었다.

**(b) USB serial 바이트 유실로 손상된 레코드 1건**

`pilot/M-C0-PILOT-STATIONARY-001.raw.jsonl:1030` 에서 인접 키가 융합된
`"breath_filtered_v_std"` 가 관측됨 (`breath_filtered_valid` + `breath_phase_std` 가
바이트 유실로 붙음). JSON 은 정상 파싱되므로 파싱 기반 QA 로는 잡히지 않는다.
빈도 1/3598.

→ **해소됨.** `tools/physical_capture_qa.py` 에 `schema_conformance` 검사를 추가했다
(qa schema 1.2). 스키마가 `additionalProperties: true` 이고 현재 펌웨어가 미선언 필드를
12개 내보내므로, 키 이름이 아니라 **키 빈도**로 판정한다. 모든 레코드에 있는 미선언 키는
정보성이고, 일부 레코드에만 있는 키만 실패로 처리한다. 손상 행 위치는 캡처의 최빈 키 조합과
비교해 찾는다. STATIONARY 파일럿에서 1030 행을 지목하고 DESKWORK 파일럿과 2026-08-18 세션
4건은 통과한다. 파일럿 QA 산출물도 1.2 로 재생성했다(raw 파일은 불변).
참고: `M-C0-PILOT-STATIONARY-001` 에는 session manifest 가 없어 이 손상을 설명할 실험
기록지가 원래부터 없었다.

### 1.5 §33 로컬 전용 미커밋 데이터

사전 조사 완료: **미반영 측정 데이터 0건.** 보고할 것 없음.

---

## 2. CAP-1 — 캡처 계약 (센서 없이 완료)

기존 스키마를 그대로 재사용한다. 새 디렉터리·새 매니페스트 스키마·새 검증기를 만들지 않는다
(§13, §29).

- `schemas/session_manifest.schema.json`, `schemas/raw_record.schema.json`
- `protocols/mc0_measurement_contract.json`
- `templates/session_manifest.planned.json`, `templates/environment_metadata.template.json`
- `tools/live_mr60_monitor.py` (raw JSONL 캡처), `tools/physical_capture_qa.py`
- `validators/validate_contract.py`

CAP-1 에서 추가한 것은 두 가지뿐이다.

1. `tools/cap0_m_n4_feasibility.py` — 세션이 M-N4 창을 몇 개 산출하는지 확인 (재사용)
2. `templates/capture_checklist.md` 의 **CAP-2/3 실행 조건** 절 (warmup·거리·길이·진폭)

subject ID 는 기존 규약 `SUBJ-PSEUDONYM-NNN` 를 유지한다. 사람과 세션은 별개이며,
한 사람의 인접 녹화가 서로 다른 ID 로 TRAIN/TEST 에 갈라지지 않게 한다.

---

## 3. CAP-2 / CAP-3 실측 결과 (2026-08-18 완료)

센서 연결 후 4개 세션을 기록했다. 전부 `validate_contract.py --check-files --strict-warnings` PASS.

### 3.1 세션 인벤토리 (§34)

| Session | Subject | Condition | Duration | Core phase | Freshness | Reference | Main limitation | Recommended use |
|---|---|---|---:|---|---|---|---|---|
| M-C0-20260818-CAP2-S001-01 | SUBJ-001 | 자연호흡·정지·앉음 52cm | 239.9 s | OK | DERIVED | none | 저진폭 43% | DEVICE_DOMAIN_REFERENCE |
| M-C0-20260818-CAP2-S001-02 | SUBJ-001 | 동일조건 반복 57cm | 239.9 s | OK | DERIVED | none | 저진폭 29% | DEVICE_DOMAIN_REFERENCE |
| M-C0-20260818-CAP3-S001-REBOOT-01 | SUBJ-001 | ESP 재부팅 후 52cm | 239.9 s | OK | DERIVED | none | 피험자 1명 | DEVICE_DOMAIN_REFERENCE |
| M-C0-20260818-CAP3-EMPTY-01 | SUBJ-NONE | 빈 방 | 240.0 s | 전부 0.0 | DERIVED | n/a | 호흡신호 없음(의도적) | FAILURE_QA_EVIDENCE |

총 canonical window 29개, 폐기 0. raw JSONL 은 기존 `raw/` ignore 정책에 따라 로컬 보관.

### 3.2 M-N4 수율

| 세션 | 창 | 폐기 | republication | phase_age max | 저진폭 |
|---|---:|---:|---:|---:|---:|
| CAP2-01 | 7 | 0 | 0 | 18 ms | 43 % |
| CAP2-02 | 7 | 0 | 0 | 18 ms | 29 % |
| REBOOT | 7 | 0 | 0 | 18 ms | 1 % |
| EMPTY | 8 | 0 | 0 | — | n/a |

네 세션 모두 10 Hz, 0.5 s 초과 끊김 0, uart/checksum 오류 0, seq 누락 0.

### 3.3 답이 나온 질문

**재부팅은 phase 스케일을 바꾸지 않는다.**

| 세션 | breath_phase 범위 | pstdev |
|---|---|---|
| CAP2-01 | −0.65 … +0.72 | 0.204 |
| CAP2-02 | −0.82 … +0.66 | 0.230 |
| REBOOT | −0.82 … +0.85 | 0.295 |

재부팅 후 값이 세션 간 자연 변동 범위 안에 있다. M-N4 의 `boot.window_may_cross_boot_or_restart: false` 는
타이밍(`ts_monotonic_ms` 리셋) 때문이지 스케일 변화 때문이 아니다. n=3 관찰이며 통계적 주장이 아니다.

**저진폭은 거리 문제가 아니다.** CAP-0 에서 세운 "파일럿 저진폭은 46 cm 때문"이라는 가설은 기각됐다.
파일럿과 같은 45.9/51.7 cm 에서 저진폭이 1 %까지 내려간 세션이 나왔고, CAP2-01 은 거리가 51.7 cm 로
고정된 상태에서 90–180 s 구간만 진폭이 내려갔다 회복했다. 호흡 깊이를 반영하는 신호로 본다.
→ 거리 특성화(CAP-3 잔여)의 우선순위를 낮춘다.

### 3.4 빈 방 세션 — presence gate 근거

모델 트랙 M-N7 의 `NO_PERSON_INFERENCE_GATING_HAZARD` 를 장치 쪽에서 재현했다.

```text
breath_phase      2400행 전부 정확히 0.0 (고유값 1종)
distance_cm_raw   2400행 전부 null
presence          2400행 전부 false
sensor_state      2400행 전부 UNKNOWN / PRESENCE_NOT_DETECTED

M-N4 창 8개 → 전부 채택, MAD=0, mad_collapsed=true (zero tensor)
```

**빈 방에서는 phase 갱신 자체가 느려진다. 점유 세션 3건은 8 ms 규칙으로 폐기된 행이 0 이고
`phase_age_ms` 최대 18 ms 인 반면, 빈 방 세션은 2400 행 중 330 행이 재게시로 폐기되고
(`phase_age_ms` 최대 114 ms) 실질 갱신률이 약 8.6 Hz 로 내려간다. 창 판정에는 영향이
없었지만(8개 전부 채택) presence gate 의 보조 신호로 쓸 수 있는 특성이다.

M-N4 는 빈 방을 거르지 않는다.** 계약의 `near_zero_behavior: ZERO_TENSOR` 대로 zero tensor 를 내보내고,
모델은 그것을 APNEA 로 읽는다. 이를 막을 수 있는 것은 presence gate 뿐이다.

다만 gate 가 쓸 producer 신호는 예외 0건으로 깨끗하다. Pi 런타임 담당자에게 그대로 넘길 수 있다.

---

## 4. CAP-5 핸드오프

모델 트랙이 소비할 것:

- raw: `raw/M-C0-20260818-*.jsonl` (로컬, SHA-256 은 각 manifest 의 `files.raw_jsonl`)
- manifest: `manifests/M-C0-20260818-*.session_manifest.json`
- QA: `qa/M-C0-20260818-*.qa.json`
- 창 수율/품질 재현: `python3 tools/cap0_m_n4_feasibility.py <raw.jsonl>`

세션당 반드시 함께 읽어야 하는 값은 `producer_non_valid_fraction` 이다.
M-N4 에 진폭 게이트가 없으므로, 저진폭 창을 구분하려면 이 값을 봐야 한다.

주의 두 가지가 각 manifest 노트에 기록돼 있다.

1. `distance_cm` 은 **장치 파생값**(`distance_cm_raw` 중앙값)이다. 줄자 실측이 아니므로
   운영자가 실측을 적은 `M-C0-PILOT-*` 의 값과 같은 성격으로 비교하면 안 된다.
2. `sensor_angle_deg = 100` 은 이번 세션들의 **운영자 기준**(책상면 기준, 90 = 책상에 수직)이다.
   `M-C0-PILOT-*` 의 `0`(가슴과 수평 정렬)과 다른 관례이므로 숫자를 직접 비교하면 안 된다.

---

## 5. CAP-6 — DEFERRED (2026-08-18 모델 트랙 결정)

`reports/MR60_CAP6_PROTOCOL_REQUEST.md` 에 대한 회신으로 CAP-6 의 상태가 **차단에서 연기로** 바뀌었다.

```text
Six new people are NOT required to build or integrate the system.
Six is only the later M-N11 scoring floor.
Immediate priority = sensor integration + end-to-end system.
CAP-6 / M-N10 multi-subject capture is DEFERRED.
```

즉 앞서 정리한 차단 3가지는 해소된 것이 아니라 **일정에서 뒤로 밀렸다.**
센서 트랙은 6명 모집을 시작하지 않는다.

### 5.1 질문별 회신

| 질문 | 회신 |
|---|---|
| APNEA 확보 방법 | **(C)** — 숨 참기 없음. 공개 110명 데이터의 APNEA proxy 사용. 빈 방은 presence gate 이지 APNEA GT 가 아님. 통합은 APNEA 캡처에 막히지 않음 |
| M-N10 프로토콜 문서 | 팀 PR #32 (`docs/mmwave-m-n10-protocol-share`). 상태 `CAPTURE_NOT_PERFORMED`, "나중 시험지이지 이번 주 SOP 아님" |
| 레퍼런스 장비 | M-N10 시작 시에만 필요. Movesense 우선, 벨트/흉부움직임/독립 타임스탬프 파형 허용. **BPM 전용 금지.** 자체 구매 금지 |
| "새 사람 6명" | `SUBJ-001` 은 새 사람 아님. 한 몸 = 한 명. 6 = 나중 하한, 8 = 나중 목표. 둘 다 이번 주 일이 아님 |
| CAP-0~3 | 통합 근거로 수용. presence 신호를 gate 로 배선 예정. **M-N4 에 진폭 게이트 추가하지 않음.** 4개 세션은 `DEVICE_DOMAIN_REFERENCE` / `FAILURE_QA_EVIDENCE` 유지 |

`phase_update_seq` 펌웨어 패치 미제안 판단도 그대로 유지됐다.
M-N11 과 `DEVICE_VALIDATED` 는 승인되지 않았다. APNEA 는 SafeNest proxy 이며 임상 판정이 아니다.

### 5.2 M-N10 규격 대조 — 지금 맞는 것과 안 맞는 것

`config/mmwave/m_n10_capture_protocol_lock.json` (`MMWAVE_M_N10_CAPTURE_PROTOCOL_V1`,
`LOCKED_BEFORE_HUMAN_CAPTURE`) 기준.

**이미 맞는 것**

| 항목 | M-N10 요구 | 현재 |
|---|---|---|
| 조건당 사용 가능 구간 | ≥ 120 s | 4분 세션 = 여유 |
| MR60 필수 필드 7개 | breath_phase, ts_monotonic_ms, phase_age_ms, seq, human_detected_raw, firmware_version, device_id | 전부 있음 |
| 창 경계 | subject/session/boot/large_gap 를 넘지 못함 | 재부팅을 별도 session_id 로 분리해 둠 |
| 기하 | "not a frozen law", 기록만 | 52–57 cm 기록됨 |

**안 맞아서 이번에 채운 것**

`session_identity_required` 6개 중 4개가 없었다. 스키마 최상위가 `additionalProperties: false`
였으므로 값을 넣을 수조차 없었다. 다음을 **optional** 로 추가해 기존 manifest 호환을 유지했다.

```text
schemas/session_manifest.schema.json
  + trial_id                              (top level, optional)
  + boot_id                               (top level, optional)
  + condition.condition_intent
  + reference.actual_reference_availability
      NOT_AVAILABLE / AVAILABLE_ALIGNMENT_VERIFIED /
      AVAILABLE_ALIGNMENT_UNVERIFIED / NOT_APPLICABLE
```

2026-08-18 세션 4건에 값을 채웠다. `boot_id` 는 펌웨어가 내보내지 않으므로 **파생값**이다.
`ts_monotonic_ms` 가 직전 캡처 대비 역행하면 새 boot 로 본다.

| 세션 | trial_id | boot_id | uptime |
|---|---|---|---|
| CAP2-S001-01 | T1 | BOOT-20260818-A | 635 → 875 s |
| CAP2-S001-02 | T2 | BOOT-20260818-A | 1464 → 1704 s |
| CAP3-S001-REBOOT-01 | T1 | BOOT-20260818-B | 959 → 1199 s |
| CAP3-EMPTY-01 | T1 | BOOT-20260818-B | 1317 → 1557 s |

**미해결 — 모델 트랙 확인 필요**

`boot_id`, `session_id`, `subject_id`, `trial_id` 가 `required_mr60_fields`(레코드 단위)와
`session_identity_required`(세션 단위) 양쪽에 들어 있다. 레코드에 주입하면 raw immutable 원칙을
깨므로 **세션 단위로 해석해 manifest 에 넣었다.** 이 해석이 맞는지 확인이 필요하다.

**아직 대응하지 않은 것 (M-N10 착수 시점 사안)**

```text
subject id 체계    현재 SUBJ-001 / M-N10 은 MN10-S001 (previous_team_subject_reused=false)
조건 A/B/C         프로토콜은 정의됐으나 우리 체크리스트에는 미반영 → 아래 6장
레퍼런스 필드 9개   장비가 없어 해당 없음
시계 동기          장비가 없어 해당 없음
피험자 배분        1/3 DEV, 2/3 RESERVED (N>=6 이면 RESERVED>=4), seed 20260818
Pi preflight       Pi 를 로거로 쓰면 인간 측정 전 M-N9 isolated smoke 필수. 현재 NOT_PERFORMED
```

### 5.3 M-N10 중에는 추론이 금지된다

```json
"float_inference_allowed_in_m_n10": false,
"int8_inference_allowed_in_m_n10": false,
"prediction_inspection_allowed_in_m_n10": false,
"reserved_model_inference_count": 0
```

M-N10 측정 작업 자체는 센서 트랙의 §45 경계(TFLite scoring 금지)와 충돌하지 않는다.
다만 **이번 주 통합 작업**(M-N9 INT8 실행 → UI/DB)은 별개이며, 그 주체가 센서 트랙이라면
§45 예외 승인이 필요하다. 이 건은 미해결로 둔다.

---

## 6. 나중 M-N10 측정 조건 (지금 수행하지 않음)

`capture_conditions` 잠금 내용. 체크리스트에도 같은 내용을 넣어 두었다.

| 조건 | 의도 | 최소 사용 구간 |
|---|---|---|
| A quiet rest | 정지, 편안한 자세 | 120 s |
| B elevated | 유도된 빠른 호흡 **또는** 짧은 가벼운 움직임 후 회복 | 120 s |
| C repeat after reposition | 피험자가 나갔다 오거나 기하 리셋 후 최소 한 조건 반복 | 120 s |

`intent_is_not_label: true` — 조건 이름을 클래스로 매핑하면 안 된다. B 의 큐도 정답이 아니다.

숨 참기는 강제 금지다. 선택적 짧은 pause 는 앉은 정지 자세, 불편 시 즉시 중단,
독립 레퍼런스 확인 필수이며 **별도 안전 승인**이 있어야 한다.

레퍼런스 정답으로 금지된 것: MR60 `breath_rate_raw`, 벤더 추정치, paced cue 단독,
`human_detected_raw`, 모델 예측.

시계 동기는 같은 호스트 공통 시계가 1순위이고, 아니면 양쪽 타임라인에 명시적 sync marker 를
남겨야 한다. 눈대중 정렬은 금지이며, 미검증 세션은 `REFERENCE_ALIGNMENT_UNVERIFIED` 로
분류되어 M-N11 채점에서 제외된다.

---

## 7. presence gate 근거 (통합 담당 인계용)

`M-C0-20260818-CAP3-EMPTY-01` 에서 gate 입력으로 쓸 신호는 예외 0건이다.

```text
2400 records, 240 s, 사람 없음

human_detected_stable   false        2400 / 2400
sensor_state            UNKNOWN      2400 / 2400
error_code              PRESENCE_NOT_DETECTED  2400 / 2400
distance_cm_raw         null         2400 / 2400
breath_phase            정확히 0.0   고유값 1종
```

점유 세션 3건과의 차이:

| | 점유 3건 | 빈 방 |
|---|---:|---:|
| 8 ms 규칙 폐기 | 0 | 330 / 2400 |
| `phase_age_ms` 최대 | 18 ms | 114 ms |
| 실질 갱신률 | 10.0 Hz | 약 8.6 Hz |

M-N4 는 빈 방 입력을 거르지 않고 zero tensor(MAD=0, `mad_collapsed=true`) 8개를 그대로
내보낸다. 이를 막는 것은 presence gate 뿐이다.

---

## 7.5 캡처 경로와 라이브 경로는 서로 다른 경로다 (2026-08-18 정정)

모델 트랙 회신에서 두 경로가 한 번 섞여 서술됐고, 이후 정정됐다. 혼동하기 쉬우므로 기록한다.

| | 캡처/레퍼런스 경로 (센서 트랙) | 라이브 프로덕션 경로 |
|---|---|---|
| 전송 | **USB serial** | SafeNest TCP v1 :9000 |
| 펌웨어 | `ESP32/reference/mmwave_platformio` (`safenest-mr60-esp/1.2.0`) | `ESP32/Arduino/esp32_sensor_node` |
| JSON | 평평(flat) | 중첩 예정 (`mmwave.{...}`, PR #29 DRAFT) |
| `breath_phase`/`ts_monotonic_ms`/`phase_age_ms`/`seq` | 있음 | 없음 (PR #29 에서 중첩으로 추가 예정) |
| `human_detected_raw` | **있음** | 없음. **PR #29 에도 없음** |
| CODEOWNERS | `@jinsu1011` | `/ESP32/` → `@yuseungha @jinsu1011` |

CAP-0~3 은 전부 USB 경로 증거다.

확정된 사항:

- **PR #29(DRAFT) 머지는 선행 조건이 아니다.** 기다리지도, 머지하지도 않는다.
  하드웨어 컴파일/플래시/라이브 캡처 증거가 없는 DRAFT 이며 `ESP32/` 소유자 영역이다.
- **`human_detected_raw` 를 Arduino TCP JSON 에 추가하지 않는다.**
  ESP32 소유자의 펌웨어/스키마 변경이며 "펌웨어 변경 금지" 지시와 충돌한다.
  모델 트랙이 앞서 요청했던 이 항목은 **철회됐다.**
- presence gate 는 USB JSONL 에 이미 있는 boolean(`human_detected_raw` /
  `human_detected_stable`)을 그대로 소비한다. **숫자 점유 임계값을 새로 만들지 않는다.**
- USB 를 프로덕션 경로로 슬쩍 대체하지 않는다. USB 는 캡처/레퍼런스 경로다.
- 라이브 TCP 를 붙이는 작업은 **integration 디코더 쪽 일**이며 센서 트랙 펌웨어 일이 아니다.

통합 측 USB 어댑터는 이미 존재하고 필요한 필드를 읽는다
(`archive/integration_source_snapshots/devices/mmwave/src/mr60_esp_adapter.py`):
`human_detected_stable` 우선, 없으면 `human_detected_raw` 로 presence 를 잡고
(`:193`), presence 가 아니면 추정기를 `MMWAVE_PRESENCE_NOT_DETECTED` 로 리셋한다(`:243`).

## 7.6 `distance_cm_raw` 는 5.74 cm 로 양자화되어 있다

전 캡처(2026-08-18 세션 4건 + PR18 파일럿 2건)에서 관측된 고유값은 15개뿐이며
인접 간격이 모두 정확히 5.74 cm 다.

```text
40.18  45.92  51.66  57.40  63.14  68.88  74.62  80.36
86.10  91.84  97.58  103.32  109.06  114.80  120.54
```

따라서 장치 파생 `distance_cm` 의 실질 해상도는 최선이어도 ±2.87 cm 다.
manifest 의 `distance_cm` 을 줄자 실측으로 대체하면 이 한계가 사라진다.
세션 간 거리 비교(예: 51.7 cm 대 57.4 cm)도 한 칸 차이일 뿐이므로 과대 해석하지 않는다.

## 7.7 벤치 기준선 (2026-08-18 실측) 과 그 한계

세션 4건을 모두 기록한 뒤 줄자로 실측했고, 같은 작업 중에 센서 기울기를 90도로 재설정했다.
따라서 실측값 중 일부만 캡처 조건으로 소급 적용할 수 있다.

| 항목 | 값 | 캡처 조건으로 유효한가 |
|---|---|---|
| 바닥 → 안테나 면 높이 | **75 cm** | **유효.** 기울기만 바꿨고 책상·거치대는 그대로다. 기존 100 은 눈대중 추정이었고 manifest 4건을 75 로 정정했다 |
| 센서 → 가슴 직선거리 | 50 cm | **참고만.** 기울기 변경 후 측정. 다만 장치 칸(51.66 bin ≈ 48.8–54.5 cm)에 들어와 캡처 때와 크게 다르지 않았을 것으로 본다. `distance_cm` 은 장치 파생값을 유지했다 |
| 기울기 | 현재 90도 | **무효.** 캡처 당시는 운영자 추정 ~100도. manifest 의 `sensor_angle_deg = 100` 을 유지한다 |

**이 4개 세션의 캡처 당시 기울기는 이제 확정할 수 없다.** 운영자 추정 ~100도가 남은 전부다.
90도로 찍은 향후 세션은 이 4건과 각도 축에서 비교 대상이 아니다.

### 재발 방지

기하 실측은 **캡처 전**에 하고, 캡처가 끝날 때까지 센서를 건드리지 않는다.
`templates/capture_checklist.md` 시작 전 항목에 반영했다.

### 현재 벤치 기준선 (향후 세션용)

```text
바닥 → 안테나 면        75 cm
센서 → 가슴 직선거리    50 cm
기울기                  책상면 기준 90도 (책상에 수직)
```

향후 세션은 이 기준선에서 시작하며, 값은 캡처 전에 다시 확인해 manifest 에 기록한다.

## 7.8 M-N10 영문 프로토콜 정독 결과 (센서 트랙에 영향 있는 항목만)

`docs/mmwave/20260818_SafeNest_mmWave_M-N10_Targeted_Real_Device_Capture_01.md` 전문 확인.
`M_N11_AUTHORIZED = NO`, gate `INCOMPLETE`, `NEXT_RECOMMENDED_PHASE = M-N10_CAPTURE_COMPLETION`.

**Pi smoke 는 하드 블로커가 아니다.** 앞서 §5.2 에 "Pi 를 로거로 쓰면 인간 측정 전 필수"로
적어 두었는데, 문서는 대안을 명시한다.

```text
Pi 가 로거     → INT8 SHA 3b008af4… 로 isolated smoke 를 인간 측정 전에 닫을 것
다른 검증된 raw 로거 → 캡처 진행 가능. 단 보고서에 PI_SMOKE_REMAINS_UNVERIFIED 를 적을 것
```

우리 USB/맥 로거(`tools/live_mr60_monitor.py`)가 후자에 해당한다. 즉 M-N10 캡처가
Pi 준비에 묶여 있지 않다. 다만 그 경우 보고서 표기 의무가 생긴다.

**피험자 배분 예시** — 6→DEV 2/RESERVED 4, 8→3/5, 9→3/6.
"데이터가 불편하다는 이유로 RESERVED 를 DEV 로 옮기지 않는다"가 명시돼 있다.

**raw 파일별 기록 의무** — 파일명, subject/session, 크기, SHA-256, **clocks**,
device ID, firmware/config identity. 우리 manifest 는 clocks 를 제외하고 이미 충족한다.
M-N10 세션에는 wall time 과 monotonic time 을 함께 남겨야 한다.

**창 적격성 집계는 M-N10 범위 안이다.** "M-N10 may count eligible vs invalid 30 s windows
under the frozen M-N4 contract (timing, gaps, boots, MAD)" — `tools/cap0_m_n4_feasibility.py`
가 이미 그 집계를 산출한다. 신경망 정확도 검사는 M-N10 범위 밖이며 RESERVED 추론은 0 이다.

**raw 로컬 루트** — `datasets/mmwave/raw/m_n10/` (Git 에 넣지 않음).
우리 CAP 세션의 `raw/` ignore 정책과 같은 취급이다.

## 8. 경계 (유지됨)

| 항목 | 상태 |
|---|---|
| 대규모 라벨 데이터셋 | NO |
| NORMAL/RAPID/APNEA 매핑 | NO |
| 숨 참기/무호흡 실험 | NO |
| 학습 / TFLite 추론 | NO (통합 작업 주체 미확정) |
| 구 B 모델 수정 | NO |
| 펌웨어 수정 | NO |
| raw 전처리 적용 | NO |
| 6명 모집 | NO — 모델 트랙이 명시적으로 중단 요청 |

## 9. 현재 결손

1. 독립 respiration reference 없음. M-N10 은 장비가 벤치에 올라올 때까지
   `INDEPENDENT_RESPIRATORY_REFERENCE_NOT_AVAILABLE` 상태로 두는 것이 정상이라고 회신됨.
2. 피험자 1명. `SUBJ-001` 은 M-N10 피험자가 될 수 없음.
3. `distance_cm` 줄자 실측 미수행 (장치 파생값). 다음 세션에서 1회면 해소.
4. 전이 구간(사람 입/퇴장) 데이터 없음. presence gate 경계 케이스 미확보.
5. `boot_id` 등 4개 필드의 레코드/세션 단위 해석 미확정.
6. Pi preflight (`M-N9 isolated smoke`) 미수행.
