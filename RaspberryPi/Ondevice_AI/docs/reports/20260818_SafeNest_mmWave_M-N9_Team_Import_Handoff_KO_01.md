# SafeNest mmWave M-N9 팀 저장소 인수인계

- 날짜: 2026-08-18
- 대상: 팀 저장소 `jinsu1011/safenest-embedded-competition` PR #30
- 이 문서의 역할: **무엇을 넣었고, 지금 런타임이 무엇을 쓰며, 다음에 무엇을 하면 안 되는지**를 팀원이 읽기 위한 인수인계
- 이 문서가 아닌 것: 재학습 보고, 실기기 Accuracy/F1, Raspberry Pi 배포 승인

작성 위치는 재구성 이후 AI 루트인 `RaspberryPi/Ondevice_AI`입니다. 루트 `ondevice_ai/`는 만들지 않았습니다.

## 1. 한 줄 결론

잠긴 mmWave 후속 모델은 **M-N9 FULL_INT8**입니다. 파일은 이 저장소에 들어 있습니다. **지금 `./run_safenest.sh`가 그 모델을 돌리지는 않습니다.** 라이브 키 `models.mmwave`는 예전 v0.1.0 그대로 막혀 있습니다.

| 질문 | 답 |
| --- | --- |
| 최신 잠긴 INT8이 팀 저장소에 있는가? | 있다. `MMWAVE_M_N9_FULL_INT8_V1` |
| 오늘 Pi 런타임이 M-N9를 쓰는가? | 아니다. 배선은 다음 작업 |
| 옛 10 Hz × 300 샘플 모델을 라이브로 승격해도 되는가? | 안 된다 |
| 빈 방/사람 없음을 APNEA로 보여도 되는가? | 안 된다. presence gate 필수 |
| 실 MR60 성능이 증명됐는가? | 아니다. `DEVICE_VALIDATED = NO` |
| M-N10 사람 측정을 지금 시작해야 하는가? | 아니다. 캡처 PR은 보류 |

## 2. 왜 예전 모델이 아닌가

팀 런타임과 `RaspberryPi/Ondevice_AI`에 남아 있는 역사적 mmWave는 다른 계약입니다.

| | 역사적 B / v0.1.0 | 지금 잠긴 M-N9 |
| --- | --- | --- |
| 파일 | `models/mmwave/mmwave_resp_int8_v0.1.0.tflite` | `models/mmwave/m_n9/MMWAVE_M_N9_FULL_INT8_V1.tflite` |
| 입력 | `[1, 300, 1]`, 10 Hz, 30 s | `[1, 240, 1]`, 8 Hz, 30 s |
| 신호 | `resp_phase` + BPF + z-score | MR60 `breath_phase`의 시간 인식 1차 미분(R2) + 창 국소 MAD(나누기만, 중심화 없음) |
| 상태 | `deployment_allowed=false`, class collapse | 잠긴 후속 후보. Runtime 미배선 |
| 공개 데이터 RAPID recall | 해당 없음(붕괴) | VAL에서 약 0.40. INT8이 더 나빠지지는 않음 |

300개 창을 M-N9에 넣으면 안 됩니다. M-N9를 옛 interpreter/BPF 경로에 끼워 넣어도 안 됩니다.

## 3. 이 PR이 넣은 파일

경로 기준은 `RaspberryPi/Ondevice_AI/`입니다.

```text
models/mmwave/m_n9/MMWAVE_M_N9_FULL_INT8_V1.tflite
SHA-256  3b008af4be0facc4037c2afd3fe39292fb794208eb4370dbe6916b2d15aa38a4
size     11816 bytes

config/mmwave/m_n9_full_int8_artifact_lock.json
config/mmwave/m_n4_canonical_input_dataset_contract.json
scripts/mmwave_m_n4_canonical.py
models/mmwave/m_n9/team_import_inventory.json
docs/reports/20260818_SafeNest_mmWave_M-N9_Team_Import_Handoff_KO_01.md
```

상류 권위:

```text
https://github.com/sheepmeat/test
SHA  390f3be3d75987a79a0e0438ba8a9d5e9e19dc97
```

팀 저장소 기준 커밋은 PR #30 베이스 `c6979cd`입니다. `COMPONENT_SOURCES.json`의 Ondevice_AI 베이스 SHA `4129753`은 전체 트리 재동기화가 아니라, 그 스냅샷 위에 M-N9 overlay를 얹은 것입니다.

## 4. 입력 계약 (M-N4, 바꾸지 말 것)

```text
계약 ID:        MMWAVE_MR60_COMPAT_INPUT_DATASET_V1
소스:           MR60BHA2 0x0A13 breath_phase
갱신 시각:      ts_monotonic_ms - phase_age_ms
표현:           R2 = Δphase / Δt_update
평활:           없음
스케일:         WINDOW_LOCAL_MAD (divide only, no centering)
창:             30 s
속도:           8 Hz
샘플 수:        240
shape:          [1, 240, 1]
```

운영에서 `phase_age_ms`가 없으면 창을 만들지 않습니다. JSON 한 줄 = 샘플 하나 같은 폴백은 금지입니다. 큰 간격이 있는 창은 통째로 버립니다.

INT8 입출력:

```text
input   int8 [1,240,1]  scale 0.5623255372047424  zero_point 4
        q = clip(round(x / scale + zero_point), -128, 127)
output  int8 [1,3]      scale 0.00390625          zero_point -128
        x_float = (q - zero_point) * scale
```

클래스: `0 NORMAL`, `1 RAPID_OR_ABNORMAL`, `2 APNEA`.  
APNEA는 SafeNest의 자발적 호흡 정지 / 참조 센서 기반 **프록시**이며 임상 apnea가 아닙니다.

## 5. presence gate (모델 4번째 클래스가 아님)

빈 방이나 사람 없는 canonical 영입력은 FLOAT/INT8 모두 높은 신뢰도의 APNEA-proxy로 나갑니다. 이것은 INT8 버그가 아니라 M-N7에서 확인된 동작입니다.

```text
PRESENCE_GATE_REQUIRED = YES
사람이 없으면 호흡 분류를 SUPPRESSED 한다
UI에 NORMAL / RAPID / APNEA를 생리 상태로 올리지 않는다
```

기존 MR60 필드 `human_detected_raw`를 쓰면 됩니다. 이 저장소에서 새 presence 임계값을 만들지 마십시오. 구현은 Runtime 배선 작업입니다.

## 6. 지금 런타임이 하는 일

`RaspberryPi/Runtime/ai/runtime.py`의 `LazyModel("mmwave")`는 여전히 `models.model_manifest.json`의 **`models.mmwave`** 만 봅니다. 그 항목은 v0.1.0이고 `CLASS_COLLAPSE_ON_REPOSITORY_NPZ`로 막혀 있습니다.

`RaspberryPi/Runtime/ai/pipeline.py`는 아직 `respiration_phase_window` 길이 **300**, 10 Hz를 요구합니다.

그래서 이번 PR은:

- M-N9를 `models.mmwave_m_n9`로 추가하고
- `mmwave_active_locked_artifact.runtime_wired = false`로 표시하고
- 라이브 키를 바꾸지 않았습니다

`config/mmwave_input_contract.yaml`도 역사적 300샘플 계약으로 남겨 두었습니다. 새 계약은 `config/mmwave/*.json`입니다.

## 7. 이 숫자가 의미하는 것 / 의미하지 않는 것

상류 M-N9 VAL (17명, 70 창, heldout 재사용 없음):

| | FLOAT | INT8 |
| --- | ---: | ---: |
| Macro F1 | 0.723 | 0.739 |
| Top-1 일치 | — | 0.986 |
| RAPID recall | 0.40 | 0.40 |

이것은 공개 데이터 VAL 양자화 동치이지, MR60 실측 점수가 아니고, Pi latency도 아닙니다.

```text
Mac TFLite load + zero invoke  = 이번 팀 PR에서 수행
Pi isolated smoke              = NOT_PERFORMED (파이 없음)
live MR60                      = NOT_PERFORMED
DEVICE_VALIDATED               = NO
```

## 8. 하지 말 것

- 펌웨어, 팀 센서 threshold, `ESP32/`를 이 모델 때문에 바꾸지 마십시오
- 빈 방을 APNEA로 “고치기” 위해 재학습하지 마십시오
- 공개 heldout을 다시 열지 마십시오
- M-N10 다인 캡처를 이 PR 머지의 다음 자동 단계로 올리지 마십시오
- `scripts/mmwave_m_n4_canonical.py`의 freeze `main()`을 팀 트리에서 실행해 A6 산출물을 덮지 마십시오. 헬퍼(`accept_phase_events`, `form_canonical_window`)만 재사용하면 됩니다

## 9. 다음 작업 (이 PR 밖)

1. integration git(`yuname121/integration`)에도 같은 INT8 바이트를 넣는다
2. 맥에서 스냅샷/재생 스트림으로  
   `breath_phase + freshness → 30 s canonical → M-N9 INT8 → presence suppress → DB/UI`  
   를 붙인다. 센서/파이가 없어도 재생까지는 할 수 있다
3. 하드웨어가 돌아오면 Pi smoke (복사 → SHA → load → invoke)
4. 그 시스템이 로거가 된 뒤에 M-N10 캡처를 재개한다

## 10. 상세 증거 위치

팀 저장소에 전체 M-N5~M-N9 실험 트리를 복사하지 않았습니다. 변환·VAL 동치·presence 근거는 상류를 보면 됩니다.

- 상류 lock: `sheepmeat/test` `config/mmwave/m_n9_full_int8_artifact_lock.json`
- 상류 보고: `docs/mmwave/20260818_SafeNest_mmWave_M-N9_FULL_INT8_Pi_Readiness_01.md`
- 상류 결과: `datasets/mmwave/manifests/m_n9_full_int8_result.json`
- 이 저장소 인벤토리: `models/mmwave/m_n9/team_import_inventory.json`
- 이 저장소 포인터: `models/model_manifest.json` → `models.mmwave_m_n9`
