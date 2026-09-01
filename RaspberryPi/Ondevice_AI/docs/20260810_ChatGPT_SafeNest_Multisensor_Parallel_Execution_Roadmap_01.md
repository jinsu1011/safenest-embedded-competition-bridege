# SafeNest 멀티센서 병렬 A–E 실행 로드맵

- 문서 버전: `06`
- 기준일: `2026-08-15`
- 이전 기준일: `2026-08-15` (`05`)
- canonical component root: 이 문서의 상위 저장소에서 `AGENTS.md`가 위치한 디렉터리
- 적용 대상: mmWave, CO₂, Thermal 온디바이스 AI 데이터·모델·runtime 검증
- 후속 통합 대상: PIR 보조 신호 및 멀티센서 risk fusion
- 상태: `ACTIVE_MASTER_ROADMAP`
- 2026-08-14 개정: mmWave `M-C`를 기존 팀 MR60 forensic audit → correspondence gate → 선택적 탐색 추론 → 프로토콜 실측 → 정식 평가로 세분. Phase A/B 역사는 유지한다.
- 2026-08-14 CO₂ 개정: `C-C`를 기존 팀 SCD40 legacy audit(`C-C0`) → measurement protocol freeze/operator handoff(`C-C1`) → 외부 protocol-controlled acquisition → later controlled intake/formal validation(`C-C2`)로 분리한다. logger/transport/sensor freshness, frozen feature-vector completeness, unit과 feature semantics, calibration 필드를 분리한다. Phase A/B 역사와 frozen C-B5는 변경하지 않는다.
- 2026-08-15 CO₂ 개정: PR #78의 T/RH feature-necessity 결과(`T_RH_FEATURE_DEPENDENCE_INCONCLUSIVE`)를 후속 5-seed·paired-bootstrap pre-acquisition decision audit로 재평가했다. 네 feature arm의 modest/repeatable predictive benefit은 관측됐지만 reduced-feature predictive superiority는 확립되지 않았다. 시스템 contract burden of proof가 충족되지 않아 최종 방향은 `ADOPT_REDUCED_FEATURE_DIRECTION`이며, `C-B6` reduced-feature candidate development/lock을 별도 model phase로 둔다. 현재 four-feature C-C1 protocol/B5는 historical evidence로 보존하고 formal protocol-controlled physical acquisition과 formal operator handoff를 C-B6 lock 전까지 `HOLD`한다. exploratory real-device observation은 별도 evidence class로 관리한다. B5와 LOCKED_TEST는 변경하지 않는다.
- 2026-08-15 C-B6 실행: `C_B6_REDUCED_CO2_SLOPE_CANDIDATE_001`을 새 TRAIN-only scaler, TRAIN-internal-only threshold policy, Float/TFLite/full-integer INT8 artifact, validation evidence, checksum, lock으로 생성했다. 최종 threshold는 `0.43`이며 B5 `0.58`은 상속하지 않았다. C-B6 focused validator와 INT8 equivalence gate는 PASS지만 CO2_slope INT8 input saturation이 관측되어 phase 상태는 `C_B6_PASS_WITH_LIMITATIONS`다. 다음은 limitation review를 포함한 `C-C1R` protocol revision/hand-off authorization이며 physical acquisition은 계속 `HOLD`한다.
- 2026-08-15 C-C1R 실행: `CO2_C_C1R_REDUCED_MEASUREMENT_PROTOCOL_001`을 C-B6 lock에 결속해 동결했다. `CO2 + Pi-derived CO2_slope`, nominal 60초 effective model-input/export cadence, transport/sensor freshness 분리, `ENDPOINT_H150` 150초·90초 초과 gap reset, 독립 VACANT/OCCUPIED GT, raw JSONL/session/checksum 계약을 정의했다. 다만 team main `3d86bf2a...`의 현재 capture path는 fresh SCD40 event marker/chronology와 protocol/session/candidate manifest를 제공하지 않아 `OPERATOR_HANDOFF_BLOCKED_BY_ACQUISITION_TOOLING`이다. 따라서 `C_C1R_BLOCKED`, protocol은 `FROZEN`, physical acquisition은 `HOLD`, C-C2는 `NOT_STARTED`다.

이 문서는 기존 mmWave A–E 실행 문서를 포함하면서 CO₂와 Thermal을 독립 트랙으로 병렬 실행하기 위한 상위 제어 문서다. 기존 mmWave 문서는 역사·세부 실행 근거로 계속 유효하지만, 신규 작업의 센서 간 순서와 공통 gate는 이 문서를 우선한다. 2026-08-14에 mmWave Phase C(`M-C`) 구조가 개정되었으며, Part II의 해당 절은 `docs/20260806_ChatGPT_SafeNest_mmWave_Execution_Sequence_01.md`와 동기화한다. CO₂ 트랙은 legacy evidence audit, historical four-feature protocol freeze, final model-input decision, 별도 model phase `C-B6` reduced-feature candidate development/lock, revised protocol handoff, external controlled acquisition, authorized formal intake로 분리한다. Phase A/B 원문 역사와 기존 C-C1 four-feature evidence는 유지한다.

## 0. 문서 우선순위와 해석 규칙

1. 최상위 `AGENTS.md`가 경로·안전·provenance·팀 이관 규칙의 최우선 기준이다.
2. 이 문서는 세 센서의 병렬 순서, 합류 gate, 공용 파일 변경 규칙을 정한다.
3. 아래에 이관된 mmWave 문서는 mmWave 세부 실행 기준이다. 2026-08-14 이후 Phase C는 두 문서에서 동일한 세분 구조를 따른다.
4. 각 센서 phase 보고서와 machine-readable manifest가 완료 수치의 근거다.
5. 문서와 artifact가 충돌하면 validator가 통과한 machine-readable evidence를 우선하고 문서 불일치를 별도 수정한다.

`A/B/C/D/E`라는 문자만 단독으로 쓰면 센서가 불명확하므로 신규 branch, report, manifest, issue에서는 다음 접두어를 사용한다.

| 접두어 | 트랙 | 의미 |
|---|---|---|
| `M-` | mmWave | radar raw/canonical phase, 호흡 proxy 모델, MR60 domain |
| `C-` | CO₂ | 실제 occupancy 원본, feature model, SCD40 domain |
| `T-` | Thermal | 실제 thermal frame/sequence, fall model, Thermal-44 domain |
| `I-` | Integration | 공용 provider 계약, replay simulation, risk fusion, Pi 통합 |

기존 mmWave 문서의 `A0`, `B0` 등은 각각 `M-A0`, `M-B0`와 같은 의미다. 기존 본문은 evidence 보존을 위해 이름을 일괄 치환하지 않는다.

## 0.1 팀 저장소 PR·브랜치 증거 오버레이 (2026-08-14 live-main refresh)

이 절은 팀 저장소의 실제 센서 구현·실측 자료와 현재 로드맵의 연결점을 기록하기 위한 보강 규칙이다. 2026-08-13 검토 기준은 당시 팀 `main` `f3bd342eabcad27dc2c3ecdc16f035b8b13cb153`과 그 시점 원격 branch·PR이다. 2026-08-14 M-C 개정은 팀 `main` `fdf34b804f35e5868356f0ed6f804a248aa69131`에서 기존 MR60 실측을 재확인한 후속 지식이며, 13일 검토 이력을 지우고 다시 쓰지 않는다. 이번 CO₂ audit도 같은 team `main` SHA를 기준으로 raw SCD40 evidence를 재검산했다. 팀 저장소의 구버전 `ondevice_ai/` 트리는 이번 방향성 판정과 phase evidence의 근거에서 **제외**한다. 이 절은 파일을 자동 이관하라는 지시가 아니며, 미병합 자료를 standalone 학습 데이터로 자동 편입하지 않는다.

### 0.1.1 증거 층위와 병합 상태 해석

팀 저장소 자료는 다음 세 층위로 분리한다.

| 증거 층위 | 대표 경로/자료 | 로드맵에서의 용도 | 금지 해석 |
|---|---|---|---|
| standalone offline evidence | 이 저장소의 `datasets/`, `models/`, A/B manifest·validator | 재현 가능한 전처리·split·모델 비교·locked test | 팀 실센서 로그를 근거 없이 A/B에 섞기 |
| device-domain evidence | 팀 `devices/<sensor>/`의 firmware, raw log, calibration, 분석 보고서 | `M-C0`의 기존 실측 forensic 입력, `M-C1` 이후 정식 평가 입력, C-C/T-C의 실제 입력·장치 결함·domain gap 검증 | public dataset 성능이나 모델 일반화 성능으로 승격. 기존 팀 로그만으로 `FORMAL_DEVICE_VALIDATION_SET` 또는 `REAL_SENSOR_VALIDATION` 주장 |
| integration evidence | 팀 `devices/esp32_node/`, `integration/`, 통신 규격·LCD/Pi 자료 | I-0/I-1/I-2의 packet·timestamp·provider·fail-closed 계약 검증 | 통합 노드 동작을 개별 AI 정확도로 주장 |

PR이 `open`이거나 branch에만 존재하면 **후보 evidence**일 뿐 팀 `main`의 승인된 기준이 아니다. 에이전트는 PR/branch 자료를 사용할 때 source branch, head SHA, base SHA, 병합 상태, 원본 checksum, 제한사항을 report에 남긴다. 병합되지 않은 자료는 원본을 보존한 채 C/I 검증 입력으로만 참조하고, standalone A/B artifact를 덮어쓰지 않는다.

### 0.1.2 2026-08-13 원격 PR·branch 확인 결과; CO₂ live-main refresh 2026-08-14

다음 목록은 팀 저장소의 `ondevice_ai/` 변경을 제외하고 센서·실행·통합 방향에 영향을 주는 원격 자료만 요약한 것이다.

| 상태 | 대상 | 확인된 사실 | 이 로드맵에서의 인지·처리 |
|---|---|---|---|
| `MERGED` | PR #14 `feature/co2-scd40-verification` (`ea925e4`) → team `main` (`fdf34b8`) | Git-tracked CSV 4개, 총 990 capture rows / 936 capture-valid rows. 초기 baseline 23개, breath-rise/recovery 31개의 transport-invalid row가 보존되어 있다. 센서 분리 60초 원시 시험은 `NOT VERIFIED`; report 판정은 `PARTIAL` | C-C0 legacy device evidence로만 참조한다. raw CSV의 현재 SHA-256을 다시 계산하고 committed summary/report SHA mismatch를 별도 기록한다. 분리·stale·reconnect·sensor-freshness 계약이 protocol-controlled evidence로 확인되기 전 formal C-C2 evidence로 승격하지 않는다 |
| `OPEN` | PR #15 `feature/thermal-v5-real-validation` (`e4cb7d8`) | 실제 열화상 raw frame 수신·62×80 parse·TFLite·fail-closed·UDP 경로 검증 자료가 있다. TCP 단계의 brownout/655.3°C 오류와 UDP 전환이 기록되어 있다. 문서에는 Thermal-90/MI48 계열과 Thermal-44 명칭이 혼재한다 | T-C의 runtime/domain-gap 입력으로 보존한다. `ALL PASS` 문구만으로 T-B 학습 성능·낙상 일반화·T-C 완료를 인정하지 않는다. 센서 모델명, 원시 frame 단위·calibration·orientation·프로토콜을 먼저 reconcile한다 |
| `OPEN` | PR #12 `feature/esp32-lcd-integration` (`c9f4583`) | ESP32 4센서 수집과 Pi/LCD 상태 전달을 실제 장치에서 확인했다. 다만 Thermal은 약 70% 고정/무효 pixel 때문에 full-frame stream을 끄고 `thermal_max_c`만 전송하며, 호흡수 noise와 통신 조건도 기록되어 있다 | I-0/I-1 packet·validity·timestamp·runtime evidence로 참조한다. 이 경로의 scalar thermal telemetry를 full-frame T-A/T-B 입력과 동일시하지 않는다 |
| `OPEN` | PR #11 `agent/add-competition-package` (`4ac9878`) | ESP32/Pi 실행 패키지와 통신·설치 문서를 추가한다. 새로운 학습 데이터나 센서 정확도 evidence는 추가하지 않는다 | I-6 handoff/운용 참고로만 사용한다. A/B/C 성능 근거로 사용하지 않는다 |
| `NO PR` | `codex/mmwave-20rpm-root-cause` (`0e8538c`), `codex/mmwave-phase-integration` (`b0d3c95`) | 2026-08-13: MR60 실제 로그·phase·presence·window 자료와 20 rpm 저-SNR 원인 분석이 있다. 당시 해석은 20 rpm 오차의 직접 원인이 TFLite보다 입력 품질과 estimator validity gate라는 것이었다 | 미병합 branch는 후보 evidence로 보존한다. 2026-08-14 후속 재확인은 아래 0.1.5. production 변경이나 A/B 학습 편입은 별도 review·회귀검증 후 결정한다 |

PR #13의 `ondevice_ai` 동기화 변경은 이 오버레이의 범위에서 제외한다. PR 설명에 언급된 `feature/pir-verification`은 이 검토 시점 원격 branch 목록에서 확인되지 않았으므로 승인된 PIR evidence로 간주하지 않는다.

### 0.1.3 센서별 필수 인지 사항

- **mmWave**: 팀 MR60 자료는 이미 timestamped JSONL·CSV·paced/거리/장시간 세션이 있는 장치 domain 자료다. `breath_phase`(firmware `0x0A13`)와 `breath_rate_raw`(firmware `0x0A14`)는 다른 신호다. 전자는 장치가 노출하는 최저 수준 위상형/중간 신호이고, 후자는 vendor 파생 호흡수다. true radar ADC/IQ/range-bin raw는 확인되지 않았다. 다수 세션의 timestamp-측정 cadence는 ≈10 Hz이지만, 이것이 Phase-B `BPF_ZSCORE` 입력 대응의 증명은 아니다. 단일 피험자(`S001`)·독립 호흡 참조 부재·저진폭/phase stale·presence loss·lock-loss·실패한 paced 시험이 있다. 기존 실측은 `M-C0` forensic 입력이며 정식 검증셋이 아니다. 실측 로그는 무작위로 학습에 섞지 않는다. A4의 voluntary breath-hold label은 SafeNest proxy이며 clinical apnea가 아니다.
- **CO₂**: PR #14의 SCD40 ppm 시계열은 실제 장치 증거지만 occupancy/환경 변화 자료이지 질식·유해가스 ground truth가 아니다. UCI occupancy target과 SCD40 safety rule을 분리한다. 팀 `capture_scd40.py`는 SCD40 I²C logger가 아니라 Pi `/health` HTTP polling이다. `fresh`/`age_seconds`는 transport freshness이며 SCD40 신규 measurement freshness가 아니다. CSV 독립 column과 990개 nested `raw_response_json` 모두 `co2_ppm`만 보존하고 Temperature/Humidity는 보존하지 않는다. ESP32 producer는 SCD4x `readMeasurement`에서 T/RH를 읽지만 telemetry JSON에는 버린다. H150 재구성만으로 B5 추론을 허가하지 않는다. UCI T/RH와 SCD40 on-chip T/RH는 단위가 같아도 동일 feature domain이 아니다. `read_measurement` 출력은 `TRUE_SENSOR_RAW_SIGNAL`이 아니다. 기존 실측은 `C-C0` forensic 입력이며 정식 검증셋이 아니다.
- **Thermal**: PR #15의 full-frame path와 PR #12의 `thermal_max_c` scalar path는 서로 다른 runtime contract다. Thermal-90/MI48/Thermal-44 명칭, 62×80 geometry, raw uint16→°C 변환, calibration, orientation, invalid pixel 정책을 하나의 provenance로 reconcile하기 전에는 서로의 결과를 합치지 않는다. 자세/`LYING` proxy는 실제 낙상 사건이나 임상 성능을 의미하지 않는다.
- **PIR**: 독립 AI 재학습 트랙이 아니라 mmWave 재실·퇴실과 위험 rule을 보조하는 binary evidence다. 별도 branch/실측이 승인되기 전에는 I-0 계약·fault/replay 대상으로만 다룬다.
- **통합**: ESP32 `safenest.telemetry.v1`, TCP 9000, thermal frame type 2, `thermal_max_c` scalar, `valid`/`SensorState`/stale semantics를 I-0 inventory에 함께 기록한다. 센서별 offline candidate가 고정되기 전에 learned fusion을 최적화하지 않는다.

### 0.1.4 PR·branch 자료를 phase에 연결하는 추가 gate

1. `M-C`, `C-C`, `T-C`는 팀 PR의 “실제 동작 확인”을 그대로 완료로 복사하지 않고, raw source·checksum·unit·timestamp·calibration·failure registry를 standalone canonical contract와 대조한다. mmWave는 이 대조를 단일 단계로 수행하지 않고 `M-C0` forensic → correspondence gate → (선택) 탐색 추론 → `M-C1` 프로토콜 실측 → `M-C2` 정식 평가 순서를 따른다. CO₂도 단일 단계로 수행하지 않고 `C-C0` legacy forensic → logger/transport/sensor freshness → feature completeness → semantic/H150/B5 identity/pre-inference gate → (선택) 탐색 추론 → `C-C1` protocol freeze/operator handoff → external acquisition → authorized `C-C2` intake/validation 순서를 따른다.
2. 실제 하드웨어 log는 immutable raw evidence로 보존하고, 재생(replay)용 파생 파일을 별도 namespace로 만든다. 원본을 relabel하거나 overwrite하지 않는다.
3. C phase에서 발견한 통신 결측, dead pixel, stale phase, low-SNR, sensor identity mismatch가 모델 문제인지 입력/장치 문제인지 분리하여 기록한다. 입력 문제를 곧바로 재학습 사유로 쓰지 않는다.
4. 팀 PR이 병합되었더라도 `devices/`의 device-domain evidence와 standalone `datasets/`의 A/B evidence를 자동으로 합치지 않는다. 병합은 source/base SHA와 충돌·ownership 검토가 끝난 뒤 별도 handoff에서 수행한다.
5. 최종 흐름: **standalone A/B 재현성 확보 → 기존 장치 evidence M-C0/C-C0 → 대응 판정 → protocol freeze/handoff(C-C1; mmWave는 M-C1) → sensor-specific final input decision → 별도 model phase C-B6 candidate development/lock → revised protocol handoff → 외부 controlled acquisition → authorized formal intake(M-C2/C-C2) → 측정·승인된 gap만 D에서 보완 → I에서 replay·rule fusion·Pi 검증**. M-C/C-C 불일치가 자동으로 M-D/C-D를 허가하지 않는다.

### 0.1.5 2026-08-14 M-C 기존 실측 증거 재검토 (후속 지식)

재확인 기준: 팀 저장소 `https://github.com/jinsu1011/safenest-embedded-competition` `main` `fdf34b804f35e5868356f0ed6f804a248aa69131`. standalone `main` `4260119cb5274d6cffacf1a40934bc81f86c46ee`의 M-B11/M-B12 lock은 `REAL_DATA_OFFLINE_CANDIDATE`이며 장치 검증으로 승격하지 않는다. 세부 수치·필드 lineage는 mmWave 실행 문서 §5를 따른다.

확인된 상태:

| 항목 | 상태 |
|---|---|
| timestamped JSONL / 세션 CSV / delivery_v2 manifest | `AVAILABLE` |
| 측정 ≈10 Hz cadence (다수 세션) | `AVAILABLE` |
| `breath_phase` (0x0A13) | 최저 노출 위상형/중간 신호 |
| `breath_rate_raw` (0x0A14) | vendor 파생 출력 |
| paced 12/15/20 rpm, 거리 조건, ≈31 min 로그 | `AVAILABLE` |
| 독립 호흡 참조 / 다피험자 / true radar raw | `NOT ESTABLISHED` |
| Phase-B 신호-의미 대응 / 정식 device validation | `NOT YET ESTABLISHED` / `NOT YET PERFORMED` |

~20 rpm: 15 rpm paced 조건에서 vendor `breath_rate_raw` mean/median ≈ 18.80 / 19.0 rpm, phase 주기 추정 ≈ 15.01 rpm. 조건 의존 vendor bias를 시사하는 탐색적 증거이며 보편 보정 규칙이 아니다. vendor 호흡수, phase 주기, AI 분류를 한 현상으로 합치지 않는다.

Track M의 현재 개념 순서는 다음과 같다.

```text
M-B locked offline candidate
→ M-C0 existing-team MR60 forensic audit
→ signal/cadence/offline-contract correspondence gate
→ optional exploratory legacy-device inference
→ independent review
→ M-C1 protocolized physical measurement
→ M-C2 formal device-domain evaluation
→ only measured and separately authorized gaps may start M-D
```

## 1. 현재 출발 상태

| 트랙 | 현재 검증 상태 | 즉시 시작 가능한 작업 | 금지되는 선행 작업 |
|---|---|---|---|
| mmWave | `M-A0~M-A6 PASS_WITH_WARNINGS` | `M-B0` 평가 protocol·near-duplicate | LOCKED_TEST를 이용한 선택·튜닝 |
| CO₂ | 기존 NPZ는 synthetic smoke 성격이며 실제 UCI provenance 미복원 | `C-A0` 원본 identity·inventory | 기존 synthetic 지표를 실제 성능으로 승격 |
| Thermal | 실제 평가 dataset 부재로 일부 테스트 skip | `T-A0` dataset 선정·identity | 실제 낙상 성능·일반화 성능 주장 |
| Integration | mock·fail-closed wiring은 존재, 실센서 통합 미검증 | `I-0` 계약 차이 inventory만 가능 | 센서별 candidate lock 전 fusion 최적화 |

Phase A 완료는 실센서 성능이나 배포 준비 완료를 뜻하지 않는다. 각 센서는 offline evidence, device-domain evidence, Pi evidence를 별도 상태로 보존한다.

## 2. 병렬 실행 구조

```text
Track M  M-A 완료 ──> M-B locked offline ──> M-C0 existing MR60 forensic
                                           ──> correspondence gate
                                           ──> (optional) exploratory inference
                                           ──> M-C1 protocolized capture
                                           ──> M-C2 formal eval
                                           ──> M-D gap data (승인된 측정 gap만) ──┐
                                                                                │
Track C  C-A real-data reconstruction ──> C-B locked offline ──> C-C0 legacy SCD40 audit
                                           ──> C-C1 four-feature protocol freeze (historical)
                                           ──> final model-input decision ──> HOLD
                                           ──> C-B6 reduced-feature candidate development / lock
                                               (`C_B6_PASS_WITH_LIMITATIONS`, threshold `0.43`)
                                           ──> C-C1R reduced-feature protocol revision / handoff authorization
                                           ──> external controlled acquisition
                                           ──> authorized C-C2 intake / validation
                                           ──> C-D gap data (별도 승인만) ─┤
                                                                                ├─> I-0~I-6 integration
Track T  T-A dataset reconstruction ──> T-B model ──> T-C Thermal-44 domain ───┤
                                                                                │
Track I  contract inventory only ───────────────────────────────────────────────┘
```

센서 트랙 사이는 병렬 실행한다. 한 센서 트랙 내부에서는 이전 gate가 통과하기 전에 다음 phase를 성능 탐색 목적으로 시작하지 않는다.

### 2.1 지금 권장하는 동시 작업

- mmWave 작업자: `M-B0` evaluation protocol, exact/near-duplicate audit, LOCKED_TEST 접근 통제
- CO₂ 작업자: `C-A0` 실제 UCI source identity, license, raw file inventory, checksum
- Thermal 작업자: `T-A0` dataset 후보 비교, license, subject/session/sequence provenance 적합성
- 통합 작업자: 코드 수정 없이 local/team provider 계약과 signal semantics 차이 목록 작성

### 2.2 병렬 작업의 hard dependency

- `C-B`는 `C-A6` 통과 후에만 시작한다.
- `T-B`는 `T-A6` 통과 후에만 시작한다.
- scaler, normalizer, feature selector, calibration threshold는 각 센서의 TRAIN에서만 fit한다.
- LOCKED_TEST는 architecture, preprocessing, imbalance, threshold, representative dataset 선택에 사용하지 않는다.
- `I-2` replay integration은 최소 한 센서의 locked offline candidate와 나머지 센서의 명시적 unavailable/mock 상태가 있어야 시작할 수 있다.
- `I-3` fusion 최적화는 M/C/T 세 트랙의 validation contract가 고정된 후 시작한다.
- 실센서 성능 주장은 해당 센서의 정식 C 평가(mmWave는 `M-C2`)와 Pi 측정이 완료된 뒤에만 가능하다. 기존 팀 로그만으로는 주장하지 않는다.

## 3. 공용 파일과 branch 충돌 방지

센서별 구현은 독립 branch와 report namespace를 사용한다.

```text
feature/mmwave-b0-evaluation-protocol
feature/co2-a0-real-data-inventory
feature/thermal-a0-dataset-selection
refactor/integration-provider-contract
```

다음 공용 파일은 여러 센서 branch가 동시에 직접 갱신하지 않는다.

- `AGENTS.md`
- `README.md`
- `docs/README.md`
- `datasets/MANIFEST.json`
- `models/model_manifest.json`
- 공통 evaluation schema와 risk configuration
- 팀 저장소의 `shared/contracts/`, `.github/`, root 문서

센서 phase branch에서는 센서 전용 manifest·report를 먼저 생성한다. 공용 inventory 반영은 phase 승인 후 별도 integration commit에서 evidence를 읽어 갱신한다. `git add .`는 사용하지 않는다.

## 4. 공통 sensor-local A–E 의미

| Phase | 공통 의미 | 센서별 변형 |
|---|---|---|
| A | 실제 원본에서 canonical dataset과 immutable split을 만드는 단계 | reader, label, grouping unit가 modality별로 다름 |
| B | 실제 데이터 offline 학습·비교·locked candidate 고정 | metric과 architecture가 modality별로 다름 |
| C | 실제 기기 출력과 학습 입력 사이의 domain·runtime 검증. mmWave는 기존 실측 forensic(`M-C0`), 대응 판정, 선택적 탐색 추론, 프로토콜 실측(`M-C1`), 정식 평가(`M-C2`)를 분리하고, CO₂는 legacy audit(`C-C0`) → historical four-feature protocol(`C-C1`) → final model-input decision → model phase `C-B6` reduced-feature candidate lock → revised protocol → later controlled intake/formal validation(`C-C2`)을 분리한다 | MR60, SCD40, Thermal-44 각각 별도. SCD40는 logger/transport/sensor freshness와 frozen feature completeness를 혼동하지 않는다. 현재 four-feature C-C1/B5는 변경하지 않고, C-B6 candidate lock 전 acquisition을 HOLD한다. MR60 하드웨어 부재는 `M-C1`만 `BLOCKED_HARDWARE`로 두고 `M-C0`을 공백으로 되돌리지 않는다 |
| D | C에서 측정·승인된 gap을 메우는 추가 dataset/model 확장. C 불일치가 자동 재학습을 허가하지 않음 | gap 없는 무목적 수집 금지 |
| E | sensor-local artifact·contract·report lock | 기존 mmWave 원문의 E는 상위 `I` fusion 단계로 재해석 |

각 센서의 A 종료물에는 최소한 source identity, license, checksum, inventory, label contract, group split, canonical data, sample provenance, quality audit, duplicate/leakage audit, standalone validator가 있어야 한다.

## 5. 병렬 synchronization gate

### Gate P0 — 현재

- M-A 완료
- C-A0, T-A0 시작 가능
- M-B0 시작 가능
- 통합은 contract inventory만 허용

### Gate P1 — 세 트랙의 데이터 기반 확보

- M-B protocol과 near-duplicate 판정 완료
- C-A6 통과
- T-A6 통과
- 공용 manifest가 세 실제 dataset을 synthetic fixture와 구분

### Gate P2 — offline candidate lock

- M-B, C-B, T-B가 각자 Float/TFLite/INT8 equivalence와 multi-seed 결과를 보유
- sensor별 LOCKED_TEST 사용 이력이 기록됨
- 일반 성능과 배포 성능 상태가 분리됨

### Gate P3 — device-domain 검증

- mmWave: `M-C0` 기존 팀 MR60 forensic → signal/cadence/offline-contract correspondence → 대응이 방어 가능할 때만 탐색적 레거시 추론 → 독립 검토 → `M-C1` 프로토콜 실측 → `M-C2` frozen Phase-B candidate 정식 평가
- SCD40: `C-C0` 기존 팀 실측 forensic → logger vs transport vs sensor freshness → frozen feature-vector completeness → semantic correspondence → `ENDPOINT_H150` → frozen C-B5 identity → pre-inference gate → 대응이 방어 가능할 때만 탐색적 레거시 추론 → historical four-feature `C-C1` protocol freeze → final model-input decision → `C-B6` reduced-feature candidate development/lock → revised protocol/handoff → external acquisition → authorized `C-C2` intake/formal validation
- `TRANSPORT_FRESHNESS != SCD40_FRESH_MEASUREMENT_FRESHNESS`. `/health`의 `fresh == true`만으로 신규 SCD40 measurement로 보지 않는다. H150 재구성만으로 B5 추론을 허가하지 않는다. UCI T/RH 단위와 SCD40 on-chip T/RH 단위가 같아도 동일 feature domain으로 보지 않는다
- Thermal-44: 실제 출력 contract와 offline 입력 contract 비교 (T-C 단계 규칙)
- domain gap, missingness, latency, warming-up, stale 정책을 측정한다
- mmWave `breath_phase`와 `breath_rate_raw`를 동일 신호로 취급하지 않는다
- 기존 팀 실측을 정식 validation set으로 승격하지 않는다
- C-C0/C-C1의 gap과 final model-input decision은 측정 protocol·candidate lock을 설계하는 근거이지 C-B5 재튜닝이나 자동 C-D 허가가 아니다. 현재 reduced 방향은 four-feature predictive superiority를 뜻하지 않으며, C-B6가 `C_B6_PASS_WITH_LIMITATIONS`로 닫혔고 C-C1R protocol이 동결됐어도 team acquisition tooling correction과 precollection validator PASS 전까지 formal protocol-controlled physical acquisition을 HOLD한다. Exploratory pre-deployment real-device observation은 별도 evidence class로 허용할 수 있지만 자동으로 C-C2 evidence가 되지 않는다. C-C2 formal validation 결과와 별도 decision gate 뒤에만 측정·승인된 gap에 한해 M/C/T-D 진입한다. mmWave `DEVICE_DOMAIN_GAP_OBSERVED`도 Phase-B 수정이나 자동 M-D를 허가하지 않는다

### Gate P4 — integration readiness

- 세 sensor provider가 동일한 fail-closed output contract를 구현
- replay simulation과 fault injection 통과
- Pi 5 latency·memory·thermal·장시간 안정성 측정
- 임의의 mock 성공을 실센서 성공으로 보고하지 않음

## 6. 신규 작업 에이전트 필수 시작 절차

모든 센서 작업 에이전트는 작업 전에 다음을 보고해야 한다.

1. 선택한 sensor track과 phase ID
2. authoritative input artifact와 checksum
3. 수정할 전용 파일과 건드리지 않을 공용 파일
4. split/grouping/LOCKED_TEST 정책
5. 완료 validator와 회귀 테스트
6. 생성될 report·manifest 경로

phase ID 없이 “모델 개선”, “데이터 전처리”, “성능 향상”처럼 범위가 불명확한 작업은 시작하지 않는다.

---

# Part II — 기존 mmWave 실행 로드맵 원문 이관

아래 내용은 `docs/20260806_ChatGPT_SafeNest_mmWave_Execution_Sequence_01.md`를 이관한 것이다. mmWave의 세부 수치·Priority 7–18·A–E 판단 근거는 이 부분을 따른다. 상위 병렬 운용에서 기존 `A~E`는 `M-A~M-E`로 식별하며, 기존 Phase E의 fusion 작업은 세 센서가 준비된 뒤 `I` 트랙에서 실행한다. 2026-08-14에 Phase C만 기존 팀 MR60 증거에 맞게 세분했으며, 그 절은 상세 실행 문서와 동기화한다.

---

# 0. 외부 에이전트 참조용 로컬 작업 공간 현황 및 디렉터리 맵 (Local Workspace & File Structure Overview)

> **[CAUTION] 작업 에이전트를 위한 안내**:
> 본 문서는 SafeNest 활성 작업 공간의 디렉터리 구조, 실측 아티팩트 해시, 모델 계보 및 실행 순서를 정의합니다. 모든 작업은 먼저 최상위 `AGENTS.md`를 읽고 이 문서의 canonical-root 규칙을 따라야 합니다.

---

### 0.1 최상위 디렉터리 및 경로 규칙
- **유일한 활성 프로젝트 루트**: 이 문서의 상위 디렉터리인 `embed2/`
- **활성 코드 위치**: `config/`, `datasets/`, `models/`, `preprocessing/`, `inference/`, `sensors/`, `integrated_node/`, `risk/`, `scripts/`, `tests/` 등 최상위 직속 경로
- **과거 버전 보존 위치 (READ-ONLY)**: `archive/version_snapshots/`
- **금지 사항**: `SafeNest_V4_*`, `SafeNest_V5_*`, `SafeNest_V6/`, `ondevice_ai/`를 별도 활성 루트로 생성하거나 archive의 코드·manifest·모델을 runtime에서 자동 선택하지 않는다.
- **경로 기록 원칙**: 활성 JSON/YAML/manifest/metadata에는 저장소 상대경로만 기록하고 사용자별 절대경로와 `file://` URI를 저장하지 않는다.
- **버전 관리 원칙**: 현재 버전은 폴더명이 아니라 model/dataset manifest, 보고서, Git tag 및 release artifact로 표현한다.

---

### 0.2 로컬 디렉터리 & 주요 파일 트리 구조 (Actual Local Tree Snapshot)

```text
embed2/
├── AGENTS.md                              # canonical-root, archive, path, phase 규약
├── config/                                # 활성 입력·센서·risk 계약
├── datasets/                              # 활성 dataset, raw archive, A0–A6 manifest
├── models/                                # 활성 모델과 명시적 historical baseline
├── preprocessing/                         # canonical/experimental 전처리
├── inference/                             # 모델 loader·interpreter
├── sensors/                               # mock·real provider contract/adapter
├── integrated_node/                       # 최상위 노드 실행·위험도 연결
├── risk/                                  # 위험도·fallback
├── scripts/                               # 현재 phase·학습·검증 실행기
├── tests/                                 # 현재 작업본 회귀 테스트
├── benchmarks/                            # 활성 기준·결과
├── docs/
│   ├── 20260806_ChatGPT_SafeNest_mmWave_Execution_Sequence_01.md
│   └── reports/
├── releases/                              # 배포 산출물; 활성 source root 아님
└── archive/
    └── version_snapshots/                 # V4/V5/구 V6 전체 스냅샷, 읽기 전용
```

---

### 0.3 주요 로컬 아티팩트 실측 해시 & 파이프라인 검증 상태

| 자산 구분 | 파일 경로 (Relative to canonical root) | 실측 SHA-256 Hash / MD5 | 보존 및 계보 상태 (Lineage Status) |
|---|---|---|---|
| **Zenodo 60GHz Raw Archive** | `datasets/raw_archives/external_datasets/db_records.zip` | SHA256: `f0bcfdac94f88b43bb34d3da8e8f071a787291f86c97798059b8dbf4d4be08b0`<br>MD5: `370de95033f1a98b78e57dbbea92a8bc` | `LOCAL_REPACKAGED_ARCHIVE_CONFIRMED`<br>(110 participants, 4 posture/test conditions) |
| **V6 Processed NPZ** | `datasets/mmwave/processed/mmwave_respiration_v1.npz` | SHA256: `a08072f3d9b55cd95b530c7b5b90f17ef80f6015ee76119f217b9d834c1107fb` | `SYNTHETIC_SMOKE_AND_RETRAINING_ASSET`<br>(3,433 windows, 10Hz/30s) |
| **mmWave v0.1.0 INT8 (기존)** | `models/mmwave/mmwave_resp_int8_v0.1.0.tflite` | SHA256: `43cdd6f321c2b645232162233e098c2b65549388cbc9e680a17a0eccdc8f0158` | `HISTORICAL_SOURCE_MAPPING_INCOMPLETE`<br>(기존 외부 실데이터 개발 이력) |
| **V6 Candidate INT8** | `models/mmwave/mmwave_resp_int8_v0.2.0_candidate.tflite` | SHA256: `85c023d3eefca13ecbb72a841974e53a56d5f4173920645d46df49a9088452ff` | `SYNTHETIC_SMOKE_ONLY`<br>(Z-score: mean=0.006092, std=2.501384) |

---

### 0.4 로컬 개발 환경 검증 실행 CLI 명령어
```bash
# canonical project root(embed2) 진입
cd "<path-to-embed2>"

# 1. candidate 기술 결함 및 품질 정밀 검사 구동 (Exit Code 0 성공 검증)
python3 scripts/check_mmwave_candidate.py

# 2. V6 mmWave 파이프라인 pyTest 구동
python3 -m pytest tests/test_mmwave_v6_pipeline.py -v

# 3. candidate 재학습 및 양자화 구동 (결정성 보장 seed=42)
python3 scripts/train_mmwave.py --seed 42 --epochs 25

# 4. Mock 파이프라인 bounded 1-step smoke 테스트
python3 -c 'from integrated_node.run_node import SafeNestIntegratedNode as N; n=N(mode="mock"); n.start(); print(n.step().to_json()); n.shutdown()'
```

---

# SafeNest mmWave Priority 7–18 및 A–E 상세 실행 순서

- 작성일: 2026-08-06
- Phase C 개정일: 2026-08-14
- Phase C 개정 근거: 팀 저장소 `main` `fdf34b804f35e5868356f0ed6f804a248aa69131`에서 확인한 기존 MR60 실측 증거. Phase A/B 역사와 locked offline candidate는 변경하지 않는다.
- 문서 목적: Priority 6 이후 mmWave 데이터·학습·양자화·장치 도메인·멀티모달 융합 작업의 선행관계와 실행 순서를 구체화
- 대상: Zenodo 60 GHz radar 원본 재가공, SafeNest mmWave 실데이터 모델, MR60BHA2 장치 도메인, 후속 데이터 확장, 멀티모달 융합
- 내용: 최상단 Section 0에 로컬 디렉터리 맵, 실측 해시, 스크립트 실행 명령 포함. 이하 본문은 실행 순서 및 방법론 기술.

---

## 1. 핵심 결론

Priority 7부터 바로 시작하지 않는다. 가장 먼저 수행할 작업은 **A. Zenodo 실제 raw-to-NPZ pipeline 복원**이다.

현재 합성 NPZ는 학습·양자화·평가 코드의 smoke test에는 유용하지만, class 패턴이 쉽게 분리되어 성능이 포화될 수 있다. 이 상태에서 preprocessing, class imbalance, model architecture의 우열을 결정하면 실제 인체·radar domain 성능과 관계없는 결론을 얻을 수 있다.

최종 전체 순서는 다음과 같다.

```text
Priority 6 자산·gap 분석
→ A. Zenodo raw-to-NPZ 복원·무결성 감사
→ B. 실데이터 모델 실험·학습·비교
→ Priority 7–18을 실데이터 기준으로 재구성해 수행
→ C0. 기존 팀 MR60 실측 forensic audit
→ C0A. signal/cadence/offline-contract correspondence gate
→ C0B. 대응이 방어 가능할 때만 exploratory legacy-device inference
→ 독립 검토
→ C1. 프로토콜 기반 신규 MR60 실측
→ C2. frozen Phase-B candidate의 정식 device-domain 평가
→ D. 측정된 domain gap이 별도 승인된 경우에만 dataset/model 확장
→ E. 멀티모달 model·risk fusion 개선
```

C 단계는 단일 “MR60 수집 후 모델 검증”이 아니다. 기존 비공식 실측, Phase-B 대응 판정, 탐색적 추론, 프로토콜 실측, 정식 장치 평가를 분리한다. C에서 발견한 domain mismatch는 재학습을 자동 허가하지 않으며, 그 작업은 D의 별도 승인 대상이다.

---

## 2. 전 단계 공통 원칙

### 2.1 계보 분리

다음 모델은 서로 다른 lineage로 관리한다.

| 모델 | 역할 | 해석 원칙 |
|---|---|---|
| Historical v0.1.0 | 기존 외부 실데이터 개발 이력의 역사적 모델 | 사용자 확정 이력은 인정하되 exact raw-file-to-model mapping 부족은 별도 표시 |
| V6 v0.2.0 candidate | 합성 NPZ 기반 smoke·재현성 모델 | 실세계 성능 근거로 사용 금지 |
| 신규 real-data offline candidate | Zenodo 110명 계보 복원 이후 학습할 신규 모델 | real-subject offline 성능 대상 |
| MR60-adapted candidate | 측정된 domain gap이 **별도 승인된 M-D**에서만 만들 수 있는 후속 모델 | M-C 산출물이 아니다. offline candidate와 분리. M-C는 frozen Phase-B 후보를 평가할 뿐 이 lineage를 생성·교체하지 않는다 |

### 2.2 불가역 산출물 분리

원본에서 만들어진 canonical signal과 실험적 전처리 결과를 분리한다.

- raw rFFT에서 복원한 canonical respiration phase를 우선 보존한다.
- detrending, band-pass filtering, Z-score를 유일한 NPZ에 불가역적으로 박아 넣지 않는다.
- preprocessing ablation을 수행할 수 있도록 canonical signal과 `preprocessing_profile`을 분리한다.
- Z-score 통계는 subject split 이후 train data로만 계산한다.

### 2.3 locked test 원칙

- 전처리, imbalance, architecture, seed, calibration 선택은 train·validation으로만 수행한다.
- subject-wise test는 최종 candidate가 선정된 후 원칙적으로 한 번 사용한다.
- 여러 실험의 test 점수를 보고 configuration을 선택하지 않는다.
- v0.1.0, v0.2.0, 신규 real-data candidate의 최종 비교는 동일 locked test에서 수행한다.

### 2.4 일반 성능과 배포 성능 분리

- Zenodo offline 성능은 `OFFLINE_REAL_DATA` 또는 `REAL_SUBJECT_GENERALIZATION`으로 표시한다.
- 팀 저장소에 기존 MR60 실측이 있어도, C2 정식 device-domain 평가 전에는 `REAL_SENSOR_VALIDATION`을 주장하지 않는다.
- 기존 팀 로그·CSV는 `LEGACY_OR_INFORMAL_DEVICE_EVIDENCE`이며 `FORMAL_DEVICE_VALIDATION_SET`이 아니다.
- Mac latency를 Raspberry Pi latency 또는 sensor-to-alarm latency로 해석하지 않는다.
- 임상 apnea와 voluntary breath hold를 동일한 것으로 표현하지 않는다.

---

## 3. Phase A — Zenodo 실제 raw-to-NPZ pipeline 복원

### A0. 원본 identity·schema·inventory 고정

#### 목적

전체 변환 전에 원본 archive의 identity와 내부 recording 구조를 machine-readable inventory로 고정한다.

#### 세부 작업

1. 원본 archive의 공식 dataset identity, version, DOI, license, 바이트 크기, checksum을 기록한다.
2. 로컬 archive가 공식 archive와 byte-identical하지 않으면 공식 hash와 로컬 repackaged hash를 모두 보존한다.
3. participant, posture, activity/test, recording, radar data, timestamp, chirp config, reference signal, annotation 목록을 inventory로 만든다.
4. 누락 파일, zero/damaged frame, timestamp 역전·중복·gap, 손상 recording을 식별한다.
5. 각 recording에 고유한 `dataset_id`, `subject_id`, `session_id`, `recording_id`, `source_file_id`를 부여한다.

#### 완료 판단

- 전체 participant·recording 수와 조건별 구성을 설명할 수 있다.
- 각 rFFT가 timestamp·chirp config·annotation·reference 파일과 연결된다.
- 제외·주의 recording이 이유와 함께 별도 표시된다.

---

### A1. 안전한 rFFT reader와 소규모 pilot

#### 목적

전체 110명을 처리하기 전에 소수 participant/recording으로 schema와 signal 해석을 확정한다.

#### 세부 작업

1. rFFT container의 serialization, frame 수, array shape, dtype, complex value 여부, virtual antenna·range-bin 순서를 확인한다.
2. 외부 serialization은 출처·hash를 확인한 입력만 읽고, 임의 object execution을 허용하지 않는 방식을 선택한다.
3. chirp config에서 frame periodicity, antenna 수, range-bin 간격, 파장·주파수 정보를 읽어 recording metadata에 연결한다.
4. radar timestamp 수와 rFFT frame 수를 대조한다.
5. sitting/lying, rest/post-exercise, breath-hold 포함/미포함을 고르게 포함한 pilot subset을 선정한다.

#### 완료 판단

- pilot 모든 recording이 같은 규칙으로 decoding된다.
- frame·timestamp alignment 오류가 숫자로 기록된다.
- 전체 변환을 시작하기 전에 예외 schema가 식별된다.

---

### A2. target range-bin·phase extraction 규칙 결정

#### 목적

rFFT에서 SafeNest canonical respiration phase를 일관되고 재현 가능하게 추출한다.

#### 세부 작업

1. 탐색 가능한 거리 구간과 제외할 near-field·background bin을 정한다.
2. target bin 선택 후보를 비교한다.
   - magnitude 최대 bin
   - static clutter 제거 후 energy 최대 bin
   - respiration band 에너지 최대 bin
   - phase coherence/SNR 기반 bin
   - 인접 bin·virtual antenna 통합
3. label이나 test 결과를 보고 bin을 선택하지 않고 deterministic signal-quality rule을 사용한다.
4. complex phase 추출, unwrap, discontinuity 처리, zero/damaged frame 정책을 정한다.
5. multi-antenna 중 단일 antenna를 선택할지 coherence-weighted aggregation을 사용할지 비교한다.
6. 추출된 phase의 시간 파형, spectrum, respiration-band energy, SNR, motion indicator를 pilot에서 확인한다.

#### 중요 제약

- 0.1–0.5 Hz BPF를 canonical signal의 유일 보존본에 박아 넣지 않는다.
- filter 전 phase와 filter 후 derived profile을 구분해야 Priority 7 ablation을 수행할 수 있다.
- range-bin selection rule과 선택 결과를 sample provenance에 남긴다.

#### 완료 판단

- pilot 전반에서 respiration-related phase가 시각·스펙트럼·reference 근거로 해석 가능하다.
- 선택 규칙이 participant·posture·label에 따라 수작업으로 바뀌지 않는다.
- 실패·low-quality recording의 판정 조건이 명시된다.

---

### A3. timestamp·resampling·window 정책

#### 목적

연속 radar timeline을 SafeNest 10 Hz, 30초 canonical window로 변환하되 시간 provenance와 연속성을 잃지 않는다.

#### 세부 작업

1. config의 nominal frame period과 실제 timestamp 간격을 대조한다.
2. duplicate, backward timestamp, gap, dropped frame의 허용·제외 기준을 정한다.
3. 원본이 이미 10 Hz이면 불필요한 resampling을 하지 않는다.
4. irregular timestamp인 경우 small gap interpolation과 large gap rejection을 분리한다.
5. 30초 window와 stride를 정하고, overlap된 window가 동일 연속 recording에서 파생된 사실을 보존한다.
6. train에서 overlap augmentation을 사용하더라도 validation·test에서 과도한 상관 window가 지표를 부풀리지 않도록 non-overlap 또는 event-centered 평가를 별도 설계한다.
7. 연속 timeline을 보존해 향후 false alarms/hour, event detection delay, event miss rate를 계산할 수 있게 한다.

#### 완료 판단

- 모든 window가 source recording과 start/end timestamp로 연결된다.
- window 생성으로 인한 중복·상관 수치가 기록된다.
- gap을 조용히 보간하여 없던 호흡 신호를 만들지 않는다.

---

### A4. annotation·label mapping 정책

#### 목적

원본 test 조건과 non-breathing annotation을 SafeNest label에 의미적으로 연결한다.

#### 세부 작업

1. 원본 label·test condition, annotation timestamp, SafeNest target label, mapping 규칙을 분리한다.
2. `NORMAL`, `RAPID_OR_ABNORMAL`, `APNEA` 각각에 대해 direct/derived/ambiguous 매핑을 지정한다.
3. voluntary breath hold는 clinical apnea와 별도 원본 label로 보존하고 SafeNest APNEA로의 매핑은 `DERIVED`로 표시한다.
4. post-exercise recording 전체를 자동으로 RAPID으로 지정하지 않고, 실제 호흡률·불규칙성·reference 가용성에 기반한 파생 조건을 정한다.
5. event overlap, event-centered window, transition window, mixed window, ambiguous window 정책을 비교한다.
6. annotation 해상도보다 정밀한 label을 임의로 만들지 않는다.

#### 현재 반드시 재검토할 정책

기존 안의 “30초 window 중 non-breathing overlap이 50%, 즉 15초 이상이면 APNEA” 규칙은 그대로 고정하지 않는다. 현재 inventory 기준 breath-hold event는 대부분 약 10–11초이므로 15초 기준은 APNEA sample을 거의 제거할 수 있다.

다음을 비교한 후 정책을 선정한다.

- 10초 이상 event overlap
- window 내 event 비율+최소 event 길이 결합
- event midpoint 기준 30초 window
- transition window 학습 제외, 평가 별도 보고
- event detection 평가와 window classification 평가 병행

#### 완료 판단

- 모든 sample에 original label, SafeNest label, mapping type, overlap/duration 근거가 있다.
- label 분포와 제외·ambiguous 수치가 기록된다.
- posture·activity·recording condition artifact가 class label을 대신하지 않는다.

---

### A5. subject-wise split·sample provenance

#### 현재 상태 (2026-08-08)

- `MMWAVE_SUBJECT_SPLIT_PROFILE_001` 생성 및 검증 완료
- 110명 subject를 seed 42로 TRAIN 77 / VALIDATION 17 / LOCKED_TEST 16에 단일 배정
- 440개 recording을 subject split에 고정: TRAIN 308 / VALIDATION 68 / LOCKED_TEST 64
- 각 split의 lying/sitting × rest/post-exercise 조건 균형 확인
- subject overlap 0건, recording overlap 0건
- A4 pilot 15 windows의 `mapping_type`, `assignment_status`, label provenance 보존
- `AMBIGUOUS` window는 provenance에 남기고 pure-class training에서 제외
- 인구통계 companion metadata 미보유로 age/sex/height/weight 균형은 `NOT_VERIFIABLE`
- A5 gate: `PASS_WITH_WARNINGS`, A6 entry: `READY_WITH_CONDITIONS`

#### 목적

중첩 window를 만들기 전에 subject 단위 분할을 고정하고 모든 sample을 source에 연결한다.

#### 세부 작업

1. participant를 train, validation, test에 중복 없이 배정한다.
2. 가능하면 posture, activity, sex/age group, label event 분포를 그룹 단위로 균형화한다.
3. 동일 subject의 모든 recording·window를 하나의 split에만 배정한다.
4. split seed, grouping key, subject 목록, 배정 이유를 machine-readable manifest로 보존한다.
5. 각 window에 다음 계보를 보존한다.
   - sample/dataset/source file ID
   - subject/session/recording ID
   - posture/activity/device/environment
   - start/end timestamp
   - selected range bin·antenna·phase extraction profile
   - original/SafeNest label·mapping type
   - split·synthetic flag·quality flag

#### 완료 판단

- subject overlap 0건
- recording overlap 0건
- duplicate window hash의 cross-split overlap 0건
- 모든 NPZ index가 provenance record에 1:1로 연결

---

### A6. 전체 변환·품질 감사·A 종료 gate

#### 현재 상태 (2026-08-08)

- 전체 110명·440 recording 변환 완료: `SUCCESS` 90, `SUCCESS_WITH_WARNINGS` 350, 실패 0
- canonical real-data window 530개 생성, 각 window는 300 sample `float64`
- window/provenance/NPY 530행의 1:1 의미·신호 SHA-256 정렬 확인
- NaN/Inf/constant·near-constant window 0건
- cross-split subject·recording·window·exact-signal overlap 0건
- acquisition timestamp는 공통 수집 컴퓨터 clock 기준이며 timezone은 `UNVERIFIED`; UTC 변환을 주장하지 않음
- A6 gate: `PASS_WITH_WARNINGS`, Phase B entry: `READY_WITH_CONDITIONS`
- standalone A6 validator는 모든 A0 recording의 성공 상태·window 수를 확인하고, 530개 window/provenance/NPY 행의 식별자·label·split·eligibility·signal hash를 전수 대조한다.
- annotation read/parse 실패는 정상 label로 대체하지 않고 해당 recording을 차단하며 exception registry에 기록한다.
- checksum gate는 필수 산출물 목록의 누락·중복·형식 오류·project root 이탈을 거부한다.

#### 목적

pilot에서 확정한 규칙으로 전체 110명을 변환하고 B 단계에 사용해도 되는지 판정한다.

#### 세부 작업

1. 전체 recording에 동일한 extraction·window·label 규칙을 적용한다.
2. 처리 성공/실패/제외 수, 제외 이유, condition·subject별 신호 품질을 요약한다.
3. NaN/Inf, constant signal, extreme amplitude, zero frame, timestamp gap, low SNR을 감사한다.
4. duplicate·near-duplicate·cross-split leakage를 감사한다.
5. class·subject·posture·activity·recording 분포를 요약한다.
6. canonical processed dataset, provenance, split manifest, preprocessing/extraction config의 checksum을 고정한다.
7. 임의 수의 원본 recording에서 processed window까지 역추적하는 spot check를 수행한다.

#### A 종료 기준

- raw → canonical phase → window → label → split chain이 재실행 가능하다.
- subject/sample provenance가 machine-readable하게 보존된다.
- split·duplicate·window leakage 감사가 통과한다.
- 제외·low-quality sample이 조용히 삭제되지 않고 이유와 함께 기록된다.
- 이 기준을 충족하기 전에 B의 모델 탐색을 시작하지 않는다.

---

## 4. Phase B — 실데이터 모델 학습·비교

### B0. 평가 protocol·baseline·test lock

#### 목적

실험을 반복하며 test에 맞추는 것을 방지하고 v0.1.0, v0.2.0, 신규 모델을 비교할 공통 규칙을 먼저 정한다.

#### 세부 작업

1. train/validation/test subject 목록과 checksum을 고정한다.
   - A5의 TRAIN/VALIDATION/LOCKED_TEST 배정을 재계산하거나 변경하지 않는다.
   - scaler·normalizer·feature-selection 통계는 TRAIN에서만 fit한다.
   - architecture 비교 전 exact duplicate 감사에 더해 near-duplicate 진단을 수행한다.
2. model selection metric과 final test metric을 분리한다.
3. 필수 metric을 정한다.
   - macro F1
   - class별 precision/recall/F1
   - APNEA/breath-hold recall·miss rate
   - confusion matrix
   - class prediction distribution·collapse
   - continuous timeline이 있을 경우 false alarms/hour·event miss·detection delay
4. v0.1.0의 exact historical preprocessor가 불완전하면 현재 canonical contract에서의 결과를 “historical-model compatibility benchmark”로 표시한다.
5. v0.2.0의 real test 결과는 실데이터로 학습했다는 근거가 아니라 합성 학습 모델의 external compatibility 결과로 표시한다.
6. 신규 model이 확정되기 전에 locked test 점수를 실험 선택에 사용하지 않는다.

---

### B1. Priority 7 — preprocessing ablation

#### 실행 시점

A6 통과 후, architecture·imbalance 탐색 전에 수행한다.

#### 실험 설계

기존 4개 누적 mode만으로는 세 기법의 “독립 기여도”를 완전히 알 수 없다. 다음 두 수준 중 하나를 사전 선택한다.

#### 권장 설계 A — full factorial

Detrend, BPF, Z-score의 on/off 8개 조합을 동일 split·seed·architecture·loss에서 비교한다. main effect와 interaction을 구분할 수 있다.

#### 권장 설계 B — 최소 충분 ablation

자원을 줄여야 하면 full pipeline, no detrend, no BPF, no Z-score, raw/minimal 조건을 비교한다. 각 조건은 full pipeline에서 한 요소만 제거해 marginal effect를 본다.

#### 추가 분석

- 0.1–0.5 Hz BPF가 >30 bpm 신호를 감쇠시키는지 확인한다.
- BPF 유무 ablation과 0.1–0.5/0.1–0.8 Hz band tuning을 하나의 결론으로 섞지 않는다.
- APNEA/breath-hold처럼 거의 constant인 구간에 high-pass·detrending이 미치는 영향을 별도 본다.
- 성능 외에 saturation, signal amplitude distribution, 제외·warning 비율을 보고한다.

#### 완료 판단

- validation metric으로 preprocessing profile을 선정한다.
- test result를 보고 profile을 변경하지 않는다.
- 선정된 profile과 대안 profile의 신호·성능 trade-off가 기록된다.

---

### B2. Priority 8 — class imbalance 전략

#### 실행 시점

Priority 7에서 preprocessing profile을 고정한 후 수행한다.

#### 세부 작업

1. 실제 train split에서 class count와 subject당 event/window 수를 재계산한다.
2. 합성 NPZ에서 유도된 고정 class weight를 재사용하지 않는다.
3. 동일 split·preprocessor·architecture·seed에서 다음을 비교한다.
   - standard cross-entropy, no weighting
   - real train split에서 계산한 class weighting
   - train-only random oversampling
   - multi-class focal loss
4. oversampling은 validation/test에 적용하지 않고, subject diversity를 늘리지 않는다는 한계를 표시한다.
5. macro F1뿐 아니라 APNEA recall, precision, false positive, subject별 편차를 비교한다.
6. 임계값 선택이 필요하면 validation에서만 선정한다.

#### 완료 판단

- 소수 class recall을 높이면서 precision·false alarm이 과도하게 악화되지 않는 전략을 선정한다.
- 고정 수치가 아니라 실제 split 기반 설정과 선택 근거를 남긴다.

---

### B3. Priority 9 — TinyML architecture 비교

#### 실행 시점

preprocessing과 imbalance 전략을 일단 고정한 후 수행한다.

#### 비교 대상

- Conv1D + Global Average Pooling baseline
- SeparableConv1D 계열
- Conv1D + BiLSTM 계열: full INT8 변환 가능성을 먼저 확인하고 미지원 operator·Select TF Ops가 필요하면 TinyML 배포 후보에서 분리

#### 공정 비교 조건

- 동일 subject split
- 동일 preprocessing profile
- 동일 loss/imbalance strategy
- 동일 epoch budget·early stopping 원칙
- 동일 evaluation code·metric
- parameter count, Float/INT8 크기, validation macro F1·class recall, 변환 성공 여부 비교

#### 완료 판단

- Float 성능만 높은 모델이 아니라 full INT8 변환, footprint, recall, stability를 포함한 상위 1–2개 구조를 선별한다.
- 타겟 제약을 넘는 구조는 성능이 높아도 deployment finalist에서 분리한다.

---

### B4. Priority 10 — multi-seed 재현성

#### 실행 시점

모든 실험 조합에 수행하지 않고 Priority 9의 상위 1–2개 configuration에 수행한다.

#### 세부 작업

1. 최소 3개 training initialization seed에서 반복한다.
2. 각 seed의 training history, best epoch, validation macro F1, class recall, model checksum을 보존한다.
3. mean, standard deviation, minimum/worst-seed 성능을 보고한다.
4. initialization seed 안정성과 subject split 변화 안정성을 구분한다.
5. 실제 generalization 안정성이 중요하면 별도 subject-group split seed 또는 group cross-validation을 후속 실험으로 정의한다.

#### 완료 판단

- 평균만이 아니라 worst-seed 성능이 수용 가능한 구조를 선정한다.
- `std ≤ 0.05`, `mean F1 ≥ 0.80`같은 기준은 실제 baseline 분포를 보기 전에 불변 진리로 놓지 않고, 선정 규칙으로 사전 합의한다.

---

### B5. Priority 13 — representative dataset 구성 비교

#### 실행 시점

Float finalist가 선별된 후 INT8 candidate 생성 전에 수행한다.

#### 실험 설계

class-balanced calibration을 즉시 “개선된 정답”으로 고정하지 않고 다음을 비교한다.

- deterministic train-order baseline
- train distribution 비율을 반영한 random sample
- class-balanced sample
- amplitude·SNR·subject·condition·extreme range를 반영한 distribution-aware sample

#### 필수 기록

- train split에서만 선정
- calibration sample index·sample ID
- class·subject·condition 분포
- preprocessed tensor min/max/percentile
- input/output saturation
- Float→INT8 metric drop·output MAE·Top-1 agreement

#### 완료 판단

- class balance자체가 아니라 activation range 표현, INT8 성능, saturation 결과로 calibration profile을 선정한다.

---

### B6. Priority 12 — Float Keras → Float TFLite → INT8 equivalence

#### 실행 시점

각 finalist 및 calibration 후보에 수행한다. 최종 candidate 선정 전 필수 검사이다.

#### 세부 작업

1. 동일 validation input을 세 stage에 입력한다.
2. Keras→Float TFLite, Float TFLite→INT8의 다음을 계산한다.
   - Top-1 agreement
   - dequantized output MAE·max error
   - class별 prediction change
   - macro F1·recall drop
   - input/output saturation
3. 출력이 softmax probability이면 `logit MAE`라고 부르지 않고 probability/output MAE로 표시한다.
4. mismatch sample을 sample ID와 함께 보존해 특정 class·subject·signal range에서 변환 오차가 집중되는지 분석한다.

#### 완료 판단

- 변환 단계별 성능 하락과 오차가 기록된다.
- 사전 정한 agreement, output error, F1/recall drop, saturation 기준을 충족한다.

---

### B7. Priority 11 — input perturbation robustness

#### 실행 시점

INT8 finalist에 수행한다. 이후 M-C2는 **frozen candidate**에 대해 device-realistic perturbation을 재평가할 수 있다. 이 반복은 모델·scaler·preprocessing 변경, fine-tuning, 후보 교체를 허가하지 않는다.

#### 세부 작업

1. 교란 주입 지점을 canonical phase 전·후 중 명시한다.
2. 다음 교란을 독립 및 필요 시 결합 조건에서 평가한다.
   - Gaussian noise: SNR 20 dB, 10 dB 등
   - amplitude scaling
   - baseline drift
   - short/long dropout
   - timestamp jitter·missing frame
   - motion burst·outlier
3. 각 교란의 정의, random seed, SNR 계산 방식, dropout mask를 보존한다.
4. clean 대비 macro F1·class recall 하락, collapse, saturation, confidence 변화를 보고한다.
5. BPF·detrending이 당연히 제거하는 교란만으로 robustness를 과대평가하지 않는다.

#### 완료 판단

- clean 성능과 교란별 성능 하락이 비교된다.
- 변형 불가능/위험 조건은 모델 추론 대신 invalid/fallback으로 처리할지 결정한다.
- 이 결과를 실센서 robustness로 표현하지 않는다.

---

### B8. Priority 14 — Mac offline latency·footprint

#### 실행 시점

구조 후보 상대 비교와 finalist 확인 단계에 수행한다.

#### 측정 조건

- warm-up 후 반복 측정
- 단일 interpreter 재사용
- thread 수, delegate, runtime/version, CPU 환경 기록
- model invoke-only latency와 preprocessing+quantization+invoke latency 분리
- mean, median, P95, P99, min/max
- TFLite 파일 크기, parameter 수, 가능하면 peak memory

#### 해석 원칙

- 100회는 최소 smoke 측정으로 보고 안정적 percentile에 필요한 반복 수를 늘릴 수 있다.
- `<5 ms`, `P99 <15 ms`는 Mac 개발 기준일 뿐 Pi 5·end-to-end 성능을 보장하지 않는다.
- 30초 window startup latency와 model invoke latency를 분리한다.

#### 완료 판단

- 모델별 동일 환경 상대 지연·크기 비교가 가능하다.
- 실측 환경과 측정 범위가 결과에 포함된다.

---

### B9. Priority 15 — Mock end-to-end integration

#### 실행 시점

선정 전 finalist가 runtime에서 실제로 로드될 수 있는지 검증한다.

#### 필수 조건

1. 테스트가 명시적으로 해당 finalist model·metadata·checksum을 선택해야 한다.
2. 기존 runtime default model을 로드한 것을 finalist 통합 성공으로 판정하지 않는다.
3. 현재 지원하지 않는 `--steps` 같은 명령을 완료 조건으로 쓰지 않고 bounded test harness 또는 명시적 종료 조건을 준비한다.
4. NORMAL, RAPID_OR_ABNORMAL, APNEA, invalid/fault, missing/stale 조건을 포함한다.
5. 다음을 검증한다.
   - actual loaded model ID/version/checksum
   - fallback 사용 여부·이유
   - input window contract
   - `InferenceResult` class/score/confidence/latency/valid/error
   - risk input·JSON output
   - timeout·stale·sensor fault 처리

#### 완료 판단

- finalist의 checksum이 runtime metadata와 일치한다.
- 모든 시나리오가 예외 중단 없이 올바른 valid/fallback/fault 계약으로 종료된다.
- scenario name으로 정답 score를 강제한 결과와 모델이 실제로 만든 prediction을 구분한다.

---

### B10. Priority 16 — real-data offline candidate 선정

#### 선정 전 필수 산출물

- preprocessing ablation table
- imbalance comparison
- architecture comparison
- multi-seed stability
- representative calibration comparison
- Float/Float TFLite/INT8 equivalence
- perturbation robustness
- latency·footprint
- Mock E2E 결과

#### 선정 규칙

candidate 선정 방법을 최종 test를 보기 전에 고정한다. 다음을 함께 본다.

- validation macro F1
- APNEA/breath-hold recall·precision
- subject별 worst-case 성능
- seed 분산
- Float→INT8 drop·agreement·saturation
- robustness 하락
- model size·latency
- runtime 호환성

단순히 F1이 가장 높은 모델을 선정하지 않는다. APNEA recall이 0이거나 class collapse, 과도한 saturation, runtime 미지원, lineage 불일치가 있는 후보는 제외한다.

#### 최종 test

확정된 후보 하나를 locked subject-wise test에 평가한다. 동일 test에서 v0.1.0, v0.2.0 candidate, 신규 real-data candidate를 비교한다. 이 결과를 보고 다시 7–13을 tuning하지 않는다. 필요하면 새 실험 cycle과 새 holdout 정책을 명시한다.

#### 완료 판단

- 하나의 **Real-Data Offline Candidate**가 근거와 함께 선정된다.
- 이 후보를 MR60 deployment 최종 모델으로 즉시 선언하지 않는다.

---

### B11. Priority 17 — offline candidate artifact lock

#### 고정 항목

- raw archive/dataset identity·checksum
- processed dataset·provenance·split manifest checksum
- extraction·preprocessing profile/version
- label mapping/version
- scaler mean/std·clip·filter
- training config·seed·environment
- Keras·Float TFLite·INT8 checksum
- representative dataset identity·indices
- input/output tensor contract·class map
- validation/test metric·scope
- runtime role·fallback·known limitations

#### 완료 판단

- manifest·metadata·artifact의 path, checksum, scaler, class map, contract가 일치한다.
- 이전 v0.1.0·v0.2.0 lineage를 덮어쓰지 않는다.
- 상태를 `REAL_DATA_OFFLINE_CANDIDATE`에 상응하게 분리하고 MR60 실센서 검증 완료로 표현하지 않는다.

---

### B12. Priority 18 — 실데이터 offline 검증 보고

#### 필수 내용

1. raw-to-NPZ lineage 요약
2. participant·recording·window·class·split 통계
3. 제외·low-quality·ambiguous sample 통계
4. Priority 7–15 실험 비교표
5. v0.1.0 vs v0.2.0 vs real-data candidate 최종 test
6. Float/TFLite/INT8 lineage·equivalence
7. robustness·latency·Mock E2E
8. 선정·제외 candidate 이유
9. `REAL_SUBJECT_GENERALIZATION`, `REAL_SENSOR_VALIDATION`, `BLOCKED_HARDWARE`, `NOT_VERIFIABLE` 범위 분리
10. C 단계 MR60 인수인계 조건: 기존 팀 실측 forensic(C0) → correspondence gate → 선택적 탐색 추론 → 프로토콜 실측(C1) → 정식 평가(C2). 재학습은 D.

#### 완료 판단

- 합성 smoke 성과와 실데이터 성과가 분리된다.
- 실제 실행·실측한 수치만 포함한다.
- 외부 검토자가 최종 candidate의 source-to-runtime chain을 확인할 수 있다.
- C2에서 frozen candidate의 device-domain 재평가 항목이 명시된다. 재학습·adaptation은 D.

---

## 5. Phase C — MR60BHA2 실측 device-domain 검증

Phase C의 질문은 더 이상 “offline radar classifier를 학습할 수 있는가”가 아니다. 질문은 다음과 같다.

> 물리 MR60BHA2가 내보내는 신호의 물리·시간 의미가, 고정된 Phase-B 모델이 사용한 신호 domain과 충분히 대응하는가?

C 단계는 하드웨어가 새로 도착해야만 시작하는 공백 상태가 아니다. 팀 저장소 `main`에는 이미 timestamped JSONL, 세션 CSV, paced-breathing·거리 조건 실측, 장시간 로그, 진단/delivery manifest가 있다. 이 증거는 2026-08-14에 팀 `main` `fdf34b804f35e5868356f0ed6f804a248aa69131`에서 재확인한 **후속 device-domain 지식**이며, Phase A/B 개발 당시 존재했던 것처럼 A/B 역사를 다시 쓰지 않는다.

Phase C는 다음을 하나의 단계로 합치지 않는다.

1. 기존 비공식·레거시 실측
2. Phase-B 입력 대응 판정
3. 탐색적 레거시 추론
4. 이후 프로토콜 제어 실측
5. 정식 device-domain 평가

하드웨어 가용성 gate는 Phase C의 개념적 시작점이 아니다. 신규 프로토콜 수집(C1)의 선행조건이다. 기존 로그가 있으면 C0은 하드웨어 부재로 차단되지 않는다.

### 5.0 Frozen Phase-B 경계와 과학적 한계

C는 Phase B를 재개하지 않는다. 현재 후보는 `REAL_DATA_OFFLINE_CANDIDATE`로 남으며 다음으로 승격하지 않는다.

- 선택 후보: `M-B3_CONV1D_GAP_BASELINE_seed42_M-B5_CAL_CLASS_BALANCED_120`
- 엄격 INT8 runtime: `M-B3_CONV1D_GAP_BASELINE_seed42_M-B6_STRICT_INT8`
- 입력 계약: `int8 [1, 300, 1]`, 명목 10 Hz · 30초 · 300 sample
- 전처리: `M-B1_D0_B1_Z1` / `BPF_ZSCORE` (약 0.1–0.5 Hz 호흡대역 강조)
- artifact SHA-256: `6dff6aaa72c79d76715d40cf7e32bb1e6cd9b2c2e3ac78eaf2fda737561430c5`

300개의 숫자를 `[1,300,1]`로 reshape할 수 있다는 사실만으로 Phase-B 입력이 성립하지 않는다. 신호 의미와 시간 의미가 대응해야 한다.

최종 offline recovery-evaluation 한계는 C가 침묵 속에 수리하는 대상이 아니다.

- Accuracy ≈ 0.560
- Macro F1 ≈ 0.494836
- NORMAL recall ≈ 0.20
- RAPID_OR_ABNORMAL recall ≈ 0.421053
- APNEA-proxy recall ≈ 0.935484
- APNEA-proxy FPR ≈ 0.522727
- initialization-seed 민감성 확인됨

재학습·전처리 변경·seed 재선택·INT8 재교정·class/threshold 변경은 C가 아니라, 측정된 gap이 별도 승인된 뒤의 D다.

팀 저장소의 구버전 `ondevice_ai/`는 이 locked candidate의 검증이 아니다. 역사적 구현·호환 맥락으로만 참조하고, 탐색적 추론을 한다면 standalone M-B11 artifact SHA에 묶는다.

### 5.1 2026-08-14 확인된 기존 팀 증거 상태

아래는 C0 실행 결과가 아니라, 로드맵이 더 이상 “실측 없음/cadence 미지”를 전제하지 않도록 고정한 **후속 증거 상태**다. 정식 검증 완료를 뜻하지 않는다.

| 항목 | 상태 |
|---|---|
| 기존 물리 MR60 측정 | `AVAILABLE` |
| timestamped JSONL | `AVAILABLE` |
| 측정된 ≈10 Hz cadence | 다수 세션에서 `AVAILABLE` |
| phase-like 호흡 신호 | MR60이 노출하는 중간/위상형 신호로 `AVAILABLE` |
| vendor 호흡수 출력 | `AVAILABLE` |
| paced 12/15/20 rpm 시험 | `AVAILABLE` |
| 거리 조건 세션 | `AVAILABLE` |
| 장시간(≈31 min) 세션 | `AVAILABLE` |
| 독립 호흡 참조(벨트/spirometer 등) | `NOT ESTABLISHED` |
| 다피험자 정식 검증 집단 | `NOT ESTABLISHED` (delivery 식별자는 `S001`) |
| true radar ADC/IQ/range-bin raw | `NOT ESTABLISHED` |
| Phase-B 신호-의미 대응 | `NOT YET ESTABLISHED` |
| 정식 device validation | `NOT YET PERFORMED` |

대표 경로(팀 저장소, 확인 시점 `main`):

- `devices/mmwave/firmware/`
- `devices/mmwave/firmware/csv/2026-07-26_han_junwoo_delivery_v2/`
- `devices/mmwave/firmware/logs/final/`
- `docs/mmwave/`
- `docs/operations/PROJECT_PROGRESS.md`

Provenance는 세 층으로 분리한다. 현재 경로 ownership, 원 측정 생성, 이후 재현 분석을 한 사람의 “jinsu data”로 합치지 않는다.

- 원 측정/CSV delivery 적재: `41af82b89ef8b47a15e380583ea0eac37384406e`
- 경로 재배치(PR #2)와 문서 재배치(PR #7)는 소유권/문서 정리이며 원 측정 생성 사건이 아니다.
- 이후 재현 분석 예: `3b44e505490811b640ed9200b2fd6ed27846edc3` — schema 1.2 약 31분 로그에서 ESP C++와 Python 호흡 계산 18,276건 비교, gate-decision 불일치 51/18,276 (0.279%), phase dropout 및 `breath_phase` 2소수 양자화 관찰.

### 5.2 신호 rawness 분류와 호흡 개념 분리

필드/아티팩트는 파일명이 아니라 producer-code lineage로 분류한다.

| 분류 | 의미 |
|---|---|
| `TRUE_RADAR_RAW_SIGNAL` | ADC / IQ / complex range-bin / raw rFFT |
| `SENSOR_LOWEST_EXPOSED_PHASE_LIKE_SIGNAL` | 장치가 외부로 내보내는 최저 수준 위상형 신호 |
| `PHYSICAL_INTERMEDIATE_SIGNAL` | 센서 내부 처리 후의 중간 물리 신호 |
| `VENDOR_DERIVED_OUTPUT` | 벤더 알고리즘이 만든 파생값 |
| `TEAM_DERIVED_OUTPUT` | 팀 펌웨어/분석이 계산한 파생값 |
| `MODEL_READY_OR_PROCESSED` | Phase-B 전처리까지 적용된 입력 |
| `UNKNOWN` | producer lineage 미확인 |

현재 확인된 해석(C0에서 producer code로 재확인):

- firmware `0x0A13` → `totalPhase` / `breathPhase` / `heartPhase`. JSONL 키 `breath_phase`는 `SENSOR_LOWEST_EXPOSED_PHASE_LIKE_SIGNAL` 또는 `PHYSICAL_INTERMEDIATE_SIGNAL`. true radar raw가 아니다.
- firmware `0x0A14` → `breathRaw`. JSONL 키 `breath_rate_raw`는 `VENDOR_DERIVED_OUTPUT`.
- 팀 필터 호흡수는 `TEAM_DERIVED_OUTPUT`.

세 호흡 개념을 혼동하지 않는다.

```text
물리 흉곽/레이더 상호작용
→ MR60 내부 레이더 처리
→ MR60-exposed breath_phase
→ (선택) 팀 신호처리
→ 가능한 30 s 모델 입력 구성
→ frozen Phase-B classifier
→ NORMAL / RAPID_OR_ABNORMAL / APNEA-proxy
```

별도 계보:

```text
MR60 내부 vendor algorithm
→ breath_rate_raw
→ vendor 호흡수 추정 (rpm)
```

후자는 명시적으로 증명되기 전에는 모델 입력이 아니다. vendor 호흡수 스트림을 raw radar data로 취급하지 않는다.

### 5.3 세 종류의 “10 Hz” 주장

| 층 | 의미 | 현재 상태 |
|---|---|---|
| A. Model contract | Phase-B 명목 표현 = 10 Hz, 30 s, 300 sample | locked |
| B. Acquisition intent | 소스코드의 명목/목표 수집 주파수 | 구현 intent일 뿐 C의 증거가 아님 |
| C. Measured cadence | timestamp에서 구한 유효 sampling frequency | delivery_v2 다수 세션에서 ≈9.99 Hz로 측정됨 |

B를 C의 증명으로 쓰지 않는다. 확인된 예(팀 `devices/mmwave/firmware/csv/2026-07-26_han_junwoo_delivery_v2/manifest.json`, CSV timestamp 재계산과 일치):

- `S001_NORMAL_D06` 9.99496 Hz, `D09` 9.99613 Hz, `D12` 9.99580 Hz, `D15` 9.99837 Hz
- `S001_BREATH_PACED_12_02` 9.99543 Hz, `15_03` 9.99410 Hz, `20_04` 9.99423 Hz, `20_05` 9.99299 Hz
- 선택 세션의 최대 샘플 간격 ≈101–103 ms, duplicate/backwards timestamp 없음

이 수치는 일부 세션의 시간 의미가 명목 10 Hz에 가깝다는 C0 자산이다. 그 자체로 Phase-B 입력 대응의 증명이 아니다.

Export producer `devices/mmwave/firmware/export_mmwave_csv.py`는 timestamp와 `breath_phase`를 보존하고, 정규화·평활·재샘플·세션 병합을 하지 않으며, presence 부재 구간에 phase를 합성하지 않는다. 이 CSV는 임의 수작업 CSV보다 가치가 크지만 정식 검증셋이 아니다.

### 5.4 역사적 “~20 rpm” 관측의 현재 해석

“센서가 대략 20 rpm을 출력한다”는 모호한 문장은 폐기한다. 팀 분석(`devices/mmwave/firmware/analysis/breath/2026-07-28_vitals_measured_vs_reference.json`, `docs/operations/PROJECT_PROGRESS.md`)은 다음을 구분한다.

- vendor 호흡수 estimator의 조건 의존 행동
- phase 파형 주기성
- AI 분류 출력

확인된 탐색적 수치(paced cue 참조, 독립 생리 센서 아님):

| 참조 | phase 주기 추정 | vendor mean | vendor median | vendor MAE |
|---|---:|---:|---:|---:|
| 12 rpm | 12.34 | 14.52 | 14.0 | 2.61 |
| 15 rpm | 15.01 | 18.80 | 19.0 | 3.80 |
| 20 rpm | 20.01 | 19.40 | 22.0 | 5.02 |

15 rpm paced 조건에서 vendor 필드는 약 19 rpm, phase-like 주기 추정은 약 15 rpm이었다. 이는 조건 의존 양의 vendor bias를 시사하는 **exploratory evidence**다. 보편 bias 모델이나 고정 보정 offset을 선언하지 않는다.

실패/약세 세션은 삭제하지 않고 device-domain QA 증거로 보존한다.

- `S001_BREATH_PACED_12_01`: 파일명은 12 rpm이나 실제 약 6.06 rpm (한 호흡 약 10초). 12 rpm 정답으로 쓰지 않는다.
- `S001_NORMAL_D15`: lock-loss. `breath_rate_raw`가 15.0에 고정되고 std=0인 구간이 있다. 전체 distance 표본 std가 0인 것은 아니며, vitals freeze와 긴 동일-거리 streak로 해석한다.
- `S001_BREATH_PACED_20_04` 얕은 호흡 실패 vs `20_05` deep 성공.

Paced cue는 탐색적 참조일 뿐 정식 생리 ground truth가 아니다. 자연 호흡 기록에는 독립 호흡 참조가 없다.

### C0. 기존 팀 MR60 증거 forensic audit (`M-C0`)

상태 라벨: `EXPLORATORY_EXISTING_TEAM_MEASUREMENT` / `LEGACY_OR_INFORMAL_DEVICE_EVIDENCE`. `FORMAL_DEVICE_VALIDATION_SET`이 아니다.

목적: 신규 수집 전에 이미 있는 물리 증거를 특성화한다.

답해야 할 질문:

- 어떤 측정이 있는가, 무엇이 생성했는가, 필드 의미는 무엇인가
- 어떤 값이 raw / intermediate / vendor / team-derived인가
- timing·metadata·누락은 무엇인가
- 30 s / 300 sample 창을 구성할 수 있는가
- 신호 의미가 Phase-B와 대응하는가
- 역사적 ~20 rpm 관측이 실제로 무엇을 가리키는가

C0는 producer-code lineage와 Git 이력을 포함한다. 성공한 C0가 모델 예측을 만들 필요는 없다. 과학적으로 유효한 종료 예:

```text
USABLE_FOR_DEVICE_DOMAIN_EXPLORATION = true
FORMAL_MODEL_VALIDATION_READY = false
```

또는:

```text
EXPLORATORY_INFERENCE_ALLOWED = false
CAUSE_UNRESOLVED = true
```

계획된 machine-readable 산출물(이 로드맵 개정 작업에서 생성하지 않음):

```text
existing_measurement_inventory.json
signal_field_inventory.json
producer_code_lineage.json
timing_characterization.json
measurement_metadata_completeness.json
offline_contract_correspondence.json
legacy_device_data_quality.json
twenty_rpm_evidence_inventory.json
exploratory_inference_eligibility.json
m_c0_summary.json
validation_result.json
checksums.sha256
```

기존 증거의 한계를 유지한다: 피험자 다양성 부족(`S001`), 독립 호흡 참조 부재, 일부 기하/자세/방향 metadata 불완전, 실패·오라벨 시험, phase dropout, lock-loss, true radar raw 부재, 세션 간 수집 버전 차이.

### C0A. Signal / cadence / offline-contract correspondence gate

frozen-model inference **이전**에 기계 판독 가능한 결정을 요구한다. 배열 shape 호환만으로 추론하지 않는다.

독립 평가 항목과 값(`YES` / `NO` / `UNKNOWN`):

```text
signal_semantic_correspondence
cadence_correspondence
thirty_second_window_correspondence
bpf_zscore_input_compatibility
tensor_construction_reproducible
```

결정:

```text
AUTHORIZED_FOR_EXPLORATORY_INFERENCE
또는
BLOCKED_PENDING_SIGNAL_CORRESPONDENCE
```

reason code 예: `SIGNAL_SEMANTICS_UNVERIFIED`, `CADENCE_NOT_VERIFIABLE`, `UNIT_SEMANTICS_UNKNOWN`, `SESSION_BOUNDARY_UNCLEAR`, `PHASE_DROPOUT_UNRESOLVED`, `INSUFFICIENT_METADATA`.

거리/자세 메타 부재는 tensor-level blocker가 아니라 제한사항일 수 있다. blocking과 non-blocking limitation을 구분한다. 탐색 추론은 필수가 아니다. 다음도 과학적으로 유효한 M-C0 결과다.

```text
cadence_correspondence = YES
signal_semantic_correspondence = UNKNOWN
exploratory inference = BLOCKED_PENDING_SIGNAL_CORRESPONDENCE
```

### C0B. Exploratory legacy-device inference (선택)

C0A가 기술적으로 방어 가능할 때만 수행한다. 필수 성공 조건이 아니다. 라벨은 `EXPLORATORY_LEGACY_DEVICE_INFERENCE`.

모든 예측은 다음을 묶는다: source measurement, checksum, session, timestamp/window 경계, signal field, 변환, preprocessing identity, model identity, model SHA, tensor 구성, metadata 한계.

신뢰할 수 있는 독립 라벨이 없으면 정식 accuracy/F1을 계산·홍보하지 않는다. pacing 파일명이나 팀 기억만으로 정식 ground truth가 되지 않는다. 올바른 결과로 `BLOCKED_PENDING_SIGNAL_CORRESPONDENCE`를 허용한다.

독립 검토 후에만 C1으로 진행한다.

### C1. 프로토콜 기반 물리 MR60 측정 캠페인 (`M-C1`)

C1은 레거시 분석과 분리된 **신규** 수집이다. C0에서 발견한 gap이 프로토콜을 정한다.

하드웨어 가용성·capture 경로·전원·timestamp 기준·안정 환경은 **C1의 선행조건**이다. 없으면 C1만 `BLOCKED_HARDWARE`로 표시한다. C0는 기존 로그로 계속할 수 있다. 하드웨어가 없다고 Mac에서 C0/C0A와 D의 gap 조사를 병행할 수 있으나, 그 병행이 C2 정식 평가나 재학습을 허가하지는 않는다.

기술적으로 적용 가능한 최소 메타:

```text
subject pseudonym, session ID, trial ID, timestamps, effective cadence,
sensor distance, posture, sensor orientation, presence/motion state,
raw vs derived signal identity, acquisition code commit/SHA,
firmware version, sensor/firmware identity, trial duration,
reference breathing condition, independent respiration reference where needed,
QA/exclusion criteria, signal-lock status, environmental/context metadata
```

사람 대상 수집은 동의·개인정보·보관 정책을 따른다. voluntary breath hold를 임상 apnea로 표현하지 않는다. 실패·약세 세션은 삭제하지 않고 QA·exclusion 정책 설계에 쓴다.

### C2. Frozen candidate의 정식 device-domain 평가 (`M-C2`)

정식 metric은 여기에 속한다. C0/C0B가 아니다.

요구:

- 프로토콜 제어 세션
- 검증된 신호 대응
- 재현 가능한 tensor 구성
- frozen Phase-B 모델
- 불변 평가 정책
- 신뢰할 수 있는 참조 라벨/상태
- 명시적 subject/session 분리
- 최종 평가 전 exclusion 규칙 고정
- 평가 데이터에 대한 침묵의 모델 튜닝 금지

비교 대상은 Zenodo canonical 입력과, C1에서 구성한 MR60 입력이다.

- sample interval·gap·jitter
- amplitude·phase range·percentile
- respiration-band spectrum
- SNR·motion artifact·dropout
- distance·angle·posture별 분포
- preprocessing 후 scaler range·clipping·INT8 saturation
- frozen candidate의 confidence·class distribution. 정식 recall/F1은 신뢰 가능한 독립 라벨이 있을 때만

C2는 domain gap을 **식별**할 수 있다. 식별 라벨은 `DEVICE_DOMAIN_GAP_OBSERVED`다. 이는 Phase B 수정을 허가하지 않는다.

```text
poor device behavior
!=
authorization to modify Phase B
```

다음을 C 안에서 하지 않는다.

```text
팀 측정을 TRAIN에 병합
Phase-B 모델 fine-tune
architecture 재선택
preprocessing 변경
selected seed 변경
INT8 재교정
class semantics/threshold 변경
```

`MR60_REAL_SENSOR_VALIDATED`는 **frozen Phase-B candidate**의 정식 C2 평가가 요구를 충족하고 한계를 정직하게 보고한 뒤에만 사용한다. 기존 팀 CSV에 모델을 한 번 돌리거나, M-C 안에서 후보를 교체·adaptation한 것으로 이 상태를 주지 않는다.

확인된 실패 조건만이 D 진입 후보가 된다. D 자체는 별도 승인 없이 시작하지 않는다.

---

## 6. Phase D — gap-driven 추가 dataset 확장

### 시작 조건

A/B의 real-subject 결과와 C2에서 측정된 MR60 domain 결과를 먼저 본다. C0/C0B의 탐색적 관찰만으로 D를 시작하지 않는다. “좋아 보이는 공개 호흡 dataset”이 아니라 확인된 실패 조건을 채우는 dataset만 선정한다.

C에서 발견한 device-domain mismatch는 재학습을 자동 허가하지 않는다. D는 gap-driven dataset/model 확장 트랙이며 별도 승인 후에만 다음을 검토한다. 아래 목록은 **M-D 전용**이며 M-C0/M-C1/M-C2 작업 단위가 아니다.

1. external test only
2. MR60-specific input adapter
3. device-specific scaler
4. source-specific preprocessing profile
5. fine-tuning
6. joint retraining
7. domain adaptation·multi-stage training

adaptation으로 model·scaler·preprocessor·contract이 바뀌었다면 최소한 multi-seed, Float/TFLite/INT8 equivalence, representative calibration, device-realistic robustness, runtime latency, E2E, quality check, artifact lock·report를 반복한다. MR60 sample이 적거나 subject diversity가 부족하면 최종 test를 학습에 사용하지 않는다.

### gap 예시

- MR60 device domain
- distance·angle·posture
- motion·cough·position change·background movement
- low SNR·dropout·multipath
- rapid·irregular·shallow breathing
- apnea/breath-hold event 수·길이
- subject age·body type·health diversity
- continuous session·event timeline

### dataset별 용도 선정

각 dataset을 다음 중 하나 이상으로 지정한다.

- source-only benchmark
- external test only
- joint retraining
- fine-tuning
- domain adaptation
- reference-domain only

비레이더 생리 신호는 별도 전이 전략이 없는 한 radar phase dataset에 직접 병합하지 않는다.

### 진입 절차

1. gap→candidate→intended role 정의
2. source·license·waveform·provenance 검증
3. 사용자 승인
4. 원본 archive 보존·checksum
5. source-specific adapter·canonical contract 변환
6. 기존 dataset과 분리된 무결성 감사
7. source-only/external test
8. 필요한 경우에만 retraining/fine-tuning
9. 기존 candidate와 동일 protocol 비교

---

## 7. Phase E — 멀티모달 model·risk fusion 개선

### 시작 조건

- mmWave 개별 모델의 real-data 입출력 계약과 failure condition이 안정됨
- Thermal, CO₂, PIR의 timestamp·valid·stale·error·confidence 계약이 일관됨
- sensor 간 시간 정렬 방법이 정의됨
- fusion 평가에 사용할 실제 scenario·event label이 있음

### 단계별 접근

1. **Late-fusion baseline**
   - 기존 sensor별 score·valid·confidence·stale 입력을 사용
   - 우선 rule-based fusion의 오탐·미탐·fault isolation을 측정
2. **Calibration**
   - sensor별 score/confidence calibration
   - missing sensor·stale·fallback 조건 처리
3. **Scenario evaluation**
   - normal, fall, apnea/breath anomaly, elevated CO₂, no motion, sensor fault, 복합 상황
4. **Weight/logic tuning**
   - 실제 validation scenario에서만 조정
   - synthetic scenario 성공만으로 실제 fusion 개선을 주장하지 않음
5. **Learned fusion 검토**
   - rule-based baseline의 한계가 확인되고 충분한 synchronized data가 있을 때만 후보로 추가

### 필수 평가

- hazard·scenario별 recall·precision
- false alarms/hour
- event detection delay
- sensor dropout·fault 주입
- risk output과 system health 분리
- calibration·confidence reliability
- end-to-end latency

### 완료 판단

- 개별 sensor 오류가 정상 risk 0으로 바뀌지 않는다.
- 복합 상황의 개선이 개별 modality 성능 저하를 숨기지 않는다.
- learned fusion이 rule baseline보다 실제 holdout에서 일관된 이득을 보일 때만 채택한다.

---

## 8. 중간 gate와 사용자 결정 지점

| Gate | 확인 대상 | 통과 후 다음 작업 | 실패 시 |
|---|---|---|---|
| G0 | Priority 6 asset·gap 분석 | A0 | 불일치 정정 후 재시작 |
| G1 | pilot rFFT decoding·phase 타당성 | A3–A6 | reader·bin·phase rule 수정 |
| G2 | full NPZ provenance·split·integrity | B0 | model 탐색 중단, dataset 문제 수정 |
| G3 | validation 기반 finalist | Priority 12·11·14·15 | preprocessing/loss/architecture 후보 재검토 |
| G4 | Real-Data Offline Candidate | C0 existing-evidence audit | offline 한계를 보고하고 실험 cycle 재정의 |
| G5a | C0A correspondence gate | C0B exploratory inference 또는 C1 | `BLOCKED_PENDING_SIGNAL_CORRESPONDENCE` |
| G5b | C1 protocolized capture | C2 formal device-domain eval | device contract·capture 수정 |
| G5c | C2 frozen-candidate device eval | 측정된 gap이 승인된 경우만 D | 실센서 한계 유지, 자동 재학습 금지 |
| G6 | M-D 이후 MR60-adapted candidate (있을 때만) | E | 실센서 한계 유지. M-C가 이 후보를 만들지 않음 |

다음은 별도 승인·결정 지점으로 본다.

- label mapping 정책 확정
- subject split 고정
- locked test 최초 평가
- offline candidate 선정·manifest 등록
- 기존 팀 MR60 로그의 C0 forensic audit
- C0A correspondence 판정 후 탐색적 추론 여부
- MR60 사람 대상 신규 프로토콜 수집
- C2 결과로 D 진입을 승인할지
- 추가 외부 dataset 다운로드
- offline candidate를 deployment candidate로 승격할지 (M-C 자동 승격 아님. adapted candidate는 승인된 M-D만)
- learned multimodal fusion 도입

---

## 9. agent 작업 단위 권장

하나의 실행 프롬프트에 너무 많은 판단·변경을 섞지 않는다. 다음처럼 독립 작업으로 나누는 것을 권장한다.

1. A0 inventory·source identity
2. A1 safe reader·schema pilot
3. A2 range-bin·phase extraction pilot
4. A3 timestamp·window policy
5. A4 label policy 분석·결정
6. A5 subject split·provenance schema
7. A6 full conversion·integrity audit
8. B0 evaluation protocol·test lock
9. Priority 7 preprocessing ablation
10. Priority 8 imbalance
11. Priority 9 architecture
12. Priority 10 multi-seed
13. Priority 13 representative calibration
14. Priority 12 stage equivalence
15. Priority 11 robustness
16. Priority 14 latency·footprint
17. Priority 15 Mock E2E
18. Priority 16 selection
19. Priority 17 artifact lock
20. Priority 18 report
21. C0 existing team MR60 forensic audit
22. C0A signal/cadence/offline-contract correspondence gate
23. C0B exploratory legacy-device inference (optional)
24. independent review
25. C1 protocolized MR60 capture
26. C2 formal device-domain evaluation of frozen candidate
27. D dataset/model gap 확장 (승인된 측정 gap만)
28. E fusion baseline·개선

각 작업 프롬프트는 최소한 다음을 포함하도록 구체화한다.

- 정확한 목적·비목적
- 선행 산출물·입력
- 수정 허용 범위·금지 범위
- 실행 방법·실험 변수·고정 변수
- machine-readable output schema
- metric·판정 기준
- 실패·부족 evidence 표기
- lineage·checksum·provenance 요구사항
- 수행하지 않을 검증
- 완료 보고 형식

---

## 10. 최종 순서 checklist

### Phase A

- [x] A0 archive identity·inventory
- [x] A1 safe rFFT reader·pilot
- [x] A2 range-bin·phase extraction
- [x] A3 timestamp·resampling·window
- [x] A4 annotation·label mapping pilot
- [x] A5 subject split·pilot sample provenance
- [x] A6 full conversion·integrity audit

### Phase B / Priority 7–18

- [ ] B0 evaluation protocol·locked test
- [ ] Priority 7 preprocessing ablation
- [ ] Priority 8 imbalance strategy
- [ ] Priority 9 architecture comparison
- [ ] Priority 10 multi-seed stability
- [ ] Priority 13 representative calibration
- [ ] Priority 12 Float/TFLite/INT8 equivalence
- [ ] Priority 11 perturbation robustness
- [ ] Priority 14 Mac latency·footprint
- [ ] Priority 15 explicit candidate Mock E2E
- [ ] Priority 16 Real-Data Offline Candidate selection
- [ ] Priority 17 artifact·metadata·manifest lock
- [ ] Priority 18 offline validation report

### Phase C

- [ ] C0 existing team MR60 forensic audit
- [ ] C0A signal/cadence/offline-contract correspondence gate
- [ ] C0B exploratory legacy inference (optional; correspondence 통과 시에만)
- [ ] independent review
- [ ] C1 protocolized MR60 capture (신규 수집 시에만 하드웨어 가용성 gate)
- [ ] C2 formal device-domain evaluation of frozen Phase-B candidate
- [ ] measured domain gap registry (D 진입은 별도 승인)

### Phase D

- [ ] residual gap ranking
- [ ] gap-driven external dataset selection
- [ ] approval·acquisition·source audit
- [ ] external test/adaptation/retraining (승인된 M-D만; M-C 금지)

### Phase E

- [ ] synchronized multimodal evaluation data
- [ ] rule-based late-fusion baseline
- [ ] calibration·fault robustness
- [ ] scenario holdout evaluation
- [ ] learned fusion conditional comparison

---

## 11. 최종 종료 조건

전체 로드맵은 다음을 모두 충족할 때 완료로 본다.

1. Zenodo raw→canonical phase→window→label→split→model chain이 checksum·provenance와 함께 재현된다.
2. real-subject locked test에서 v0.1.0, v0.2.0, 신규 model이 동일 계약으로 비교된다.
3. preprocessing, imbalance, architecture, seed, calibration, conversion 선택의 근거가 validation 실측으로 남아 있다.
4. 최종 INT8 model의 quantization equivalence, robustness, latency, runtime 연결이 검증된다.
5. offline candidate와 가능한 이후 MR60-adapted/deployment candidate가 분리되어 있다. M-C는 frozen offline candidate를 평가하며, 그 안에서 adapted candidate로 교체하지 않는다.
6. 기존 팀 실측은 legacy/informal evidence로, C1 신규 실측과 C2 정식 평가가 정직하게 구분되어 보고된다. C1 하드웨어 부재는 `BLOCKED_HARDWARE`로 표시하되 C0을 공백 상태로 되돌리지 않는다.
7. 추가 dataset이 실제 gap을 보완하는 용도로만 통합된다.
8. multimodal fusion이 개별 sensor 오류를 숨기지 않고 실제 holdout에서 개선을 보인다.

---

# Part III — CO₂ 실제 데이터·모델 A–E 트랙

## C-A. 실제 CO₂ raw-to-canonical reconstruction

### C-A0. source identity·license·inventory

#### 목적

현재 synthetic smoke NPZ와 실제 UCI Occupancy 원본을 분리하고, 이후 모든 CO₂ sample이 실제 source row로 역추적되게 한다.

#### 세부 작업

1. 공식 source URL, DOI, license, 내려받은 파일명과 byte size를 기록한다.
2. raw 파일별 SHA-256을 streaming 방식으로 계산한다.
3. CSV header, delimiter, encoding, timestamp format, row count, feature 목록, label 목록을 inventory로 만든다.
4. duplicate row, missing value, nonfinite value, timestamp 역행, 비정상 범위를 원본별로 계수한다.
5. 기존 `datasets/build_processed_npz.py`의 synthetic fixture 생성 결과를 실제 UCI 처리 결과로 설명하지 않는다.
6. 원본 파일은 수정하지 않고 `datasets/raw_archives/` 또는 승인된 외부 storage에 read-only로 둔다.

#### 완료 판단

- source identity와 license가 명시됨
- raw 파일 전부 checksum 보유
- inventory가 실제 row에서 derive됨
- synthetic/real 계보 혼동 0건

### C-A1. safe CSV reader·schema contract

#### 목적

원본별 column 차이와 timestamp 해석을 명시적으로 처리하는 deterministic reader를 만든다.

#### 세부 작업

1. 필수 column과 optional column을 분리한다.
2. timestamp는 원본 문자열, parse 결과, timezone 검증 상태를 함께 보존한다.
3. label·feature column을 position이 아니라 이름으로 선택한다.
4. NaN/Inf, 잘못된 숫자, 결측 timestamp, 중복 header를 fail-closed 처리한다.
5. reader가 원본 row index와 source file ID를 잃지 않게 한다.
6. 소규모 pilot 파일에서 row 수·범위·label 분포를 독립 validator로 재계산한다.

### C-A2. timeline·session·group contract

#### 목적

인접한 시간 row가 train과 test에 섞이는 temporal leakage를 막는다.

#### 세부 작업

1. 연속 timestamp 구간을 session 또는 contiguous block으로 식별한다.
2. 큰 gap, 중복 timestamp, 역행을 기록하고 block 경계를 고정한다.
3. room/building/day/session 정보가 있으면 grouping evidence로 보존한다.
4. 정확한 독립 group을 원본만으로 확인할 수 없으면 `NOT_VERIFIABLE`로 표시하고 row-random split을 금지한다.
5. rolling history를 만들기 전에 group split 단위를 먼저 결정한다.

### C-A3. feature reconstruction contract

#### 목적

`[CO2_slope, Humidity, CO2]` 입력이 실제 raw measurement에서 어떻게 생성됐는지 재현한다.

#### 세부 작업

1. CO₂ ppm, humidity와 원본 sample interval을 검증한다.
2. `CO2_slope`의 window 길이, 단위 `ppm/min`, 회귀 또는 차분 계산식을 고정한다.
3. feature history가 session 경계를 넘지 않게 한다.
4. warm-up 부족 row, gap 인접 row, 센서 범위 초과 row의 포함·제외 규칙을 기록한다.
5. canonical feature는 unscaled 값으로 보존하고 scaler는 B 단계에서 TRAIN으로만 fit한다.
6. 임의 pilot row를 원본 CSV에서 canonical feature까지 수작업 역산한다.

### C-A4. label semantics·safety separation

#### 목적

공개 dataset의 occupancy label, 실제 CO₂ 농도, SafeNest 위험 상태를 서로 다른 의미로 보존한다.

#### 세부 작업

1. original occupancy label을 그대로 보존한다.
2. occupancy를 고농도 위험 또는 사람 안전 상태와 동일시하지 않는다.
3. `CO2 > 1500 ppm` 같은 rule-based safety threshold는 모델 label과 분리된 risk rule로 관리한다.
4. label source, mapping type, mapping rule ID와 assignment status를 sample provenance에 둔다.
5. 불확실하거나 label이 없는 row는 억지로 NORMAL로 만들지 않는다.

### C-A5. group-wise split·sample provenance

#### 목적

시간적으로 이어진 row와 history window가 여러 split에 섞이지 않게 한다.

#### 세부 작업

1. A2에서 승인된 room/session/day/block 중 가장 강한 독립 단위를 split group으로 사용한다.
2. 같은 group의 모든 row와 window를 TRAIN, VALIDATION, LOCKED_TEST 중 하나에만 둔다.
3. seed, hash assignment rule, group 목록과 split 비율을 manifest로 고정한다.
4. label·농도 범위·session 길이의 split 분포를 보고하되 LOCKED_TEST를 최적화에 사용하지 않는다.
5. sample마다 source file, row, timestamp, group, feature profile, label, split, quality를 보존한다.

### C-A6. full conversion·integrity audit

#### 목적

전체 실제 CO₂ 원본을 canonical feature dataset으로 변환하고 C-B 진입 여부를 결정한다.

#### 세부 작업

1. 전체 row/session 처리 성공·경고·실패·제외를 기록한다.
2. NaN/Inf, constant feature, 범위 이상, timestamp gap, duplicate와 cross-split leakage를 감사한다.
3. canonical numeric artifact와 provenance를 1:1 검증한다.
4. raw archive와 output manifest checksum을 고정한다.
5. 여러 source file과 split에서 deterministic lineage spot check를 수행한다.
6. standalone C-A6 validator가 모든 필수 artifact와 split inheritance를 검사한다.

#### C-A 종료 기준

- 실제 raw→feature→label→split chain 재현 가능
- temporal/group leakage 0건
- synthetic fixture와 실제 canonical artifact 분리
- 모든 제외·실패에 이유 존재
- LOCKED_TEST training eligibility 0건

## C-B. CO₂ offline model comparison

### C-B0. evaluation protocol·baseline lock

- primary metric: macro F1과 occupied recall
- secondary metric: precision, specificity, calibration, confusion matrix
- 농도 구간·session별 error slice를 사전 정의
- rule baseline, logistic regression, tree/boosting baseline, 현재 TFLite를 같은 split로 비교
- LOCKED_TEST 실행 횟수와 접근 주체 기록

### C-B1. preprocessing·history ablation

- raw CO₂/humidity와 slope 조합 비교
- history 길이와 slope 계산법 비교
- missing/gap 처리 비교
- 모든 scaler·imputer는 TRAIN에서만 fit
- validation protocol 고정 후 한 요소씩 비교

### C-B2. imbalance·calibration

- class weight, balanced sampling, threshold calibration을 분리 비교
- threshold는 VALIDATION에서만 선택
- false-negative와 false-positive 비용을 모두 보고
- occupancy probability와 CO₂ safety rule을 별도 출력으로 유지

### C-B3. architecture·multi-seed

- linear/MLP/tree 계열과 TinyML 후보를 공정 비교
- 입력 feature와 split, seed set, stopping rule을 고정
- 최소 3개 seed의 평균·표준편차와 worst seed 기록
- 단일 최고 seed만으로 후보를 선택하지 않음

### C-B4. Float→TFLite→INT8 equivalence

- 대표 dataset은 TRAIN에서만 구성
- float model, float TFLite, INT8의 동일 sample prediction을 비교
- macro F1, occupied recall, probability drift, input saturation을 기록
- 변환 artifact·scaler·class map·metadata checksum 고정

### C-B5. robustness·latency·candidate lock

- ppm offset/drift, humidity noise, missing row, stale history, timestamp jitter 시험
- Mac latency는 기술 sanity check로만 기록
- 최종 locked-test 평가는 model·threshold·artifact 확정 뒤 한 번 수행
- offline candidate와 SCD40 deployment candidate를 분리

### C-B6. Reduced-Feature Candidate Development and Lock

`C-B6` is a separate offline model-development phase created by the 2026-08-15 final input decision. It is not a C-C device-domain phase, does not authorize physical acquisition, and does not modify the current B5 artifact.

#### C-B6 entry and interpretation boundary

The decision that leads to C-B6 is a **system-contract burden-of-proof decision**, not a claim that the reduced-feature model outperformed the four-feature model:

```text
FOUR_FEATURE_PREDICTIVE_BENEFIT_OBSERVED: YES
REDUCED_FEATURE_PREDICTIVE_SUPERIORITY: NO
OCCUPIED_RECALL_ADVANTAGE_AT_0_58: YES
OCCUPIED_RECALL_ADVANTAGE_THRESHOLD_CONDITIONED: YES
DECISION_BASIS: SYSTEM_CONTRACT_BURDEN_OF_PROOF
```

The four-feature arm showed modest, repeatable offline predictive advantages across most aggregate and probability-quality metrics. The reduced arm showed higher occupied recall at the inherited `0.58` threshold, but that comparison is threshold-conditioned. The threshold came from the current four-feature B5 lineage; it does not establish inherent reduced-feature recall superiority.

#### C-B6 required candidate contract

| Item | C-B6 requirement |
|---|---|
| Input | `CO2`, `CO2_slope` |
| Slope | existing `ENDPOINT_H150`; no slope redesign in C-B6 unless separately authorized |
| Scaler | new scaler fit on TRAIN-only rows for the two-feature subset |
| Model | newly trained two-feature candidate with new coefficients |
| Metadata | new feature/model/threshold/quantization metadata |
| Artifact identity | new Float, TFLite, INT8 artifacts and checksum coverage |
| Quantization | new INT8 calibration and Float→TFLite→INT8 equivalence evidence |
| Threshold | own predeclared threshold-selection procedure before final evaluation |
| Validation | new candidate validation evidence with prior VALIDATION use acknowledged |
| Lock | new candidate lock binding model, scaler, feature order, threshold, metadata, and checksums |

The following inheritance is forbidden:

```text
B5_THRESHOLD_0_58_INHERITANCE_TO_REDUCED_MODEL = FORBIDDEN
```

The future threshold must not be copied from B5 automatically. A permitted development procedure may use TRAIN-only internal cross-validation or an internal development split. The existing VALIDATION population may continue to provide development-validation evidence, but it is not an untouched final test after prior feature/model decisions. The old `LOCKED_TEST` must not be reused for feature selection, threshold selection, model selection, or a new unbiased held-out claim.

#### C-B6 prohibitions and exit gate

C-B6 must not:

- remove columns from B5 in place;
- reuse the four-feature scaler;
- reuse B5 threshold `0.58` automatically;
- overwrite B5 model, scaler, metadata, or lock artifacts;
- use `LOCKED_TEST` for feature, threshold, or model selection;
- start physical acquisition or C-C2.

C-B6 exits only when the new two-feature candidate, its TRAIN-only scaler, own threshold policy, conversion/quantization evidence, validation evidence, metadata, checksums, and candidate lock all pass a focused validator. Only then may a revised C-C1 protocol and operator prompt be authored.

#### C-B6 execution result (2026-08-15)

The executed candidate is:

```text
CANDIDATE_ID: C_B6_REDUCED_CO2_SLOPE_CANDIDATE_001
FEATURE_ORDER: CO2 + CO2_slope
FINAL_THRESHOLD: 0.43
THRESHOLD_SOURCE: TRAIN_INTERNAL_ONLY
B5_THRESHOLD_0_58_INHERITED: NO
C_B6_STATUS: C_B6_PASS_WITH_LIMITATIONS
INT8_EQUIVALENCE_GATE: PASS
CO2_SLOPE_INT8_SATURATION: OBSERVED_LIMITATION
B5_MODIFIED: NO
LOCKED_TEST_PREDICTIVE_ACCESS: NO
PHYSICAL_ACQUISITION: HOLD
```

The C-B6 focused validator passes and the new candidate lock is complete, but
the observed CO2_slope INT8 input saturation must be carried into C-C2. C-C1R
has frozen the successor protocol, but the operator guide is not distributable
until the current acquisition tooling supplies the required fresh-event and
session evidence. C-B6 and C-C1R do not authorize physical acquisition or
`C-C2` while that tooling blocker remains.

## C-C. SCD40 legacy evidence → final input decision → controlled device-domain validation

C-C는 단일 “SCD40 로그에 모델 실행” 단계가 아니다. 실제 팀 evidence audit(`C-C0`), historical four-feature protocol freeze(`C-C1`), final model-input decision, 별도 model phase(`C-B6`) reduced-feature candidate lock, revised protocol/operator handoff, 외부 protocol-controlled acquisition, later controlled intake/formal validation(`C-C2`)을 분리한다. C-C0/C-C1과 final decision audit에서 현재 frozen C-B5 후보는 변경하지 않는다. C-C에서 발견한 domain mismatch나 입력 방향성 결과는 threshold 재튜닝·C-D 자동 진입을 허가하지 않는다.

현재 locked offline 정체성의 권위는 프롬프트 숫자나 이 문서의 관측 예시가 아니다. 실행 에이전트는 live origin/main의 machine-readable C-B5 lock을 읽고 checksum을 검증한 뒤에만 `FROZEN_B5_IDENTITY_VERIFIED = PASS`를 줄 수 있다. 아래에 적힌 candidate ID·threshold·scale 등은 작성 시점 관측 예시일 뿐이다.

#### Verified C-C0 input snapshot (read-only team evidence)

이번 roadmap revision의 legacy 입력은 team repository `main` `fdf34b804f35e5868356f0ed6f804a248aa69131`에 병합된 PR #14 (`ea925e4f3fae244d8ef4c5bd312b8e6619242767`)의 Git-tracked files다. 아래 SHA-256은 raw CSV 현재 bytes를 다시 계산한 값이며, team이 함께 커밋한 summary JSON과 report에 적힌 이전 SHA-256과 일치하지 않는다. C-C0는 raw bytes를 source of truth로 삼고 derived summary를 재검산 대상으로 남긴다.

| raw source (team repository-relative) | rows | capture-valid | invalid state | current raw SHA-256 |
|---|---:|---:|---|---|
| `devices/co2/firmware/logs/2026-08-12_preflight_30s.csv` | 30 | 30 | none | `e414be88d5b246411143b7353493565f8fea95bd6fd7f8120804c478f89c41fb` |
| `devices/co2/firmware/logs/2026-08-12_baseline_5min.csv` | 300 | 277 | `14 NOT_CONNECTED`, `9 STALE` | `f9fee44ef154bc03ff2c3e0704b3b2c9732841b8510656585b4e7ed9226b6357` |
| `devices/co2/firmware/logs/2026-08-12_baseline_attempt02_5min.csv` | 300 | 300 | none | `741e9a48b77bd8c8a4bbff31f795b1b66f748e8e3dcb36efa2b3470ef60e4d4f` |
| `devices/co2/firmware/logs/2026-08-12_breath-rise-recovery_6min.csv` | 360 | 329 | `16 NOT_CONNECTED`, `15 STALE` | `b9d01bb96aedd0df68e4f13a8ae2d4512f67e64d359a44a1c4c8c2642d110b32` |

Verified aggregate: `990` capture rows, `936` capture-valid rows, `54` transport-invalid rows. Valid CO₂ ranges are `495–1493 ppm` across the selected files. All 990 nested `raw_response_json` objects parse, contain a numeric cached `co2_ppm`, and report `valid.co2=true`; the 54 CSV-invalid rows are invalid because the capture contract also requires Pi transport `connected=true` and `fresh=true`. This is direct evidence that a cached CO₂ value can remain present while transport freshness has failed.

The trace confirms a real SCD40/SCD4x I²C producer path and a real ESP32→Pi→`/health` path, but the physical SCD40 serial/unique identity is not recorded. The captured `/health` payload and CSV have no Temperature or Humidity fields, including no nested T/RH fields. The ESP32 producer reads T/RH into local variables and then drops them from `TelemetrySnapshot` and telemetry JSON; `SensorStore` and `capture_scd40.py` therefore cannot recover them. Scenario names (`preflight`, `baseline`, `breath-rise-recovery`) are collection context, not independent VACANT/OCCUPIED ground truth.

The lineage source set is `devices/co2/firmware/capture_scd40.py`, `display-test2/esp32_sensor_node/esp32_sensor_node.ino`, `display-test2/raspberry_pi_lcd/server.py`, `display-test2/docs/COMMUNICATION_PROTOCOL.md`, the four CSVs, and `devices/co2/docs/VERIFICATION_REPORT_2026-08-12.md`. The producer's `co2Valid` is a 15-second last-successful-read freshness flag; the Pi server's `fresh` is a five-second last-telemetry-receipt flag. Neither is a per-measurement event timestamp.

### C-C0. Existing team SCD40 evidence forensic audit

상태 라벨: `EXPLORATORY_EXISTING_TEAM_MEASUREMENT` / `LEGACY_OR_INFORMAL_DEVICE_EVIDENCE`. `FORMAL_DEVICE_VALIDATION_SET`이 아니다.

개념 순서:

```
1. LEGACY PAYLOAD DISCOVERY
        ↓
2. SCD40 DEVICE IDENTITY
        ↓
3. ACQUISITION / PRODUCER LINEAGE
        ↓
4. LOGGER vs TRANSPORT vs SENSOR FRESHNESS AUDIT
        ↓
5. SCHEMA / UNIT AUDIT
        ↓
6. FROZEN FEATURE VECTOR COMPLETENESS
   CO2 / Temperature / Humidity availability
        ↓
7. FEATURE SEMANTIC CORRESPONDENCE
        ↓
8. ENDPOINT_H150 RECONSTRUCTION
        ↓
9. FROZEN_B5_IDENTITY_VERIFIED
        ↓
10. PRE-INFERENCE CORRESPONDENCE GATE
        ↓
11. 가능한 경우에만
    EXPLORATORY_LEGACY_DEVICE_INFERENCE
        ↓
12. scaler/domain/INT8/output diagnostics
        ↓
13. GROUND-TRUTH GATE
        ↓
14. C-C1 measurement-gap → protocol specification
        ↓
STOP
```

#### Fail-closed: logger code ≠ 측정 데이터

로거/캡처 코드가 있어도 실제 측정 payload가 없으면 `NOT_AVAILABLE`이다. 코드를 근거로 실측이 있다고 추정하지 않는다. 원본 payload를 읽을 수 없으면 C-C0는 fail-closed로 해당 세션을 차단한다.

#### Logger vs transport vs sensor freshness (필수)

팀 수집기는 SCD40에 직접 I²C 접근하는 logger가 아니다. `devices/co2/firmware/capture_scd40.py`는 Raspberry Pi `/health` HTTP endpoint를 기본 1초마다 polling한다. 현재 ESP32 producer는 `startPeriodicMeasurement()`를 사용하고 약 5초 첫 측정을 예상하는 코드 주석을 갖지만, legacy payload에는 SCD40 data-ready event나 measurement timestamp가 없다. low-power mode, configured interval, and actual sensor-refresh cadence는 이 evidence에서 주장하지 않는다.

세 분류로는 부족하다. 네 층을 분리한다.

```
LOGGER_POLL_CADENCE
        ↓
Pi capture_scd40.py의 HTTP polling 주기

TRANSPORT_TELEMETRY_CADENCE
        ↓
ESP32 → Pi telemetry update 주기

TRANSPORT_FRESHNESS
        ↓
/health의 fresh / age_seconds semantics

SCD40_FRESH_MEASUREMENT_CADENCE
        ↓
센서 자체에서 새로운 CO2/T/RH measurement가 생성된 시점
```

`TRANSPORT_FRESHNESS != SCD40_FRESH_MEASUREMENT_FRESHNESS`

capture code의 `fresh = sensors.get("fresh") is True`는 Pi가 ESP32 telemetry를 얼마나 최근에 받았는지의 runtime/transport freshness다. Pi `SensorStore`는 마지막 telemetry packet 수신 시각으로 `age_seconds`/`fresh`를 계산한다. `fresh == true`만으로 `NEW_SCD40_MEASUREMENT == true`라고 하지 않는다. `seq`나 `uptime_ms`가 변해도 ESP packet이 새롭다는 뜻일 뿐, 그 안의 SCD40 측정값 자체가 새로 갱신됐는지는 증명하지 않는다. 반대로 ESP `valid.co2`는 마지막 성공한 SCD4x read가 15초 stale limit 안에 있다는 flag이지 신규 measurement marker가 아니다.

The C-C0 agent must trace the ESP32 SCD40 producer implementation and classify each telemetry packet as a packet event, not automatically as a newly completed SCD40 measurement. The current producer stores only the latest CO₂ value, so repeated/cache behavior remains possible and must be preserved in the evidence interpretation.

`ENDPOINT_H150` 재구성은 logged row 개수나 `fresh == true` row 개수가 아니라 chronological **SCD40 fresh measurement** semantics를 사용한다. 현재 legacy data에는 그 semantics가 없으므로 host-clock/CO₂ endpoint 계산은 `NOMINAL_CADENCE_DIAGNOSTIC_ONLY`로 분류한다. stale/disconnect boundary를 넘지 않고 계산한 diagnostic slope도 frozen B5-compatible `CO2_slope`로 승격하지 않는다.

#### Rawness taxonomy

인간적으로 “SCD40 raw data”라고 불러도, machine-readable evidence에서는 `TRUE_SENSOR_RAW_SIGNAL`을 쓰지 않는다. `read_measurement`가 주는 CO2 ppm / Temperature / Relative Humidity는 센서 내부 처리와 conversion을 거친 device output이다. ADC/photoacoustic 내부 원시 신호를 팀이 받지 않는다.

| 분류 | 의미 |
|---|---|
| `IMMUTABLE_ACQUISITION_PAYLOAD` | 수집 직후 보존된 불변 payload |
| `LOWEST_EXPOSED_SCD40_MEASUREMENT` | 장치가 외부로 내보내는 최저 수준 측정값 |
| `TEAM_DERIVED_OR_CACHED_OUTPUT` | 팀 필터, 반복 전달, 캐시, 파생값 |
| `MODEL_READY_FEATURE` | C-B5 feature 계약까지 변환된 입력 |
| `UNKNOWN` | producer lineage 미확인 |

SCD40 `readMeasurement`가 반환한 CO₂/T/RH는 센서 내부 처리와 conversion을 거친 device output이다. 현재 team CSV의 `raw_response_json`은 transport payload를 보존하지만, producer가 T/RH를 telemetry에 넣지 않았으므로 실제 captured evidence의 exposed sensor measurement는 cached/transported `co2_ppm`뿐이다. Git-tracked raw CSV는 `IMMUTABLE_ACQUISITION_PAYLOAD` 후보로 보존하되, derived-summary SHA mismatch 때문에 C-C0 provenance status는 raw bytes `VERIFIED`, derived summaries `STALE_OR_MISMATCHED`로 분리한다.

#### Frozen feature-vector completeness gate (필수)

Frozen B5 입력 계약은 네 feature다.

```
CO2
Temperature
Humidity
CO2_slope
```

팀 `capture_scd40.py` CSV의 독립 sensor column은 `co2_ppm` 하나다. 나머지 필드는 host/transport 메타와 `raw_response_json`이다. C-C0는 `/health` producer code와 실제 raw JSON을 모두 추적한 뒤, 이 legacy set에 T/RH가 없음을 `NO`로 판정한다. producer source에 T/RH local variables가 있다는 사실은 captured T/RH evidence가 아니다.

H150 reconstruction 가능과 B5 feature vector construction 가능은 다른 판정이다.

```
B5 inference requires reproducible availability of all frozen input
features; H150 reconstructability alone does not authorize inference.
```

`FROZEN_FEATURE_VECTOR_COMPLETENESS` gate:

```
CO2 available:
YES / NO

Temperature available:
YES / NO / ONLY_IN_RAW_RESPONSE / UNKNOWN

Humidity available:
YES / NO / ONLY_IN_RAW_RESPONSE / UNKNOWN

CO2_slope reconstructable:
YES / NO / UNKNOWN

All four frozen features reproducibly constructable:
YES / NO

Decision:
FULL_B5_INPUT_AVAILABLE
또는
B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE
```

`ONLY_IN_RAW_RESPONSE`는 존재 단서일 뿐, 재현 가능한 B5 입력으로 승격된 상태가 아니다. 네 feature가 재현 가능하게 구성되지 않으면 H150이 되어도 레거시 B5 추론은 `B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE`다.

이번 verified legacy set에 대한 C-C0 feature outcome은 `CO2=YES`, `Temperature=NO`, `Humidity=NO`, `CO2_slope=DIAGNOSTIC_ONLY`, `ALL_FOUR_FROZEN_FEATURES_REPRODUCIBLY_CONSTRUCTABLE=NO`; 따라서 `B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE`다. C-C0는 이 blocked result를 성공적인 evidence-audit result로 보존하고, missing T/RH·sensor freshness marker·session/ground-truth metadata를 C-C1 protocol gap으로 전달한다.

#### Unit audit와 semantic correspondence는 별개

단위 감사(ppm, °C, %RH)는 필요하지만, 단위가 같다고 B5 feature correspondence가 성립하지 않는다.

`same unit != same sensor semantics`

UCI Temperature/Humidity는 공개 occupancy dataset의 실내 온습도 계열이다. SCD40 T/RH는 센서 on-chip 측정/보정 출력이며, enclosure self-heating·airflow에 따라 temperature offset 설정이 T/RH 품질을 바꾼다. scaler 이탈의 원인이 장소 domain shift일 수도 있고, 센서 source semantics 차이일 수도 있다.

별도 gate (`YES` / `NO` / `UNKNOWN`):

```
CO2 semantic correspondence
Temperature semantic correspondence
Humidity semantic correspondence
CO2_slope temporal correspondence
```

이번 legacy evidence의 pre-inference outcome은 `CO2=PARTIAL` (same quantity/unit, device-domain behavior unvalidated), `Temperature=UNKNOWN`, `Humidity=UNKNOWN`, `CO2_slope=UNKNOWN`이다. T/RH capture availability는 `NO`지만, payload가 없으므로 semantic correspondence는 `UNKNOWN`/`NOT_ASSESSABLE`로 분리한다. `GROUND_TRUTH_ABSENT`이므로 occupancy performance metric은 차단한다. `baseline` 또는 `breath-rise-recovery` filename, CO₂ concentration, CO₂ slope, PIR motion, or a model output을 VACANT/OCCUPIED ground truth로 재해석하지 않는다.

#### Frozen B5 identity gate

프롬프트 값과 이 로드맵의 관측 예시는 authority가 아니다. 실제 실행은 다음만 따른다.

```
live origin/main
→ current machine-readable B5 lock
→ checksum verification
→ FROZEN_B5_IDENTITY_VERIFIED = PASS
```

The current authority is the live C-B5 lock under `datasets/co2/manifests/c_b5_robustness_final_lock/` plus `models/co2/candidates/c_b5/final_candidate_metadata.json`; the historical three-input `models/model_manifest.json` entry is not the C-B5 lock. Verify the candidate metadata, scaler evidence, TFLite bytes, feature order, slope profile, threshold, and input/output quantization as one identity set.

실행 전 live lock에서 고정할 필드:

```
candidate ID
TFLite path
TFLite SHA-256
scaler path
scaler SHA-256
feature-order contract
threshold
input quantization scale
input quantization zero-point
predecessor evidence IDs
```

작성 시점 관측 예시(authority 아님): `CO2_B5_FINAL_OFFLINE_UCI_CANDIDATE_001`, threshold `0.58`, INT8 input scale `0.03529411926865578`, zero-point `0`. `FROZEN_B5_IDENTITY_VERIFIED != PASS`이면 레거시 추론을 차단한다. C-C0는 B5 재튜닝, architecture 재선택, threshold 변경, scaler 재적합을 하지 않는다.

#### Pre-inference device correspondence gate

`ENDPOINT_H150`이 만들어졌다고 바로 모델 실행으로 넘어가지 않는다. feature completeness와 B5 identity를 포함한 명시적 판정이 필요하다.

```
feature_vector_completeness: FULL_B5_INPUT_AVAILABLE / B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE
signal_or_feature_semantic_correspondence: YES / NO / UNKNOWN
fresh_cadence_correspondence: YES / NO / UNKNOWN
h150_reconstruction_correspondence: YES / NO / UNKNOWN
tensor_construction_reproducible: YES / NO / UNKNOWN
frozen_b5_identity_verified: PASS / FAIL
decision:
AUTHORIZED_FOR_EXPLORATORY_INFERENCE
또는
BLOCKED_PENDING_SIGNAL_CORRESPONDENCE
또는
B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE
```

#### Exploratory inference와 ground-truth gate

탐색 추론은 optional이다. 신뢰할 수 있는 독립 occupancy/presence 라벨이 없으면 정식 accuracy/F1을 계산·홍보하지 않는다. 다음으로 occupancy ground truth를 만들지 않는다.

```
CO2 concentration
CO2 slope
model prediction
```

`model predicts VACANT → 이 장소의 vacant baseline` 순환도 금지한다. ground truth가 없으면 output behavior·분포·scaler/INT8 saturation만 보고한다.

### C-C0 exit boundary

C-C0는 모델 성능이 아니라 legacy evidence characterization이 완료되면 끝난다. 이 verified legacy set의 exit record는 다음과 같다.

```
REAL_DEVICE_SOURCE: VERIFIED
SCD40_MODEL_IDENTITY: VERIFIED_AT_MODEL_CLAIM_LEVEL
UNIQUE_DEVICE_IDENTITY: UNKNOWN
RAW_IMMUTABILITY: PARTIAL (raw Git bytes preserved; derived-summary SHA mismatch)
TIMESTAMP_CONTRACT: PARTIAL (Pi host clocks; no SCD40 measurement timestamp)
LOGGER_POLL_CADENCE: VERIFIED
TRANSPORT_FRESHNESS: VERIFIED
SCD40_FRESH_MEASUREMENT_CADENCE: UNKNOWN
UNIT_CONTRACT: PARTIAL (CO2 only in captured payload)
SESSION_BOUNDARIES: PARTIAL
FEATURE_VECTOR_COMPLETENESS: INSUFFICIENT
FEATURE_SEMANTIC_CORRESPONDENCE: PARTIAL / BLOCKED
OCCUPANCY_GROUND_TRUTH: ABSENT
ENDPOINT_H150_RECONSTRUCTION: DIAGNOSTIC_ONLY
FROZEN_B5_INFERENCE: BLOCKED_FEATURE_INCOMPLETE
FORMAL_DEVICE_DOMAIN_VALIDATION: NO
```

C-C0 may report CO₂ range/distribution, host logger cadence, ESP packet cadence, Pi transport freshness, stale/disconnect behavior, producer lineage, rawness, and measurement gaps. It must not report occupancy accuracy/precision/recall/F1, formal SCD40 validation, or a true vacant baseline. This blocked result is a successful evidence-audit result and becomes the input to C-C1.

### Final pre-acquisition model-input decision (2026-08-15)

The pre-acquisition decision audit is recorded in:

- result: `datasets/co2/manifests/c_c1_model_input_decision/model_input_decision_result.json`
- report: `docs/reports/20260815_SafeNest_CO2_Pre_Acquisition_Model_Input_Decision_Audit_01.md`
- audit implementation: `scripts/audit_co2_model_input_final_decision.py`

It compared only the two final candidates below, using the existing TRAIN/VALIDATION lineage and leaving `LOCKED_TEST` sealed:

```text
A: CO2 + Temperature + Humidity + CO2_slope
B: CO2 + CO2_slope
```

The model family, `ENDPOINT_H150`, past-only chronology, 0.58 threshold, imbalance procedure, and split were held fixed. Each arm fit its own scaler on original TRAIN rows only. Five seeds (`20260810`–`20260814`) and 2,000 paired validation-row bootstrap replicates were declared before the new results were consumed.

Observed directional evidence:

- A was better in accuracy, Macro F1, and occupied precision in `5/5` seeds.
- B was better in occupied recall in `5/5` seeds; the aggregate paired recall delta was negative and its 95% percentile interval was `[-0.019813, -0.006048]`.
- A was better in PR-AUC, ROC-AUC, Brier score, and log loss in all five seeds when each metric's correct direction is applied. Brier score and log loss are lower-is-better metrics.
- The aggregate paired bootstrap lower bounds were positive for accuracy (`0.003156`), Macro F1 (`0.002622`), and occupied precision (`0.015862`), but not for occupied recall.
- `LOCKED_TEST` feature/target rows decoded: `0`; predictive metrics: `0`.

The predeclared burden-of-proof rule therefore selects:

```text
FINAL_INPUT_DECISION: ADOPT_REDUCED_FEATURE_DIRECTION
FUTURE_MODEL_INPUT_DIRECTION: CO2 + CO2_slope
PHYSICAL_ACQUISITION_STATUS: HOLD_PENDING_REDUCED_FEATURE_CANDIDATE_LOCK
OPERATOR_GUIDE_HANDOFF: HOLD
```

This is not a claim that Temperature/Humidity contain zero information, nor a statistical-significance or practical-equivalence claim. It means the current evidence does not justify making T/RH mandatory fields for the next acquisition contract. The current B5 four-feature artifact, scaler, threshold, and C-C1 four-feature protocol remain unchanged and are retained as historical evidence. The four-feature arm has `FOUR_FEATURE_PREDICTIVE_BENEFIT_OBSERVED = YES`; the reduced arm has `REDUCED_FEATURE_PREDICTIVE_SUPERIORITY = NO`.

#### C-B6 gate before physical acquisition

The reduced direction is not an instruction to delete T/RH from B5 or to start collecting two-feature device data immediately. `C-B6` must complete before any physical acquisition:

1. A separately authorized `C-B6` model-development task must train and validate a new `CO2 + CO2_slope` candidate using a new TRAIN-only scaler, explicit metadata, model/TFLite artifacts, checksums, and a new lock record.
2. The candidate must preserve the existing subject/split and past-only `ENDPOINT_H150` chronology, define its own threshold-selection policy, and acknowledge that the current VALIDATION set has prior decision use. The old `LOCKED_TEST` cannot be reused for feature, threshold, or model selection or claimed as a new unbiased held-out test.
3. Only after the reduced candidate is validated and locked may a revised C-C1 protocol and operator prompt be created. That revised contract must state the reduced feature fields, fresh-event cadence, H150 reset rule, threshold identity, and independent ground-truth requirements.
4. Until then, external protocol-controlled acquisition is `HOLD`; the existing four-feature operator prompt is historical evidence and must not be distributed for collection.

The current four-feature C-C1 machine-readable protocol remains version `1.0.0` with its original required fields. Its post-decision hold status is recorded separately in `post_c_c1_model_input_decision`; this does not silently mutate the historical four-feature B5 contract.

### C-C1. Measurement protocol freeze & operator handoff

C-C1은 레거시 분석과 분리된 **historical four-feature measurement protocol freeze**다. C-C0에서 발견한 gap이 프로토콜을 정한다. C-C1은 formal validation, model evaluation, 즉시 AI 소비 단계가 아니며 protocol과 operator prompt를 freeze한 뒤 멈춘다. 2026-08-15 final input decision 이후 이 four-feature handoff는 `HOLD`이며, reduced candidate lock 뒤에만 새 protocol revision을 만든다.

#### C-C1 required artifacts

1. A machine-readable/documented protocol, for example `CO2_C_C1_MEASUREMENT_PROTOCOL_001`, with version, owner, schema, required fields, deviation policy, and checksum policy.
2. An independently executable operator prompt that can be followed without the AI development agent.

The protocol retains only fields justified by C-C0, the frozen B5 contract, SCD40 behavior, and later formal validation needs. At minimum it must decide how to preserve:

```
session_id, location_id, scenario_id, protocol_version
SCD40 model claim, unique sensor identity or explicit UNKNOWN, ESP device_id
sensor measurement timestamp or sensor-fresh measurement marker
telemetry seq/uptime, Pi receipt timestamp, host logger timestamp, transport age/freshness
CO2, Temperature, Relative Humidity, per-field validity, sensor error
measurement_mode, configured measurement interval, ASC state
temperature_offset, altitude compensation, ambient pressure compensation
FRC history if known, power-cycle state, firmware/library versions
independent VACANT/OCCUPIED ground-truth value, source, and synchronized timestamp
entry/exit timing, ventilation/door/window condition where relevant
immutable raw payload, per-session source checksum, session manifest/checksum
```

Unknown or inaccessible calibration/configuration values remain explicitly `UNKNOWN`; they are never filled with defaults. The protocol preserves missing, stale, disconnect, invalid, out-of-range, restart, and logger/transport failure observations. It must not silently convert cached CO₂ into a new measurement or delete failed rows.

The operator prompt specifies the exact hardware connection, firmware/library/code version, fixed sensor settings, session-ID procedure, clocks and freshness fields to log, independent ground-truth procedure, controlled vacant/occupied entry/exit and ventilation scenarios, warm-up and duration rules, failure handling, immutable storage location, checksum generation, no-manual-edit rule, and the summary/deviation report to return. Physical measurement is outside this roadmap revision.

`calibration_state` 한 필드로 끝내지 않는다. 최소한 다음을 분리한다.

```
measurement_mode
asc_enabled
temperature_offset
altitude_compensation
ambient_pressure_compensation
frc_history_if_known
power_cycle_state
```

ASC는 일정 기간 실제 대기 수준 CO₂ 노출을 가정하므로, 실험실/밀폐환경의 장기간 device behavior 해석에 관련된다. temperature offset은 enclosure 조건에 따라 T/RH 품질을 바꾼다.

`SCD40_REAL_SENSOR_VALIDATED` 또는 상응하는 deployment 상태는 C-C1에서 부여하지 않는다. C-C1은 protocol freeze와 historical handoff artifact 보존에서 멈추며, 현재는 reduced candidate lock과 revised protocol authorization을 기다린다.

### C-C1R. Reduced-Feature Measurement Protocol Revision and Operator Handoff (protocol frozen; handoff blocked)

`C-C1R` produced and froze `CO2_C_C1R_REDUCED_MEASUREMENT_PROTOCOL_001` and
the Korean operator guide draft. The protocol is bound to
`C_B6_REDUCED_CO2_SLOPE_CANDIDATE_001`, feature order `CO2 + CO2_slope`,
threshold `0.43`, `TRAIN_INTERNAL_ONLY` threshold provenance, and the
`ENDPOINT_H150` freshness chronology contract. It preserves the nominal
60-second effective model-input/export cadence separately from native SCD40
behavior, forbids stale reuse/synthetic fill, requires independent
VACANT/OCCUPIED ground truth, and requires immutable raw/session/checksum
evidence before a later C-C2 intake.

The C-B6 `CO2_slope` INT8 saturation remains a known non-blocking limitation
for device-domain observation; C-C2 must measure and report its real-device
rate/effect. The current team capture path was inspected read-only at team main
`3d86bf2a7a4e527d7aba2dfabcb087201ffeb46e` and does not yet provide a verified
fresh SCD40 event marker/chronology or protocol/session/candidate manifest.
Therefore the protocol is frozen but `OPERATOR_GUIDE_HANDOFF` and
`PHYSICAL_ACQUISITION` remain `HOLD` with
`OPERATOR_HANDOFF_BLOCKED_BY_ACQUISITION_TOOLING`. C-C1R did not modify team
code, C-B6 artifacts, or start C-C2.

### C-C1T. Acquisition tooling readiness and pre-collection compliance gate (2026-08-15)

`C-C1T` inspected the actual ESP32 SCD40 producer and the Raspberry Pi
pass-through before any physical collection. The producer calls
`getDataReadyStatus()` and only accepts a value after successful
`readMeasurement()`, but the former telemetry contract exposed only packet
`seq`, `co2Valid`, and the cached CO₂ value. Packet sequence and Pi receipt
freshness therefore could not prove a new SCD40 measurement event.

The minimum producer-side observability correction is isolated in team PR #19:

```text
repository: jinsu1011/safenest-embedded-competition
team main base: 3d86bf2a7a4e527d7aba2dfabcb087201ffeb46e
feature branch: feature/C-C1T-co2-fresh-event-observability
feature commit: a7db03e6d7c65e91c52839e7b337c0886fa3431a
PR: #19 OPEN
```

The change exposes `co2_measurement_event_id`,
`co2_measurement_monotonic_ms`, and `co2_measurement_event_valid` only after
an accepted SCD40 read, and passes them through the Pi state. It does not
modify the AI model, scaler, threshold, feature order, or runtime decision
logic. The PR has not been merged or deployed in this task.

Standalone C-C1T tooling is recorded in
`datasets/co2/manifests/c_c1t_acquisition_tooling/capture_contract.json` and
implemented by `scripts/capture_co2_c_c1t_session.py`. It preserves raw
payloads before preprocessing, distinguishes `FRESH_EVENT` from
`CACHED_RETRANSMISSION`, records missing/transport failures, writes
independent ground-truth events, and finalizes a per-session SHA-256 bundle.
The precollection validator is
`scripts/validate_co2_c_c1t_precollection.py`; its deterministic fixture
contains two fresh events and one retransmission and passes the bundle
validator. The 60-second effective model-input/export cadence remains
explicitly declared and separate from logger polling and native SCD40
cadence.

The current C-C1T result is:

```text
C_C1T: C_C1T_BLOCKED
TOOLING_CONTRACT: PASS
DRY_RUN_BUNDLE: PASS
TEAM_PRODUCER_CHANGE: IMPLEMENTED_ON_FEATURE_BRANCH_ONLY
TEAM_PR: #19 OPEN
TEAM_MAIN_DEPLOYMENT: NO
OPERATOR_GUIDE_HANDOFF: HOLD_PENDING_TEAM_PRODUCER_PR_MERGE_AND_DEPLOYMENT
PHYSICAL_ACQUISITION: HOLD
C-C2: NOT_STARTED
C-D: NOT_AUTHORIZED
```

Opening the team PR does not authorize physical acquisition. After explicit
review and merge/deploy of the team producer change, C-C1T must be rerun
against the deployed path before the operator guide can become `READY`.

#### C-C1T human handoff: two evidence levels

The formal C-C1T gate remains blocked on deployed producer fresh-event
observability, but this must not be interpreted as a ban on every real-device
observation. The current handoff has two separate statuses:

```text
EXPLORATORY_OPERATOR_HANDOFF: READY_FOR_HANDOFF
EXPLORATORY_PHYSICAL_COLLECTION: ALLOWED
EXPLORATORY_EVIDENCE_CLASS: PRE_DEPLOYMENT_EXPLORATORY_REAL_DEVICE_EVIDENCE
EXPLORATORY_AUTOMATIC_C_C2_ELIGIBILITY: NO

FORMAL_PROTOCOL_OPERATOR_HANDOFF: HOLD
FORMAL_PROTOCOL_COLLECTION: HOLD_PENDING_PRODUCER_DEPLOYMENT_AND_LIVE_C_C1T_VERIFICATION
FORMAL_EVIDENCE_CLASS_AFTER_RELEASE: PROTOCOL_CONTROLLED_REAL_DEVICE_EVIDENCE
```

Pre-deployment exploratory evidence may characterize real CO₂ range, stable
VACANT/OCCUPIED qualitative behavior, rise/recovery, transport stability,
stale/missing/error modes, capture workflow, and future protocol needs. It is
retained evidence, not discarded data. If a fresh physical measurement event
identity is not available, it must be labelled
`fresh_sensor_event_identity=UNVERIFIED` and cannot automatically support a
formal `ENDPOINT_H150` chronology claim, C-C2 performance metrics, or
candidate accuracy/F1 claims.

The human-facing documents are:

```text
docs/handoff/20260815_SafeNest_CO2_AI_and_Measurement_Handoff_KO_01.md
docs/prompts/20260815_SafeNest_CO2_SCD40_Physical_Measurement_Guide_KO_01.md
datasets/co2/manifests/c_c1t_acquisition_tooling/human_handoff_status.json
```

The practical flow is:

```text
C-C1T tooling prepared
        ↓
exploratory collection allowed now
        ↓                         ↘
pre-deployment real-device evidence  team producer fresh-event review/deploy
                                      ↓
                               live C-C1T verification
                                      ↓
                               formal acquisition release
                                      ↓
                           protocol-controlled accumulation
                                      ↓
                                explicit C-C2 authorization
```

### External protocol-controlled data accumulation (currently HOLD)

The historical C-C1 contract describes formal protocol-controlled accumulation.
That formal path remains `HOLD_PENDING_TEAM_PRODUCER_OBSERVABILITY_PR_DEPLOYMENT`.
No formal session may start from the C-C1R contract while the deployed
acquisition adapter lacks the required fresh-event evidence. Exploratory
pre-deployment sessions may run under the separate evidence class above and
must not be silently promoted to C-C2 inputs. After the team change is deployed
and the C-C1T live validator PASS is rerun, formal accumulation remains outside
C-C2 and outside model development: the operator does not repeatedly inspect
model performance to alter scenario balance, stopping rules, thresholds,
features, or collection conditions. Any deviation receives a reason, timestamp,
affected session, and compliance classification. Raw payloads remain immutable
and the future validation set is not used as an adaptive tuning set.

### C-C2. Controlled evidence intake & formal device-domain validation

C-C2 begins only when all four conditions hold: the `C-B6` final candidate and its revised protocol are locked, protocol-controlled measurements have actually accumulated under that revised protocol, the intake passes pre-metric compliance checks, and the user explicitly authorizes C-C2. C-C2 first audits compliance; it does not assume that a file followed the protocol.

Before any performance metric, C-C2 verifies protocol version, session/source provenance, checksums and raw immutability, every feature required by the finally locked candidate, source and sensor timestamps, sensor-freshness semantics, SCD40 configuration state, error/stale/disconnect records, session boundaries, and independently synchronized VACANT/OCCUPIED ground truth. For the current reduced direction, the target candidate is `CO2 + CO2_slope`; the historical four-feature C-C1 contract is not a new acquisition authorization. Non-compliant sessions are classified and reported; they are not silently repaired or relabeled.

Only after intake passes may C-C2 evaluate the finally locked candidate using its declared feature order, `ENDPOINT_H150` built from verified fresh-measurement chronology using the revised C-C1 timestamp/freshness contract, its frozen TRAIN-only scaler, threshold, and model artifact. C-C2 does not refit the scaler, change the slope, alter the threshold, retrain, recalibrate, or change quantization. If independent ground truth is absent, outputs remain `MODEL_OUTPUT_OBSERVATION` and formal accuracy/precision/recall/F1/balanced-accuracy/confusion-matrix claims remain blocked. The current B5 four-feature artifact is not silently reinterpreted as the reduced candidate.

C-C2 is the first C-stage point that may support `FORMAL_SCD40_DEVICE_DOMAIN_VALIDATION`, subject to protocol compliance, feature completeness, independent ground truth, and complete failure accounting. B5 output semantics remain `VACANT/OCCUPIED` room occupancy; `P(OCCUPIED)` is not danger probability, and absolute CO₂ safety logic remains separate.

After C-C2, a poor or incomplete result is evidence, not automatic C-D authorization. A separate explicit decision gate must record whether any measured gap justifies C-D, what hypothesis it tests, what data split it uses, and what remains frozen.

### Decision Gate before C-D

C-D is permitted only after C-C2 compliance and validation evidence are reviewed and an explicit authorization records the measured gap, hypothesis, data split, unchanged frozen artifacts, owner, and approval. C-C0 or C-C1 findings alone never authorize C-D.

## C-D. gap-driven CO₂ dataset expansion

C-C0/C-C1/C-C2에서 식별한 mismatch는 재학습을 자동 허가하지 않는다. C-D는 C-C2 뒤 별도 decision gate에서 측정·승인된 gap만 다룬다. C-C 안에서 TRAIN 병합, C-B5 fine-tune, threshold 변경, scaler 재적합, `ENDPOINT_H150` 재선택을 하지 않는다.

- 공개 dataset에 없는 SafeNest 환경·환기·warm-up·drift 조건만 추가한다.
- 개인 식별 정보 없이 room/session/condition provenance를 보존한다.
- adaptation set과 external test set을 분리한다.
- 기존 LOCKED_TEST를 새 수집 데이터와 섞거나 재분할하지 않는다.

## C-E. CO₂ artifact lock·integration readiness

- model, scaler, feature profile, class map, threshold, checksum 고정
- offline/SCD40/Pi 검증 상태 분리
- provider output state와 metadata contract 고정
- 실제 검증이 없으면 `BLOCKED_HARDWARE` 또는 `NOT_VERIFIABLE` 유지

---

# Part IV — Thermal 실제 데이터·모델 A–E 트랙

## T-A. 실제 Thermal raw-to-canonical reconstruction

### T-A0. dataset selection·source identity

#### 목적

실제 frame/sequence와 subject/session provenance를 제공하는 thermal dataset을 선정한다.

#### 후보 평가 기준

1. 공식 배포처, license, checksum 제공 가능성
2. thermal 원본인지 RGB 변환 이미지뿐인지
3. radiometric value·unit·sensor 정보 보유 여부
4. subject, scene, session, sequence, camera ID 보유 여부
5. fall/normal label 정의와 event boundary 품질
6. SafeNest Thermal-44 해상도·시야와 비교 가능한지
7. 연구·재배포·모델 학습 사용 조건

선정 전에는 dataset 다운로드 수나 논문 metric만으로 적합 판정을 하지 않는다.

### T-A1. safe reader·raw unit contract

1. 지원 파일 형식, frame dtype, shape, channel, endianness를 명시한다.
2. radiometric temperature, sensor count, normalized image를 구분한다.
3. corrupt/truncated file, shape mismatch, NaN/Inf, saturation을 fail-closed 처리한다.
4. source sequence·frame index·timestamp를 보존한다.
5. 원본을 8-bit visualization로 바꾼 값을 canonical physical input이라고 부르지 않는다.

### T-A2. geometry·calibration·canonical frame

1. source orientation, rotation, crop, resize, invalid pixel 처리 규칙을 고정한다.
2. 현재 model input `80×62`와 실제 Thermal-44 frame orientation을 명시한다.
3. resize가 필요하면 interpolation과 aspect ratio 정책을 기록한다.
4. canonical raw/physical frame과 모델용 normalized tensor를 분리한다.
5. ambient/reference compensation을 사용할 경우 식과 parameter source를 기록한다.
6. visual spot check와 numeric inverse trace를 함께 수행한다.

### T-A3. sequence·window·event policy

1. frame rate와 timestamp reliability를 측정한다.
2. fall event 전·중·후 범위와 window 길이를 고정한다.
3. 한 event의 인접 frame이 여러 split으로 나뉘지 않게 한다.
4. frame 단위 sample과 sequence/event 단위 sample을 구분한다.
5. dropped frame, 큰 gap, duplicate frame의 처리와 exception을 기록한다.

### T-A4. label semantics·ambiguity

1. original activity/fall annotation을 보존한다.
2. staged fall, lying, sitting, bending, entering/exiting을 구분한다.
3. transition·경계 frame은 `AMBIGUOUS` 또는 별도 transition 상태로 보존한다.
4. posture를 곧바로 fall label로 치환하지 않는다.
5. 위험한 실제 낙상 시험을 요구하지 않으며 공개 데이터와 안전한 연출만 사용한다.

### T-A5. subject/session/event-wise split

1. subject를 우선 group으로 사용하고 불가능하면 scene/session/event hierarchy를 사용한다.
2. 동일 subject·event·연속 sequence의 cross-split overlap을 금지한다.
3. augmentation 파생본은 원본과 같은 TRAIN group에만 둔다.
4. split별 subject, event, activity, scene, camera 분포를 보고한다.
5. group provenance가 없으면 일반화 성능은 `NOT_VERIFIABLE`로 제한한다.

### T-A6. full conversion·integrity audit

1. 전체 file/sequence/frame 성공·경고·실패·제외를 기록한다.
2. corrupt, nonfinite, constant, saturated, duplicate/near-duplicate frame을 감사한다.
3. canonical tensor, label manifest, provenance를 sample index로 1:1 검증한다.
4. subject/session/event cross-split leakage를 독립 재계산한다.
5. 원본과 output checksum, preprocessing profile을 고정한다.
6. 실제 dataset이 준비되기 전 존재하던 synthetic fixture와 경로·claim을 분리한다.

#### T-A 종료 기준

- 실제 source→frame/sequence→label→split chain 재현 가능
- subject/session/event leakage 0건 또는 제한이 명시됨
- 실제 evaluation artifact 존재로 thermal skip 원인이 해소됨
- 모든 quality/exclusion evidence 보존

## T-B. Thermal offline model comparison

### Thermal B-series execution authority reconciliation (2026-08-14)

The bullets in this section are the original roadmap intent. For phases that
have already run, the phase-specific machine-readable evidence and passing
standalone validator are authoritative; this note does not rename or rewrite
historical evidence.

- `T-B0` completed the offline protocol, baseline contract, candidate
  preregistration, and evaluation-role policy. It did not train a model.
- `T-B1` completed the preprocessing comparison and selected
  `P1_TRAIN_FITTED_GLOBAL_ZSCORE` for the frame candidate under the frozen
  validation-only selection rule.
- `T-B2` completed a controlled frame-architecture comparison and selected
  `SMALL_CNN_BASELINE_V1`; it did not execute the original class-imbalance or
  hard-negative study.
- The original imbalance/hard-negative question remains unperformed. The
  selected SDT source exposes `LYING`, `SITTING`, `STANDING`, and `EMPTY_ROOM`
  only; `BENDING` and `PARTIAL_BODY` are not represented by verified source
  labels, so those hard-negative slices must not be fabricated.
- T-A3 evidence is frame-only: source timestamps and FPS are not verifiable,
  sequence/session/recording/event identifiers are absent, and filename or
  archive-index order is provenance only. Therefore a temporal T-B3 training
  comparison is blocked until a separate source/provenance amendment supplies
  verified ordered recordings and event context.
- The next eligible work item is a **proposed frame-only multi-seed
  confirmation** of the frozen candidate (minimum three seeds), subject to
  owner approval and a follow-up roadmap amendment. It is not authorization to
  construct pseudo-sequences or to start T-B3 training now.
- `T-B4` remains the Float→TFLite→INT8 equivalence phase, and `T-B5` remains
  robustness, latency, and candidate lock. Neither is started by this note;
  both must inherit the explicitly amended frame-level scope if temporal
  provenance remains unavailable.

### T-B0. evaluation protocol·baseline

- frame metric과 event metric을 분리
- primary: fall event recall, macro F1
- secondary: false alarms per hour/sequence, detection delay, normal activity specificity
- subject·scene·activity별 error slice 사전 정의
- rule/image baseline과 현재 TFLite, 신규 후보를 동일 split로 비교

### T-B1. preprocessing·augmentation ablation

- raw temperature/relative temperature/normalized tensor 비교
- crop, resize, background compensation 비교
- augmentation은 TRAIN에만 적용하고 원본 group을 상속
- 실제 validation improvement 없는 복잡한 pipeline을 채택하지 않음

### T-B2. imbalance·hard-negative strategy

- class weight, event-balanced sampling, focal loss를 분리 비교
- lying/bending/sitting/partial body를 hard negative로 분석
- false alarm 감소가 fall recall 붕괴를 숨기지 않게 함

### T-B3. frame vs temporal architecture

- small CNN, temporal pooling, lightweight sequence model을 공정 비교
- parameter, MACs, input history, latency를 함께 기록
- 동일 split·seed·early stopping으로 비교
- 최소 3개 seed 평균·worst case 기록

### T-B4. Float→TFLite→INT8 equivalence

- representative frames/sequences는 TRAIN에서만 선택
- float/TFLite/INT8 prediction·event decision parity 측정
- quantization saturation과 온도 범위별 error 기록
- 모델·preprocessing·class map·metadata checksum 고정

### T-B5. robustness·latency·candidate lock

- ambient offset, dead pixel, partial occlusion, hot object, missing frame, orientation 오류 시험
- Mac와 Pi latency를 분리
- locked-test는 최종 후보 확정 후 한 번 실행
- offline candidate와 Thermal-44 deployment candidate 분리

## T-C. Thermal-44 device-domain validation

1. 실제 frame shape, orientation, dtype, temperature conversion, invalid pixel semantics를 고정한다.
2. public dataset과 Thermal-44의 range·noise·FOV·ambient distribution 차이를 측정한다.
3. 정상 활동과 안전한 연출 scenario를 수집해 false alarm과 sequence behavior를 확인한다.
4. disconnect, partial frame, stale frame, NaN/Inf, sensor warm-up을 fail-closed로 검증한다.
5. Pi 5에서 acquisition+preprocess+inference latency, memory, 장시간 안정성을 측정한다.

## T-D. gap-driven Thermal dataset expansion

- C에서 확인된 FOV, ambient, occlusion, activity hard negative만 보강한다.
- 사람·session·event provenance와 촬영 동의를 보존한다.
- adaptation subject와 external holdout subject를 분리한다.
- 실제 위험 낙상이나 부상 가능 시험을 금지한다.

## T-E. Thermal artifact lock·integration readiness

- model, input geometry, normalization, event policy, threshold, checksum 고정
- offline/Thermal-44/Pi evidence 상태 분리
- provider가 raw frame과 inference result의 책임 경계를 명확히 구현
- 실제 hardware evidence가 없으면 deployment 승격 금지

---

# Part V — Multisensor Integration I 트랙

## I-0. shared contract inventory·freeze proposal

### 시작 시점

M-B0, C-A0, T-A0와 병렬로 읽기·설계 작업만 수행할 수 있다.

### 세부 작업

1. standalone provider contract, 팀 `shared/contracts/`, `devices/*/src`, integration node의 차이를 inventory한다.
2. `connect()`, `read()`, `close()`, sensor ID, timestamp, validity, error, latency, metadata schema를 비교한다.
3. `WARMING_UP`, `STALE`, `NOT_CONNECTED`, `INFER_FAILED`, hardware unavailable 상태를 fail-closed로 정의한다.
4. 실제 sensor driver ownership은 `devices/`, 공용 interface는 `shared/contracts/`, inference·risk orchestration은 `ondevice_ai/`로 유지한다.
5. contract proposal만으로 기존 device code나 firmware를 일괄 변경하지 않는다.

## I-1. sensor input/output contract conformance

### 시작 조건

- 각 센서 canonical input contract가 최소 pilot 수준으로 고정됨
- 팀 담당자와 provider ownership 합의

### 검증 항목

- mmWave: phase unit·sampling·window·gap가 M-A canonical contract 및 M-C0/M-C2 대응 판정과 일치. `breath_phase`와 `breath_rate_raw`를 혼동하지 않음
- CO₂: ppm/humidity/slope unit·history·warm-up가 C-A 및 C-C0/C-C1/C-C2 대응 판정과 일치. `TRANSPORT_FRESHNESS`와 SCD40 fresh measurement를 혼동하지 않음. H150 재구성만으로 B5 추론을 허가하지 않음. UCI T/RH 단위 일치만으로 SCD40 feature correspondence를 주장하지 않음
- Thermal: frame shape·orientation·unit·invalid pixel가 T-A/T-C와 일치
- 모든 provider: invalid/stale/missing을 정상값으로 합성하지 않음

## I-2. deterministic replay simulation

1. 실제 source-derived canonical replay와 synthetic fault fixture를 구분한다.
2. 각 node가 동일 timestamp contract로 replay되게 한다.
3. 정상, 단일 이상, 동시 이상, missing, stale, disconnect, out-of-order scenario를 실행한다.
4. replay output을 checksum 가능한 JSONL로 기록한다.
5. mock wiring 성공을 실제 sensor performance로 설명하지 않는다.

## I-3. rule-based fusion baseline

1. 현재 risk rule과 emergency override를 frozen baseline으로 평가한다.
2. 센서별 score calibration 차이를 확인한다.
3. missing sensor reweighting과 system health를 사람 위험도와 분리한다.
4. 시나리오 holdout에서 false alarm, missed critical event, detection delay를 기록한다.
5. validation 근거 없이 weight와 threshold를 조정하지 않는다.

## I-4. learned fusion conditional comparison

### 시작 조건

- synchronized 실제 multi-sensor scenario data 존재
- 개별 sensor candidate와 calibration 고정
- subject/scenario holdout 설계 완료

조건을 만족하지 않으면 learned fusion은 `DEFERRED_NO_SYNCHRONIZED_EVIDENCE`로 둔다. 합성 score 조합만으로 성능 우위를 주장하지 않는다.

## I-5. Raspberry Pi 5 system validation

- acquisition+inference+fusion end-to-end latency
- CPU, memory, temperature, power, storage growth
- 1시간 이상 안정성과 restart behavior
- sensor reconnect·partial failure·clock drift
- model/manifest/config loading과 checksum
- 경보·dashboard 출력의 schema와 설명 가능성

## I-6. team handoff·release gate

1. `AGENTS.md`의 team repository handoff contract를 따른다.
2. 기존 팀 `ondevice_ai/`와 충돌을 replace/merge/preserve/relocate/retire로 분류한다.
3. device implementation을 `ondevice_ai/sensors/`에 중복 복사하지 않는다.
4. source commit과 team base commit SHA, model/data checksum, test evidence를 PR에 기록한다.
5. direct main push, force push, `git add .`를 금지한다.
6. MR60/SCD40/Thermal-44/Pi 미검증 항목을 숨기지 않는다.

---

# Part VI — 통합 실행 checklist

## Parallel Wave 1

- [ ] M-B0 evaluation protocol·near-duplicate
- [ ] C-A0 source identity·inventory
- [ ] T-A0 dataset selection·identity
- [ ] I-0 contract inventory

## Parallel Wave 2

- [ ] M-B1~M-B4 preprocessing·imbalance·architecture·multi-seed
- [ ] C-A1~C-A6 full reconstruction
- [ ] T-A1~T-A4 reader·geometry·sequence·label pilot
- [ ] 공용 manifest integration commit

## Parallel Wave 3

- [ ] M-B5~M-B12 conversion·robustness·candidate lock·report
- [ ] C-B0~C-B5 offline candidate
- [ ] T-A5~T-A6 split·full conversion
- [ ] I-1 contract conformance

## Parallel Wave 4

- [ ] M-C0 existing team MR60 forensic audit
- [ ] M-C0A signal/cadence/offline-contract correspondence gate
- [ ] M-C0B exploratory legacy inference (optional)
- [ ] M-C1 protocolized physical MR60 measurement
- [ ] M-C2 formal device-domain evaluation of frozen Phase-B candidate
- [x] C-C0 existing team SCD40 forensic audit (`B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE`)
- [x] C-C0 freshness / feature-completeness / semantic / H150 / B5-identity / pre-inference gates
- [x] C-C0 exploratory legacy inference decision (`BLOCKED_FEATURE_INCOMPLETE`; no legacy inference run)
- [x] C-C1 four-feature measurement protocol freeze + independently executable operator prompt (historical evidence)
- [x] final pre-acquisition model-input decision (`ADOPT_REDUCED_FEATURE_DIRECTION`)
- [x] C-B6 reduced-feature candidate development and lock (`C_B6_PASS_WITH_LIMITATIONS`; INT8 slope-saturation review pending)
- [x] C-C1R reduced-feature protocol frozen and operator guide draft created (`C_C1R_BLOCKED`; handoff HOLD pending acquisition-tooling correction)
- [ ] external protocol-controlled SCD40 data accumulation (currently `HOLD`; AI tuning 금지)
- [ ] T-B offline candidate
- [ ] I-2 deterministic replay

## Parallel Wave 5

- [ ] C-C2 controlled intake + formal SCD40 device-domain validation (revised candidate/protocol and explicit authorization only)
- [ ] C-C2 뒤 별도 decision gate를 통과한 measured gap만 M/C/T-D 진입. mmWave는 M-C2에서 측정되고 별도 승인된 gap만
- [ ] T-C Thermal-44 domain
- [ ] I-3 rule fusion baseline
- [ ] I-4 learned fusion 조건 판정

## Final Wave

- [ ] M/C/T-E artifact·contract lock
- [ ] I-5 Pi 5 validation
- [ ] I-6 team handoff·release report

## 전체 종료 조건

1. M/C/T 각각 실제 source부터 locked offline candidate까지 독립 재현 가능하다.
2. 세 센서의 split·provenance·checksum·validator가 machine-readable하다.
3. synthetic smoke, offline real-data, device-domain, Pi evidence가 분리된다.
4. 실제 기기 입력과 학습 입력의 signal semantics가 측정으로 연결된다.
5. 공용 provider 계약이 invalid·stale·missing을 fail-closed 처리한다.
6. replay와 실제 integration 결과가 구분된다.
7. 팀 저장소 이관이 책임 경계와 CODEOWNERS를 보존한다.
8. 실측되지 않은 임상·하드웨어·배포 성능을 주장하지 않는다.
