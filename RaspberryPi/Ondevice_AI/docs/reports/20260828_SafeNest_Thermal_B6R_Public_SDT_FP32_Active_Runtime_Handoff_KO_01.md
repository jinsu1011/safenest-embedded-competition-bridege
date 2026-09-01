# SafeNest Thermal B6-R Public SDT FP32 활성 Runtime 인수인계

## 결론

`public_sdt_pooled_mlp_fp32_tflite_v1.tflite`를 팀 저장소의 최종 활성 thermal runtime 모델로 지정했다. 기존 `thermal_fall_int8_v0.1.0.tflite`는 파일과 이력을 보존하지만 selector와 deployment gate에서는 비활성이다.

## 모델·selector 계약

- 팀 기준 시작 commit: `339eb4f5a13ff68940e127836375bec6f11dff3d`
- 상류 모델 commit: `ccdb2b16ddbbec82d1a4d53cef6b23314ebf366b`
- 활성 key: `thermal_public_sdt_fp32_active`
- artifact: `models/thermal/public_sdt/public_sdt_pooled_mlp_fp32_tflite_v1.tflite`
- SHA-256: `f88d65d76dbb21862e1f3cdff17cefb038a432047ded6ac8d5563bc8bc8c52ff`
- size: `70,592 bytes`
- input: `[1,62,80,1] float32`, frame별 min-max 정규화
- output: `[1,3] float32`
- class order: `NOT_HUMAN`, `HUMAN_NORMAL`, `HUMAN_FALL_PROXY`
- lifecycle: `FINAL_RUNTIME_MODEL` / `ACTIVE_FINAL`

`models/model_manifest.json`, `config/models.yaml`, `ThermalInterpreter`, Runtime `LazyModel`이 같은 key를 가리킨다. selector가 어긋나면 Runtime은 `MODEL_SELECTOR_DRIFT`로 fail-closed한다.

## Runtime 판단 반영

새 모델의 결과는 관측용 shadow가 아니라 실제 Runtime AI 결과와 위험 융합에 사용된다.

- `NOT_HUMAN` / `HUMAN_NORMAL`: thermal 위험 점수 `0.0`
- `HUMAN_FALL_PROXY`: thermal 위험 점수 `0.4`
- `HUMAN_FALL_PROXY` 이유 코드: `THERMAL_FALL_PROXY_LIMITED_RISK_NO_EMERGENCY`
- 실제 `HUMAN_FALL`로 이름을 바꾸지 않음
- proxy 단독 emergency override 및 자동 긴급 알림 금지

이 경계는 모델이 최종 artifact라는 결정과 별개다. 학습 target이 누운 자세 proxy이므로 실제 낙상 이벤트 권한까지 자동으로 생기지는 않는다.

## 변경 범위

- 활성 selector와 FP32 계약: manifest, metadata, YAML, interpreter
- 운영 Runtime: lazy loader, thermal pipeline, runtime status, risk formula
- 보조 경로: Thermal-44 sensor adapter, Pi thermal runner, legacy integrated node
- 안전 회귀: 기존 INT8 non-active, proxy 제한 점수, emergency 미발생, selector drift 차단
- Stage 7 preflight: 활성 artifact identity와 제한 risk 경계 검사

## 검증 경계

로컬에서 artifact hash, FP32 tensor contract, 실제 TFLite load/invoke, Runtime risk mapping과 status projection을 검증한다. Raspberry Pi, MI48/Thermal-90, 실센서 지연시간, 실제 낙상 recall/false alarm은 수행하지 않았으며 `BLOCKED_HARDWARE`로 유지한다.

### 로컬 실행 결과

- Thermal artifact/interpreter: `11 tests`, `OK` (`2`개 선택형 NPZ smoke는 데이터 부재로 skip)
- Runtime selector/load/invoke + risk/status + manifest/preflight 집중 회귀: `54 tests`, `OK`
- Thermal mock adapter active-selector 회귀: `1 test`, `OK`
- 변경 Python compile, JSON parse, `git diff --check`: `OK`
- 배포 bundle 검증: `OK` (필수 파일, 전체 모델 hash, secret/database, Python cache 검사 통과)
- 전체 model validator는 thermal의 hash·FP32 contract·invoke를 통과했지만, 기존 mmWave B23 `.pt` selector와 TFLite 전용 validator/config 사이 불일치 때문에 저장소 전체 결과는 `FAILED`다. 이 PR에서 mmWave selector를 변경하지 않는다.
- 전체 Stage 7/UI suite는 현재 환경의 `torch`·`scipy` 부재 및 기존 Web contract 기대치 차이 때문에 실행 범위에서 제외했다. 위 집중 preflight selector 검사는 통과했다.

## Rollback

문제 발생 시 `active_runtime_selectors.thermal`과 Runtime `LazyModel` selector를 `thermal`로 되돌리고, rollback 기간에만 legacy `models.thermal.deployment_allowed`를 복구한다. 새 artifact는 조사와 재현을 위해 삭제하지 않아도 된다. PR merge 전체를 되돌릴 때는 merge commit을 `git revert`한다.
