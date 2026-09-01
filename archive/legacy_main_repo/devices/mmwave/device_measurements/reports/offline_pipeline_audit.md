# Offline Pipeline Audit

센서 연결 없이 기존 CSV를 M-B11 locked preprocessing 계약까지 통과시킨 추가 검증 결과다. 실제 MR60의 새 측정값을 만들거나 physical compatibility를 증명하는 결과는 아니다.

## Exact preprocessing replay

현재 bundled Python에는 `scipy`가 없어, 별도 임시 runtime에 `numpy 2.5.2`와 `scipy 1.18.0`을 설치해 실행했다. 메인 레포와 별도 레포의 의존성 파일은 변경하지 않았다.

실행한 순서는 기존 preprocessing source와 동일하다.

1. 10 Hz, 30초, 300-sample window
2. window mean subtraction
3. Butterworth bandpass 0.1–0.5 Hz, order 4, `filtfilt`
4. M-B11 locked z-score: mean `0.0031162832173884064`, std `2.955399434649939`
5. `[-5, 5]` clipping
6. int8 quantization: scale `0.041720833629369736`, zero-point `-3`

## CSV replay result

| 검사 | 결과 |
|---|---:|
| CSV 파일 | 9 |
| 생성 window | 620 |
| 최종 tensor shape | `(620, 300, 1)` |
| finite | 전체 통과 |
| preprocessing quality invalid | 0 |
| preprocessing clipping ratio | 0% |
| quantized 범위 | -12 ~ 9 |
| int8 saturation | 0% |
| dequantization MAE | 0.0086567635 |
| dequantization 최대 절대오차 | 0.0208602846 |

기존 CSV 9개는 locked preprocessing과 int8 입력 범위에서 수치적으로 안정적이었다. 이 결과는 기존 CSV delivery에 대한 오프라인 검증이며, 실제 새 MR60 측정의 일반화나 센서 phase 단위 검증은 아니다.

## TFLite invoke 및 host benchmark

locked SHA-256과 일치하는 int8 TFLite model과 TensorFlow `2.21.0` 임시 runtime을 확보해 실제 `invoke`를 실행했다. 기존 CSV 620개 window 모두 실행에 성공했다.

- 평균 latency (`set_tensor + invoke`): `0.008197 ms`
- median/p50: `0.008041 ms`
- p95: `0.008333 ms`
- 최대: `0.052583 ms`
- 예측: `NORMAL 0`, `RAPID_OR_ABNORMAL 0`, `APNEA 620`

이 620/620 관찰의 분류는 `EXPLORATORY_PRE_CORRESPONDENCE_INFERENCE`이고 경고는 `PIPELINE_CORRESPONDENCE_WARNING`, `DEVICE_DOMAIN_MISMATCH_WARNING`이다. MR60-to-Phase-B 신호·시간 대응이 미확립 상태이므로 formal 장치 성능, M-C2, 모델 실패, 실제 APNEA 또는 임상 근거로 해석하지 않는다. 기존 CSV label은 독립 ground truth가 아니므로 accuracy·F1·recall·confusion matrix를 계산하지 않았고 단일 원인도 확정하지 않았다. latency도 Apple Silicon host 값이다.

## Synthetic edge-case tests

- 정상 0.25 Hz sine: finite, `(1, 300, 1)`, valid
- 상수 신호: finite, `(1, 300, 1)`, valid
- NaN/Inf 포함: finite output으로 복구되지만 quality invalid
- 100-sample 짧은 입력: edge padding 후 shape은 유지되지만 quality invalid

## Bundle audit and negative tests

`tools/verify_bundle.py`로 CSV와 JSONL을 한 번에 검사할 수 있다.

- CSV: 9개, timestamp 역행 0, 중복 0, 최대 gap 0.103 s
- raw JSONL: 78개, 172,390 physical lines, valid JSON 172,387개, invalid 3개
- raw timestamp 역행 0, 파일별 duplicate 683개
- schema 1.0/1.1/1.2 외 auxiliary record 13,293개는 schema가 없음
- 결과: `PASS_WITH_EXCEPTIONS` — 기존 raw의 알려진 예외를 숨기지 않고 기록

`tools/run_negative_tests.py`는 다음 4개 오류를 모두 검출했다.

- backward timestamp
- malformed JSON
- strict duplicate timestamp
- `video_collected=true` privacy 위반

## Live monitor dry-run

`tools/live_mr60_monitor.py`를 기존 final attempt02 raw에 replay해 화면 출력을 확인했다.

- replay records: 18,574개
- 관찰 rate: 10.00Hz
- 마지막 gap: 100ms
- 최대 gap: 103ms
- JSON/UART/checksum 오류: 0/0/0
- 30초 window: `READY`
- 마지막 record distance가 166.5cm라 monitor state는 `UNKNOWN_DISTANCE`

실제 USB port를 지정하면 같은 형식으로 raw를 저장하면서 1초마다 상태를 출력한다. 현재 장치가 연결되지 않아 live port 자체는 아직 실행하지 않았다.

## 측정 준비물

실제 연결 후 바로 쓸 수 있도록 다음 템플릿을 추가했다.

- `templates/session_manifest.planned.json`
- `templates/environment_metadata.template.json`
- `templates/capture_checklist.md`

템플릿은 실제 측정 증거가 아니며, `PENDING_CAPTURE` 값을 실제 값으로 교체하고 raw SHA-256·record count·환경 정보를 채운 뒤 validator를 실행해야 한다.
