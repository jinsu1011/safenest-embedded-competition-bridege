# 기존 MR60 실측 데이터 기반 V5 AI 성능 검증

## 1. 최종 판정

- Replay benchmark: **PARTIAL**
- 새 실험 필요성: **NO_NEW_COLLECTION_NEEDED_NOW**
- 재학습 필요성: **RETRAIN_NOT_JUSTIFIED**

현재 파이프라인으로 기존 실측 로그를 재생하고 실제 INT8 TFLite 추론까지 수행하는 데는 성공했다. 다만 1.5 m에서 유효 창이 없고, 20 rpm 및 입·퇴실 로그에서 창 신뢰성이 낮으며, ABNORMAL/APNEA 실측 class ground truth가 없어 전체 3-class 정확도를 검증할 수 없다.

## 2. 발견된 기존 데이터

- Real: 현재 `devices/mmwave/firmware/logs/` 아래 JSONL 78개, 172,390줄. 이 benchmark에는 대표 실측 원본 12개, 77,274줄(센서 레코드 76,858개)을 사용했다.
- Synthetic: `ondevice_ai/datasets/mmwave/processed/mmwave_respiration_v1.npz`는 생성 스크립트가 sine/flat/noise 배열을 만드는 synthetic 학습 데이터이므로 실측 성능 통계에서 제외했다.
- Unavailable: 신뢰 가능한 실측 ABNORMAL/APNEA class ground truth와 공개 `db_records` 원본은 저장소에서 확인되지 않았다.
- Historical-only: 승인 데이터 manifest `SafeNest_V4_OnDevice_AI/datasets/mmwave/mr60_20260728_manifest.json`은 현재 트리에는 없고 Git ref `b0d3c95`에 존재한다. 해당 manifest가 가리키는 실측 원본 6개는 현재 경로에 있으며 SHA-256이 일치한다.
- 최종 검증 manifest의 과거 `firmware/esp_wroom32_mr60_monitor/...` 경로는 현재 `devices/mmwave/firmware/...`로 이동했다.

## 3. 데이터별 Replay 가능 여부

| Dataset | 실측 여부 | Schema | Ground truth | 분류 | Replay 결과 |
|---|---|---|---|---|---|
| empty 30 min | Real | 1.2 | ABSENT | A. REAL_REPLAY_READY | PASS |
| occupied 31 min | Real | 1.2 | PRESENT | A. REAL_REPLAY_READY | PASS(단, 연속성 한계) |
| distance 0.6/0.9/1.2/1.5 m | Real | 1.0 | PRESENT, 기존 NORMAL 표기 | B. REAL_REPLAY_NEEDS_ADAPTER | 0.6/0.9 PASS, 1.2/1.5 PARTIAL |
| paced 12/15/20 rpm | Real | 1.0 | rpm만 존재 | B. REAL_REPLAY_NEEDS_ADAPTER | 12/15 PASS, 20 PARTIAL |
| entry/exit 20 trials | Real | 1.0 | cue 기반 입·퇴실 | B. REAL_REPLAY_NEEDS_ADAPTER | PARTIAL |
| accepted empty/occupied 6 min v2 | Real | 1.0 | ABSENT/PRESENT | B. REAL_REPLAY_NEEDS_ADAPTER | PASS |
| 파생 CSV delivery | Real-derived | CSV | 일부 scenario | C. REAL_NOT_SUITABLE_FOR_V5_AI | raw가 있어 replay 입력에서 제외 |
| `mmwave_respiration_v1.npz` | Synthetic | NPZ | 생성 라벨 | D. SYNTHETIC | 실측 통계에서 제외 |
| 신뢰 가능한 실측 abnormal/apnea | 없음 | - | 없음 | E. UNKNOWN/Unavailable | 정확도 평가 불가 |

Schema 1.2는 strict provenance로 처리했다. Schema 1.0은 같은 `MR60ESPAdapter` 처리·검증·300-sample window 로직을 사용하되, 구형 로그임을 명시한 compatibility 모드로만 처리했다.

## 4. 거리별 결과

분석 구간은 각 300초이며, confidence는 모두 1.0으로 포화되어 분류 정확도와 동일시할 수 없다.

| 거리 | Presence | 유효 phase | 유효 창/시도 | TFLite | 예측 | p95 latency | 판정 |
|---:|---:|---:|---:|---:|---|---:|---|
| 0.6 m | 100.00% | 100.00% | 9/10 (90.00%) | 9 | NORMAL 9 | 0.193 ms | PASS |
| 0.9 m | 100.00% | 100.00% | 8/10 (80.00%) | 8 | NORMAL 8 | 0.167 ms | PASS |
| 1.2 m | 81.42% | 81.42% | 7/9 (77.78%) | 7 | NORMAL 7 | 0.143 ms | PARTIAL |
| 1.5 m | 88.00% | 0.00% | 0/0 | 0 | 없음 | - | PARTIAL |

1.2 m부터 presence 손실이 보이며, 1.5 m는 presence가 일부 유지돼도 distance가 전부 무효이고 phase가 stale이라 AI 입력을 만들 수 없다. 이는 모델 재학습보다 센서 유효 범위/배치 문제다.

## 5. 호흡수 결과

각 속도는 180초 측정 구간을 현재 estimator로 다시 계산했다. 아래 estimated는 유효 창 추정치의 평균이다.

| GT | Estimated | MAE | Max error | ±2 rpm | 유효 창/시도 | 판정 |
|---:|---:|---:|---:|---:|---:|---|
| 12 rpm | 11.972 rpm | 0.270 rpm | 0.566 rpm | 6/6 (100%) | 6/6 | PASS |
| 15 rpm | 14.994 rpm | 0.275 rpm | 0.657 rpm | 6/6 (100%) | 6/6 | PASS |
| 20 rpm | 15.996 rpm | 4.004 rpm | 9.246 rpm | 2/4 (50%) | 4/6 | PARTIAL |

- 전체 16개 유효 창 기준 가중 MAE: 1.205 rpm.
- 전체 최대 오차: 9.246 rpm.
- 전체 ±2 rpm 충족: 14/16(87.5%).
- 20 rpm의 예측 NORMAL은 rpm ground truth를 class label로 변환한 결과가 아니다. 해당 로그의 AI class 정확도는 계산하지 않았다.

## 6. Presence / Entry / Exit 결과

- 20회 입실: 20/20 감지, 평균 1.134초, 중앙값 1.073초, p95 2.228초, 최대 2.449초. 2초 이내는 16/20.
- 20회 퇴실: 19/20 release 감지, 1회 미감지. 성공 19회의 평균 15.491초, 중앙값 15.814초, p95 17.116초, 최대 17.713초. 2초 이내는 0/19.
- vendor hysteresis가 퇴실 지연을 지배한다.
- cue 기반 구간 전체에서 22개 창을 시도했으나 1개만 완성됐다. reset은 no presence 8, invalid distance 5, stale phase 8건이었다.
- transitional 로그에서 나온 NORMAL 1건은 class ground truth가 없으므로 정답/오답으로 판정하지 않았다.

## 7. Empty-space 결과

- 최장 empty 실측: 1,799.781초, 센서 레코드 17,995개.
- false presence: 0/17,995, empirical false-presence rate 0.000%.
- 생성된 유효 AI 창: 0개.
- false NORMAL: 0개.
- false APNEA: 0개.
- fail-closed event: `MMWAVE_PRESENCE_NOT_DETECTED` 17,995개.

즉 PERSON ABSENT 상태에서 respiration inference를 만들지 않았으며 NORMAL/APNEA로 오인하지 않았다.

## 8. 장시간 사람 있음 결과

- 분석 구간: 초기 60초 제외 후 1,799.751초.
- Presence continuity: 98.770%(17,753/17,974).
- usable breath_phase ratio: 82.725%(14,869/17,974).
- stale phase ratio: 16.023%(2,880/17,974).
- 유효 창/시도: 47/49(95.92%), reject/reset 2개(`MMWAVE_DISTANCE_INVALID`).
- 실제 TFLite: 47회, fallback 0회.
- 최장 연속 유효 inference 구간: 1,230초(41창).

Historical comparison: 과거 firmware-side 평가는 중간 25분 filtered-valid 25.90%, low-amplitude 69.95%로 `PRESENCE_PASS_BREATH_CONTINUITY_FAIL`이었다. 현재 adapter는 동일 raw에서 더 많은 창을 만들지만 quality gate와 전처리 정의가 과거 분석과 다르다. 따라서 판정은 **C. schema/preprocessing 차이 때문에 직접 비교 불가**이며, “개선됐다”고 주장하지 않는다. 현재도 stale phase 16.02%와 570초에 해당하는 비연속 구간이 남아 장시간 호흡 연속성 한계는 해소됐다고 볼 수 없다.

## 9. V5 TFLite 결과

- Real valid windows / actual TFLite runs: 97/97.
- Fallback: 0.
- Prediction distribution: NORMAL 97, ABNORMAL 0, APNEA 0.
- Latency: mean 0.184 ms, p50 0.104 ms, p95 0.219 ms, max 5.753 ms.
- Confidence: 97개 모두 1.0. 이는 양자화 모델 출력 포화/교정 문제를 점검할 신호이지 100% 정확도의 증거가 아니다.
- 모델: `mmwave_resp_int8` v0.1.0, SHA-256 `43cdd6f321c2b645232162233e098c2b65549388cbc9e680a17a0eccdc8f0158`, manifest hash 일치.

## 10. 정확도에 대해 말할 수 있는 것 / 없는 것

- 말할 수 있음: known-present/absent 로그의 presence 비율, paced 로그의 rpm 오차, window 성공률, 실제 TFLite 실행 수·latency·fallback, prediction distribution.
- 제한적으로 말할 수 있음: 기존 데이터가 명시적으로 NORMAL로 표기한 거리 조건에서 생성된 24개 창은 NORMAL 24/24와 일치했다. 단일 정상 class·단일 실험 계열이므로 일반화된 3-class 정확도가 아니다.
- 말할 수 없음: ABNORMAL/APNEA recall·precision·specificity, 전체 3-class accuracy, 의료 진단 성능. 나머지 73개 창에는 신뢰 가능한 AI class ground truth가 없다.
- confidence 1.0을 정확도 100%로 해석하지 않는다. absence, null, timeout을 APNEA로 해석하지 않는다.

## 11. 현재 가장 큰 병목

- P0: 신뢰 가능한 real ABNORMAL/APNEA class ground truth 부재. 모델 정확도와 안전성을 검증할 수 없다.
- P1: signal/window availability. 1.5 m는 0창, 20 rpm은 4/6창, entry/exit는 1/22창이며 장시간 로그에도 stale phase가 16.02% 존재한다.
- P2: 실제 TFLite 출력이 모든 유효 창에서 NORMAL/confidence 1.0으로 포화된다. 라벨 있는 다양한 실제 창을 확보하기 전에는 calibration과 class discrimination을 판단할 수 없다.

## 12. 새 측정이 필요한가?

**NO_NEW_COLLECTION_NEEDED_NOW**

현재 사용자가 새 MR60 실험을 수행할 필요는 없다. 기존 데이터만으로 다음 engineering step인 window failure 원인 분해, 1.2~1.5 m 운영 범위 제한, vendor exit hysteresis의 Thermal/PIR fusion 설계, 모델 입력·출력 calibration 감사까지 진행할 수 있다. 특히 위험한 apnea/hyperventilation 실험은 요청하지 않는다.

향후 class 성능 평가에는 사람 대상 새 실험보다 먼저 라이선스·출처·라벨이 확인된 외부 실측 abnormal/apnea 데이터 또는 윤리 승인된 데이터가 필요하다. 이것이 확보되기 전에는 구체적인 사용자 추가 측정을 승인하지 않는다.

## 13. AI 재학습이 필요한가?

**RETRAIN_NOT_JUSTIFIED**

현재 실패의 다수는 모델 입력 이전의 presence/distance/stale/window 문제다. 또한 clean valid window가 잘못 분류됐다고 증명할 ABNORMAL/APNEA ground truth가 없다. 현재 synthetic 기반 모델을 즉시 재학습하면 실측 성능 향상을 검증할 기준이 없다. 먼저 라벨 provenance와 domain gap을 확보하고, 그 뒤 clean valid windows에서 반복적인 오분류가 확인될 때 재학습을 검토해야 한다.

## 14. 추가/수정 파일

- `devices/mmwave/tools/mmwave_v5_replay_benchmark.py`: batch replay/metric/progress/output 도구.
- `devices/mmwave/tools/mmwave_replay_suite.json`: 12개 대표 실측 dataset suite.
- `devices/mmwave/tests/test_mmwave_v5_replay_benchmark.py`: schema, fail-closed, GT 분리, gap/stale, hysteresis 테스트.
- `devices/mmwave/validation_results/replay_v5/2026-08-08_full_existing_real/`: per-window JSONL 12개, per-dataset JSON 12개, summary JSON/CSV, 보고서.

원본 JSONL, ESP firmware, MR60 firmware, TFLite 모델, 학습 코드, dashboard는 수정하지 않았다.

## 15. 테스트 결과

검증 명령:

```text
PYTHONPATH=/opt/anaconda3/lib/python3.12/site-packages \
  /private/tmp/safenest-mmwave-v5-env/bin/python -m pytest \
  devices/mmwave/tests/test_mmwave_v5_replay_benchmark.py \
  devices/mmwave/tests/test_mmwave_performance_monitor.py \
  devices/mmwave/tests/test_mmwave_v5_provider.py \
  devices/mmwave/tests/test_mr60_esp_adapter.py \
  ondevice_ai/tests/test_mmwave_interpreter.py

/private/tmp/safenest-mmwave-v5-env/bin/python \
  devices/mmwave/tools/mmwave_v5_replay_benchmark.py \
  --manifest devices/mmwave/tools/mmwave_replay_suite.json \
  --output-dir devices/mmwave/validation_results/replay_v5/2026-08-08_full_existing_real
```

- Core test suite: 33 passed.
- Replay: 12/12 datasets 처리 완료, invalid JSON 0, output JSON parsing 성공.
- Per-window line count와 dataset `completed_windows`: 97/97 일치.
- 12개 source SHA-256 재계산값과 결과 provenance: 전부 일치.
- 실제 TFLite 97회, fallback 0회.
- Benchmark tool commit: `6da2a7141af758ed4eebba61a7f09950022deb7b`.

## 16. 최종 결론

1. 기존 GitHub 실측 데이터만으로 presence, 거리 한계, 호흡수 추정, 300-sample window 신뢰성, 실제 TFLite 실행/latency/fallback은 충분히 재검증할 수 있다. 그러나 전체 3-class 정확도는 검증할 수 없다.
2. 실제 성능은 empty fail-closed와 0.6~0.9 m, 12~15 rpm에서 양호하다. actual TFLite는 97회 모두 fallback 없이 빠르게 실행됐다.
3. 1.2 m부터 presence/window가 저하되고, 1.5 m에서는 AI 입력이 사라진다. 20 rpm, 입·퇴실 전환, 장시간 stale phase에서도 약하다.
4. 지금 사용자에게 새 센서 측정을 요청할 필요는 없다.
5. 지금 AI를 재학습할 근거도 부족하다.
6. 대회 성능 향상을 위한 첫 작업은 모델이 아니라 입력 품질이다. 현재 로그로 window reset 원인을 시간축에서 분해하고, MR60 단독의 약점을 1.2 m 운영 범위 제한과 Thermal/PIR 기반 즉시 퇴실 보완으로 명시한 뒤, 출처가 검증된 실측 class ground truth 확보 계획을 세워야 한다.
