# mmWave 최종 ESP Live Validation

## 1. 최종 판정

**MMWAVE_LIVE_VALIDATION_PASS**

저장소의 standalone ESP32 mmWave firmware를 실제 장치에 올린 뒤, 실제 MR60BHA2 데이터가 production JSONL, 현재 `MR60ESPAdapter`, `PhaseRateEstimator`, 300-sample window, 실제 INT8 TFLite, V5 provider까지 통과했다. 정상 창 4개에서 실제 TFLite가 4회 실행됐고 fallback은 0회였다. 무인 평탄 신호는 추론되지 않고 명시적으로 거부됐으며, 유효 신호 복귀 후 새 창으로 정상 회복했다. 운영 알고리즘·모델·MR60 firmware는 변경하지 않았다.

## 2. ESP firmware flash 결과

| 항목 | 결과 |
|---|---|
| 대상 | ESP32-D0WD-V3 rev 3.1, 4 MB flash |
| PlatformIO 환경 | `devices/mmwave/firmware`, `esp32dev` |
| 빌드 | 성공 |
| RAM | 32,356 / 327,680 bytes, 9.9% |
| Flash program | 268,765 / 1,310,720 bytes, 20.5% |
| 업로드 | `/dev/cu.usbserial-110`, 성공, 기록 hash 검증 성공 |
| serial | 115200 baud |
| MR60 UART | RX/TX = 16/17 |
| ESP firmware | `safenest-mr60-esp/1.2.0` |
| MR60BHA2 firmware | 변경·flash하지 않음 |

검증 종료 시점에도 ESP32에는 standalone mmWave firmware가 설치되어 있다. 조원이 보관한 통합 다중 센서 firmware로 복원하지 않았다.

## 3. Production JSONL 확인

20초 원시 캡처 `identity_raw_20s.jsonl`에서 199개 레코드가 모두 JSON으로 파싱됐다.

| 항목 | 결과 |
|---|---|
| `schema_version` | 전부 `1.2` |
| firmware | 전부 `safenest-mr60-esp/1.2.0` |
| ESP config SHA-256 | `b817e8bfd5e52b18275626f7b6a9bd60098ea4b108428a5aaf63600dbc987834` |
| sequence | 118 → 316, 누락·중복·역행 0 |
| 실효 속도 | 9.994 Hz |
| JSON 파싱 오류 | 0 |
| UART/checksum/parser 오류 | 0/0/0 |
| presence | 199/199 true |
| distance | 34.44–63.14 cm |
| finite `breath_phase` | 199/199 |
| phase 범위 | -0.45–0.22 |
| 500 ms 초과 stale | 0 |

원시 캡처 SHA-256은 `1aa85bec50d1c521fb32c576912f55c5236b9058e64e1144e23cf7f607157d89`이다.

## 4. 실시간 Serial 품질

주 반복 세션은 120.282초 동안 1,201레코드를 수집했다.

| 항목 | 결과 |
|---|---|
| 실효 속도 | 9.990 Hz |
| interval mean/p50/p95/max | 0.100/0.100/0.101/0.103 s |
| 최대 stream gap | 0.103 s |
| sequence 누락/역행 | 0/0 |
| UART/checksum/parser 오류 | 0/0/0 |
| invalid phase/stale | 0/0 |
| presence loss | 0 |

각 모니터 세션의 `host_json_errors=1`은 연결 시작 시 받은 부분 line 또는 boot line을 host가 폐기한 횟수다. 별도 199레코드 원시 캡처는 JSON 오류 0이므로 지속적인 production JSONL 손상으로 판단하지 않는다.

## 5. 실제 300-sample window

정상 반복 세션에서 300-sample 창 3개가 모두 완성됐고 reset은 없었다. 마지막 provider-contract 세션에서도 300-sample 창 1개가 추가로 완성됐다.

| 창 | sample | 실제 창 길이 | 실효 Hz | presence | 결과 |
|---|---:|---:|---:|---|---|
| 반복 1 | 300 | 약 29.92 s | 9.992 | 세션 전체 유지 | 성공 |
| 반복 2 | 300 | 약 29.92 s | 9.992 | 세션 전체 유지 | 성공 |
| 반복 3 | 300 | 약 29.93 s | 9.990 | 세션 전체 유지 | 성공 |
| 공급자 계약 | 300 | 29.921 s | 9.993 | 세션 전체 유지 | 성공 |

공급자 계약 창의 interval min/median/max는 0.100/0.100/0.102초였고 최대 session gap은 0.103초였다. phase는 finite였고 stale은 없었다. 원시 serial 확인 구간의 distance 범위는 34.44–63.14 cm이며, 공급자 계약 창 종료 시 distance는 63.14 cm였다. 검증 모니터가 AI 창별 모든 distance 샘플을 원문으로 보존하지 않아 계약 창 자체의 정확한 min/max는 산출하지 않았다.

## 6. 실제 INT8 TFLite 추론

| 항목 | 결과 |
|---|---|
| 모델 경로 | `ondevice_ai/models/mmwave/mmwave_resp_int8_v0.1.0.tflite` |
| model ID/version | `mmwave_resp_int8` / `0.1.0` |
| SHA-256 | `43cdd6f321c2b645232162233e098c2b65549388cbc9e680a17a0eccdc8f0158` |
| manifest/hash 일치 | true |
| 입력 | `[1,300,1]`, `int8`, scale `0.03259856998920441`, zero point `-13` |
| 출력 | `[1,3]`, `int8`, scale `0.00390625`, zero point `-128` |
| 정상 반복 예측 | `NORMAL` 3/3 |
| 공급자 계약 예측 | class index 0, `NORMAL` |
| 확률 | `[1.0, 0.0, 0.0]` |
| 실제 TFLite 실행/fallback | 4/0 |

`confidence=1.0`과 정상 label 일치는 기능적 일관성 결과일 뿐, 의학적 정확도 100%를 의미하지 않는다.

## 7. V5 Provider

실제 serial로 `connect() → read() → close()` 경로를 사용했다. 마지막 이벤트에 전체 `InferenceResult.to_dict()`를 보존해 다음 계약을 확인했다.

| 필드 | 값 |
|---|---|
| `sensor_id` | `mmwave` |
| `timestamp` | `1786201357.982042` |
| `valid` | `true` |
| `state` / `score` | `NORMAL` / `0.0` |
| `confidence` | `1.0` |
| `latency_ms` | `99.714` |
| `error` | `null` |
| source | `REAL_MR60BHA2_ESP_SERIAL_JSONL` |
| communication/stale | `true` / `false` |
| model hash match | `true` |
| fallback | `false` |

전체 metadata에는 ESP schema/firmware/config hash, 300-sample 창 통계, 모델 식별자·해시, class index·확률, TFLite latency가 포함됐다. 증거 파일은 `live_provider_contract_1window.jsonl`, SHA-256은 `2a7fa3aaf9051b69fff7e68d3c6d53c28d7e091ffe7aaf3476c499632ce169a7`이다.

## 8. 반복 Live inference

정상 자연 호흡 조건에서 독립 종료 창 3개를 확보했다.

| 창 | 예측 | confidence | TFLite latency | provider latency | fallback | reset/error |
|---|---|---:|---:|---:|---|---|
| 1 | NORMAL | 1.0 | 3.603 ms | 106.632 ms | false | 없음 |
| 2 | NORMAL | 1.0 | 0.295 ms | 100.791 ms | false | 없음 |
| 3 | NORMAL | 1.0 | 0.526 ms | 101.453 ms | false | 없음 |

안전하지 않은 숨 참기·과호흡·무호흡 유도는 수행하지 않았다.

## 9. Fail-closed 검증

무인 상태 원시 캡처에서 vendor presence가 true에 고정됐지만 distance 97.58 cm, phase 0, breath/heart 0, `sensor_state=DEGRADED`, `error=LOCK_LOSS_FREEZE`, distance 표준편차 0의 lock-loss 상태가 관찰됐다. 따라서 vendor presence 비트만으로 정상 무인 이탈을 판정할 수 없었다.

그 상태를 65초 유지한 검증에서는 300샘플 버퍼가 `MMWAVE_PHASE_SIGNAL_TOO_FLAT`으로 명시적으로 거부됐다. 실제 TFLite 실행 0, fallback 0, `NORMAL`/`APNEA` 생성 0으로 invalid 입력을 정상·무호흡으로 위조하지 않았다. 이후 복귀 세션은 먼저 `MMWAVE_DISTANCE_INVALID`로 기존 상태를 reset한 뒤 새 300샘플을 모아 `NORMAL`로 성공했다. 따라서 이전 respiration/window의 무기한 재사용 없이 회복됨을 확인했다.

검증 과정에서 full buffer의 terminal error 집계가 누락되는 진단 모니터 버그를 발견해 검증 도구만 수정했다. production provider의 기존 fail-closed 동작과 모델은 변경하지 않았다.

## 10. 성능 지표

주 3-window 세션 기준:

| 구분 | 결과 |
|---|---|
| 통신 | 1,201 records, 9.990 Hz, sequence drop 0, UART/checksum/parser 0/0/0 |
| 창 | attempted/completed/failed = 3/3/0, reset 0 |
| TFLite | 3회, fallback 0 |
| TFLite latency mean/p50/p95/max | 1.474/0.526/3.295/3.603 ms |
| provider read latency mean/p50/p95/max | 99.899/99.924/101.926/109.077 ms |

provider read latency에는 약 10 Hz serial 다음 레코드를 기다리는 시간이 대부분 포함될 수 있다.

## 11. 테스트 결과

| 범위 | 결과 |
|---|---|
| `devices/mmwave/tests` (`test_mr60_manifest.py` 제외) | 46 passed |
| on-device input/interpreter/stream + V5 provider | 23 passed |
| 최종 패치 focused 묶음 | 32 passed |
| 문법 검사 | 통과 |

새 실패는 없다. `test_mr60_manifest.py`는 기존부터 누락된 `ondevice_ai/datasets/mmwave/mr60_20260728_manifest.json` 때문에 분리했다. 추가 통합 실행에서 확인된 `ondevice_ai/tests/test_v5_release.py` 3개 실패도 기존 archive/저장소 상대경로 가정 문제이며, 이번 mmWave 변경과 관련된 새 회귀가 아니다.

## 12. 생성/변경 파일

- 실측 결과와 보고서: `devices/mmwave/validation_results/final_live/2026-08-08_standalone_mmwave_attempt01/`
- 검증 도구: `devices/mmwave/tools/mmwave_performance_monitor.py`
- 검증 도구 테스트: `devices/mmwave/tests/test_mmwave_performance_monitor.py`
- 진행 기록: `PROJECT_PROGRESS.md`

검증 도구 변경은 terminal full-buffer 오류 집계와 provider 결과 증거 보존만을 위한 것이다. `devices/mmwave/src`, `devices/mmwave/include`, `devices/mmwave/firmware`, `ondevice_ai/models`, `ondevice_ai/inference`의 Git diff는 비어 있다. PIR, CO2, Thermal, dashboard, Risk Engine은 수정하지 않았고 stage/commit/push/merge도 하지 않았다.

## 13. 기존에 확인된 한계

- 20 rpm 저품질 window 문제는 해결됐다고 판단하지 않는다.
- 1.5 m 거리 한계는 해결됐다고 판단하지 않는다.
- stale `breath_phase` 한계는 해결됐다고 판단하지 않는다.
- MR60 vendor exit hysteresis/presence 고정 현상은 해결되지 않았다.
- 신뢰할 수 있는 실제 `ABNORMAL`/`APNEA` ground truth가 없어 의료 정확도를 검증하지 않았다.
- MR60 sensor firmware version 필드는 `null`이며, 이번 작업에서 MR60 firmware를 읽거나 변경하지 않았다.
- 통합 다중 센서 firmware의 로컬 backup은 만들지 않았고, 사용자 확인대로 조원이 보관한다.

## 14. 최종 결론

1. 실제 MR60 → ESP production JSONL은 정상인가? **예.** schema 1.2, 기대 firmware/config hash, 약 10 Hz와 오류 없는 연속 sequence를 확인했다.
2. 실제 `breath_phase` 300-sample window가 정상 생성되는가? **예.** 정상 창 4개가 완성됐다.
3. 실제 INT8 TFLite가 fallback 없이 실행되는가? **예.** 4회 실행, fallback 0회다.
4. V5 provider까지 정상 동작하는가? **예.** `sensor_id="mmwave"`, 유효 결과와 전체 metadata를 확인했다.
5. fail-closed가 유지되는가? **예.** 평탄/거리 무효 입력은 명시적으로 거부되고 가짜 NORMAL/APNEA를 만들지 않았으며, 신호 복귀 후 새 버퍼로 회복했다.
6. 새로운 regression이 있는가? **없음.** 관련 테스트가 모두 통과했고 production diff가 없다.
7. 현재 mmWave 개별 검증을 완료 상태로 판단해도 되는가? **예.** 위의 기존 한계를 해결한 것으로 확대 해석하지 않는 조건에서, 현재 production pipeline의 기능적 live validation은 완료됐다.
