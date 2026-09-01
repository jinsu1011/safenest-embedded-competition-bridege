# TFLite Offline Benchmark

센서 없이 기존 CSV delivery를 locked M-B11 preprocessing과 실제 int8 TFLite model에 통과시킨 결과다.

## 실행 대상

- TensorFlow `2.21.0`
- CPU, 1 thread, XNNPACK delegate
- model SHA-256: `6dff6aaa72c79d76715d40cf7e32bb1e6cd9b2c2e3ac78eaf2fda737561430c5`
- input: `[1,300,1]`, `int8`, scale `0.041720833629369736`, zero-point `-3`
- output: `[1,3]`, `int8`, scale `0.00390625`, zero-point `-128`

## 실행 결과

- 입력 window: 620개
- 실제 `invoke`: 620회 모두 성공
- input saturation: 0%
- input quantized range: `-12 ~ 9`
- 평균 latency (`set_tensor + invoke`): `0.008197 ms`
- median/p50: `0.008041 ms`
- p95: `0.008333 ms`
- 최대: `0.052583 ms`
- 예측 결과: `NORMAL 0`, `RAPID_OR_ABNORMAL 0`, `APNEA 620`

`NORMAL_D06/D09/D12/D15`와 `BREATH_PACED_12/15/20` 모든 source label 그룹에서도 예측은 전부 APNEA였다. 분류는 `EXPLORATORY_PRE_CORRESPONDENCE_INFERENCE`이며, `PIPELINE_CORRESPONDENCE_WARNING` 및 `DEVICE_DOMAIN_MISMATCH_WARNING`이다.

현재 구성한 legacy CSV `resp_phase` → nominal 10Hz interpolation → `BPF_ZSCORE` → INT8 → frozen Phase-B TFLite 경로에서 620/620 window가 APNEA 출력을 냈다. MR60과 Phase-B 사이의 신호·시간 대응이 아직 확립되지 않았으므로 이는 exploratory collapse 관찰 및 correspondence/domain warning이지, 실제 장치 모델 성능이나 M-C2 결과가 아니다. 한 가지 원인을 확정하지 않는다.

모든 입력이 APNEA로 나온 것은 성능 통과가 아니다. 기존 CSV의 `NORMAL_D06`, `BREATH_PACED_12` 같은 labels는 모델의 `NORMAL/RAPID_OR_ABNORMAL/APNEA`에 대한 독립 ground truth가 아니므로 accuracy·F1·recall·confusion matrix를 계산하지 않았다. M-C0 correspondence와 M-C2는 완료되지 않았으며 임상 apnea 근거도 아니다.

또한 latency는 Apple Silicon 개발 host에서 측정한 값이다. Raspberry Pi 또는 ESP32의 배포 latency로 해석하면 안 된다.
