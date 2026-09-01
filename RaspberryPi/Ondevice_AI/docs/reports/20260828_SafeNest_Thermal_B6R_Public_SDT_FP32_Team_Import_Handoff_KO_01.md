# SafeNest Thermal B6-R Public SDT FP32 팀 저장소 Import 인수인계

## 1. 통합 범위

- 팀 저장소: `https://github.com/jinsu1011/safenest-embedded-competition`
- 팀 저장소 기준 `main`: `1df0c178b02d700f4893728b0a9b5836941b6adc`
- 상류 저장소: `https://github.com/sheepmeat/test`
- 상류 검토·병합 commit: `ccdb2b16ddbbec82d1a4d53cef6b23314ebf366b`
- 상류 PR: `https://github.com/sheepmeat/test/pull/183`
- 대상 artifact: `public_sdt_pooled_mlp_fp32_tflite_v1.tflite`

이 작업은 검증된 artifact byte와 portable identity를 팀 저장소의 canonical AI 경로에 넣는 최소 overlay다. 상류 전체 tree를 덮어쓰거나 `research/thermal_ai/`, `RaspberryPi/Runtime/`, ESP32 firmware, 센서 threshold를 수정하지 않는다.

## 2. 배치 위치와 identity

| 항목 | 값 |
|---|---|
| 팀 경로 | `RaspberryPi/Ondevice_AI/models/thermal/public_sdt/public_sdt_pooled_mlp_fp32_tflite_v1.tflite` |
| size | `70,592 bytes` |
| SHA-256 | `f88d65d76dbb21862e1f3cdff17cefb038a432047ded6ac8d5563bc8bc8c52ff` |
| input | `[1,62,80,1] float32` |
| output | `[1,3] float32` |
| quantization | `NONE` |
| class order | `NOT_HUMAN`, `HUMAN_NORMAL`, `HUMAN_FALL_PROXY` |

복사 전후 SHA-256과 size가 상류 artifact와 정확히 일치한다. 재학습·재변환·양자화는 수행하지 않았다.

## 3. 충돌 결정

| 팀 경로/책임 | 결정 | 이유 |
|---|---|---|
| 기존 `models.thermal` / INT8 artifact | `PRESERVE` | 현재 runtime selector와 `HUMAN_FALL` safety mapping을 유지한다. |
| 새 FP32 artifact | `ADD` | 별도 `public_sdt/` 하위에 exact byte로 추가한다. |
| `models/model_manifest.json` | `MERGE` | 새 key `thermal_public_sdt_fp32_shadow`만 추가한다. |
| `inference/thermal_interpreter.py` | `PRESERVE` | default selector를 바꾸지 않으며 기존 interpreter는 이미 FP32 tensor type을 처리할 수 있다. |
| `RaspberryPi/Runtime/` | `PRESERVE` | production pipeline·risk mapping을 변경할 권위나 Pi evidence가 없다. |
| `research/thermal_ai/` | `PRESERVE` | 오프라인 연구 workspace이며 runtime artifact의 canonical 위치가 아니다. |

## 4. 등록 상태

새 모델은 `SHADOW_ONLY_NONACTIVE`로 등록한다.

- `active_runtime_selector=false`
- `default_activation=false`
- `deployment_allowed=false`
- `safety_authority=false`
- `hardware_validation=BLOCKED_HARDWARE`
- 기존 `models.thermal` key, artifact, SHA, class map은 불변

따라서 이번 merge만으로 Pi runtime이 새 모델을 호출하거나 `HUMAN_FALL_PROXY`를 위험 판정에 사용하지 않는다.

## 5. 허용·금지 claim

허용 claim은 `PUBLIC_SDT_ONLY`, `SOFTWARE_ONLY`, `FP32_TFLITE`, `SHADOW_ONLY`, `NON_GATING`이다. 다음 claim은 금지한다.

- Raspberry Pi 또는 LiteRT target 성능 검증
- MI48/Thermal-90/실센서 검증
- 실제 낙상 검증
- production ready 또는 safety authority
- locked public test 일반화 성능

상류 DEVELOPMENT 8,000개 diagnostic은 accuracy `0.907`, macro F1 `0.9013267411`이지만 독립 test 성능이 아니다. locked public test access count는 `0`이다.

## 6. 의도적으로 전송하지 않은 파일

- public SDT 원본 archive와 materialized arrays
- P1 NumPy weight artifact(`.npz`)와 전체 학습 workspace
- local thermal/MI48/Thermal-90 data
- 상류 `.git`, `.github`, archive, cache, virtual environment, release bundle
- P0–P4 전체 script·manifest·report tree

팀 runtime에 필요한 exact TFLite artifact, compact metadata, manifest entry, 검증 test와 본 인수인계만 포함한다.

## 7. 검증 계약

팀 저장소 검증은 다음을 확인해야 한다.

1. artifact SHA-256/size 일치
2. live interpreter load와 FP32 `[1,62,80,1]→[1,3]` tensor contract
3. finite probability와 합 `1.0`
4. 기존 active thermal selector·artifact·class map 불변
5. 새 모델의 non-active / non-safety 경계
6. 팀 AI 전체 test와 Runtime 영향 test
7. `git diff --check` 및 machine-specific absolute path 부재

### 7.1 실제 실행 결과 (2026-08-28)

- `python -m unittest -v tests.test_thermal_public_sdt_shadow_model tests.test_thermal_interpreter`: **11개 중 9 PASS, 2 SKIP, 0 FAIL**. 새 shadow 모델 4개 test는 모두 PASS했고, skip 2개는 저장소에 선택적 NPZ 입력 fixture가 없기 때문이다.
- 새 artifact를 TensorFlow Lite XNNPACK interpreter로 실제 load/invoke하여 input/output shape, FP32 dtype, 무양자화 contract, finite probability와 합 `1.0`을 확인했다.
- `RaspberryPi/Runtime/deployment/verify_bundle.py`: **PASS (`ok=true`)**. required files, 전체 manifest model hash, secret/database, Python cache 검사가 모두 통과했다.
- `python -m unittest discover -s tests -p 'test_*.py' -v`: 총 602개 중 432 PASS, 2 SKIP, 89 FAIL, 79 ERROR. 실패·오류는 누락된 선택 의존성(`torch`, `sklearn`), 누락된 원본 dataset archive, 기존 mmWave fixture/manifest 불일치 등 현재 저장소 환경의 광범위한 blocker에서 발생했다. 이 변경이 건드린 thermal shadow 모델 focused test는 모두 통과했다.
- `scripts/validate_models.py`: 새 thermal artifact의 load/hash는 성공했으나, 기존 active mmWave 항목 `M-PV2_FAMILY_B_TRACE_TCN_BREATHING_RR_QUALITY`의 manifest/config path 불일치 때문에 전체 validator는 FAIL했다. 새 thermal 항목과 무관한 기존 저장소 blocker로 분리 기록한다.
- Runtime 영향 test는 기존 pipeline import가 선택 의존성 `torch`를 요구하여 `BLOCKED_DEPENDENCY`였다. 이번 변경은 `RaspberryPi/Runtime/` 및 active selector를 수정하지 않는다.
- JSON parse, `git diff --check`, source/target SHA-256 비교와 변경 파일 내 machine-specific absolute path scan은 PASS했다.

## 8. 하드웨어 영향과 남은 위험

하드웨어·firmware·포트·센서 calibration 변경은 없다. Pi에서 FP32 latency, RSS, CPU, temperature, prolonged replay, LiteRT op compatibility를 측정하지 않았다. public posture proxy의 domain shift와 `HUMAN_FALL_PROXY` 의미 차이 때문에 별도 권한과 실기기 evidence 없이 default selector로 승격하면 안 된다.

## 9. Rollback

runtime selector를 바꾸지 않았으므로 운영 rollback은 필요 없다. 문제가 발견되면 팀 merge commit을 `git revert <merge_commit>`로 되돌린다. 수동 rollback 시 새 artifact·metadata·test·보고서를 제거하고 `thermal_public_sdt_fp32_shadow` manifest entry와 `COMPONENT_SOURCES.json` overlay만 제거한다. 기존 `models.thermal`은 변경 전후 동일하다.
