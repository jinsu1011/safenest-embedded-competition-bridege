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
