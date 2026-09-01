# SafeNest B-complete 중간 AI 동기화 (팀 `ondevice_ai/`)

문서 상태: **OFFLINE CANDIDATE BASELINE — NOT FINAL HARDWARE DEPLOYMENT**
날짜: 2026-08-16

이 동기화는 완료된 스탠드얼론 offline AI candidate와 재현 계약을 팀 저장소 `ondevice_ai/`에 맞춰, Raspberry Pi 통합과 이후 실기기 Phase C가 **하나의 공통 기준**에서 시작하게 한다.

다음을 성립시키지 않는다.

- 실기기 성능 승인
- hardware-domain validation
- 최종 Raspberry Pi 배포 승인
- 멀티센서 장기 안정성
- production safety certification

## Provenance

| 항목 | 값 |
| --- | --- |
| Standalone | https://github.com/sheepmeat/test @ `efc7e2eb61a49e221ce0ebf6057b0c1617525ad1` |
| Team base | https://github.com/jinsu1011/safenest-embedded-competition @ `3d86bf2a7a4e527d7aba2dfabcb087201ffeb46e` |
| 대상 | `ondevice_ai/` only |
| 이전 중간 동기화 | 2026-08-13, source `77b1695` |

## B completion의 의미

B 완료는 offline candidate와 전처리/평가/TFLite·INT8 배포 계약, validator, 인수인계 자료가 팀 공통 기준으로 쓸 만큼 얼렸다는 뜻이다. 실 MR60/SCD40/Thermal 하드웨어나 Raspberry Pi 장기 배포가 검증됐다는 뜻이 아니다.

## 센서 상태

### mmWave

Frozen offline candidate: `M-B3_CONV1D_GAP_BASELINE_seed42_M-B5_CAL_CLASS_BALANCED_120` INT8, SHA-256 `6dff6aaa72c79d76715d40cf7e32bb1e6cd9b2c2e3ac78eaf2fda737561430c5`. 입력은 10 Hz / 30 s / 300 sample, `BPF_ZSCORE` → INT8 `[1,300,1]`. APNEA는 voluntary breath-hold proxy다.

다음 단계는 standalone M-C0 correspondence, 이후 M-C1/M-C2다. 실측 안내서는 PRE-M-C1 준비 문서다.

### CO₂

Frozen offline occupancy candidate: `C_B6_REDUCED_CO2_SLOPE_CANDIDATE_001`, feature order `CO2`, `CO2_slope`, TRAIN-internal threshold 0.43. INT8 SHA-256 `c5969b367f5b5e28c4d27f1bdd6220f7d02da92e99604e3f85c9f1291e98dd3b`. occupancy 모델은 CO₂ safety threshold, sensor health, fusion과 분리한다. SCD40 실기기 검증은 남는다.

### Thermal

T-B5 offline lock `FULL_INT8`, SHA-256 `fa9730c29535477a3994c11e664474a0ca0116afaaa172889f47446ab2ac46be`. 바이너리는 git에 없고 외부 SSD identity다. `HUMAN_FALL`은 lying-derived posture proxy이며 verified `FALL_EVENT`가 아니다.

## Runtime 주의

기본 `config/models.yaml`과 `models/model_manifest.json`은 역사적 v0.1.0을 계속 가리킨다. 이번 PR은 그 기본값을 바꾸지 않았다. Thermal T-B5 바이너리가 git에 없고, 기존 mock/runtime 테스트가 v0.1.0에 묶여 있기 때문이다. Pi 통합은 `docs/integration/20260816_b_complete_active_offline_candidates.json`의 B-complete 경로를 사용해야 한다.

## 보존

팀 `integrated_node/competition_runtime/`, `esp32_sensor_node.ino`, 역사적 모델(`safenest_lstm_quant.tflite`, `thermal_fall_model.h5`), 2026-08-13 통합 기록은 유지한다. `devices/`, `shared/contracts/`, 펌웨어, 대시보드는 이 PR에서 바꾸지 않는다.
