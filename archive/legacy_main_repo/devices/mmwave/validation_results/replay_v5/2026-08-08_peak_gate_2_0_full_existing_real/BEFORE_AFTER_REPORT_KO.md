# MR60 Spectral Peak Quality Gate 전체 실측 회귀 비교

## 1. 최종 결정

- 실험한 변경: `minimum_spectral_peak_ratio = 2.0`
- After replay commit: `9058af58f1dfb9f0b4360f7e98d83c0f0db41650`
- 최종 채택: **REJECTED_REVERTED**
- Revert commit: `e8bdc73`
- 새 센서 측정: 없음
- Push/Merge: 없음

20 rpm의 잘못된 저품질 RPM은 제거됐지만, 31분 occupied coverage와 0.9 m 거리 coverage가 함께 하락했다. 사용자가 명시한 조건에 따라 이 threshold를 production에 최종 채택하지 않고 원복했다. After replay 산출물은 진단 증거로 보존한다.

## 2. 비교 조건

- Before: `devices/mmwave/validation_results/replay_v5/2026-08-08_full_existing_real/`
- After: `devices/mmwave/validation_results/replay_v5/2026-08-08_peak_gate_2_0_full_existing_real/`
- 동일 manifest: `devices/mmwave/tools/mmwave_replay_suite.json`
- 동일 실측 원본: 12개 dataset, 77,274 JSONL lines, analysis sensor records 71,313개
- 동일 model: `mmwave_resp_int8` v0.1.0
- 동일 model SHA-256: `43cdd6f321c2b645232162233e098c2b65549388cbc9e680a17a0eccdc8f0158`
- After model hash match: true

## 3. 전체 집계

| 지표 | Before | After | 변화 |
|---|---:|---:|---:|
| Attempted windows | 128 | 128 | 0 |
| Completed windows | 97 | 92 | -5 (-5.15%) |
| Rejected windows | 31 | 36 | +5 |
| 전체 window success | 75.78% | 71.88% | -3.91%p |
| Weak-spectrum rejects | 0 | 5 | +5 |
| Stale resets | 8 | 8 | 0 |
| TFLite runs | 97 | 92 | -5 |
| Fallback | 0 | 0 | 0 |
| Prediction | NORMAL 97 | NORMAL 92 | class GT 없는 창 포함 |
| Dataset PASS/PARTIAL | 8/4 | 7/5 | 0.9 m가 PARTIAL로 하락 |

## 4. 데이터셋별 Before/After

| Dataset | Before window | After window | Weak reject | Before→After result | 판정 |
|---|---:|---:|---:|---|---|
| empty_30min_v120 | 0/0 | 0/0 | 0 | PASS→PASS | 안전성 유지 |
| occupied_31min_v120 | 47/49 | 45/49 | 2 | PASS→PASS | coverage 회귀 |
| distance_0_6m | 9/10 | 9/10 | 0 | PASS→PASS | 유지 |
| distance_0_9m | 8/10 | 7/10 | 1 | PASS→PARTIAL | 회귀 |
| distance_1_2m | 7/9 | 7/9 | 0 | PARTIAL→PARTIAL | 유지 |
| distance_1_5m | 0/0 | 0/0 | 0 | PARTIAL→PARTIAL | 변화 없음 |
| paced_12rpm | 6/6 | 6/6 | 0 | PASS→PASS | 유지 |
| paced_15rpm | 6/6 | 6/6 | 0 | PASS→PASS | 유지 |
| paced_20rpm | 4/6 | 2/6 | 2 | PARTIAL→PARTIAL | 정확도 개선, coverage 하락 |
| entry_exit_20 | 1/22 | 1/22 | 0 | PARTIAL→PARTIAL | 유지 |
| accepted_empty_6min_v2 | 0/0 | 0/0 | 0 | PASS→PASS | 안전성 유지 |
| accepted_occupied_6min_v2 | 9/10 | 9/10 | 0 | PASS→PASS | 유지 |

## 5. 12/15/20 rpm 비교

| GT | 지표 | Before | After | 판정 |
|---:|---|---:|---:|---|
| 12 | Mean estimate | 11.972 | 11.972 | 동일 |
| 12 | MAE / ±2 rpm | 0.270 / 6/6 | 0.270 / 6/6 | 유지 |
| 15 | Mean estimate | 14.994 | 14.994 | 동일 |
| 15 | MAE / ±2 rpm | 0.275 / 6/6 | 0.275 / 6/6 | 유지 |
| 20 | Mean estimate | 15.996 | 19.450 | 개선 |
| 20 | MAE | 4.004 | 0.550 | 개선 |
| 20 | Max error | 9.246 | 1.004 | 개선 |
| 20 | ±2 rpm | 2/4 | 2/2 | valid output 품질 개선 |
| 20 | Window success | 4/6 (66.67%) | 2/6 (33.33%) | coverage 50% 감소 |

Gate는 `14.331`, `10.754 rpm` 창을 `MMWAVE_SPECTRAL_PEAK_WEAK`로 거부하고 `19.904`, `18.996 rpm`만 남겼다. 잘못된 값을 보정하지 않고 fail-closed한 점은 의도대로다. 그러나 새로운 유효 창을 만들지 못하므로 20 rpm coverage는 절반으로 감소했다.

## 6. 31분 occupied 회귀

| 지표 | Before | After | 변화 |
|---|---:|---:|---:|
| Presence continuity | 98.770% | 98.770% | 동일 |
| Usable breath phase | 82.725% | 82.725% | 동일 |
| Raw stale phase | 2,880/17,974 (16.023%) | 동일 | 동일 |
| Completed/attempted | 47/49 | 45/49 | -2 windows |
| Window success | 95.92% | 91.84% | -4.08%p |
| Weak-spectrum rejects | 0 | 2/49 (4.08%) | +2 |
| TFLite runs | 47 | 45 | -2 |
| Longest continuous inference | 1,230 s | 1,050 s | -180 s (-14.63%) |
| Fallback | 0 | 0 | 동일 |

이 회귀가 최종 철회의 직접 조건이다. Gate가 신뢰도 낮은 output을 줄이기는 하지만, 장시간 모니터링 availability를 함께 줄였다.

## 7. 거리 데이터

| 거리 | Before | After | Weak reject | 결과 |
|---:|---:|---:|---:|---|
| 0.6 m | 9/10 (90%) | 9/10 (90%) | 0 | 유지 |
| 0.9 m | 8/10 (80%) | 7/10 (70%) | 1 | PASS→PARTIAL, 회귀 |
| 1.2 m | 7/9 (77.78%) | 7/9 (77.78%) | 0 | 유지 |
| 1.5 m | 0/0 | 0/0 | 0 | 기존 distance-invalid 한계 그대로 |

0.9 m의 최장 연속 inference도 210초에서 90초로 감소했다. 1.5 m 문제는 이번 범위에서 다루거나 변경하지 않았다.

## 8. Empty-space 안전성

- Empty 30분: Before/After 모두 false presence 0, AI window 0, false NORMAL 0, false APNEA 0.
- Accepted empty 6분: Before/After 모두 AI window 0.
- Absence는 계속 `MMWAVE_PRESENCE_NOT_DETECTED`로 fail-closed했다.
- Spectral gate 때문에 empty-space 안전성이 악화되지는 않았다.

## 9. Entry/Exit 20회

- Entry 20/20, 평균 1.134초: 동일.
- Exit 19/20, 평균 15.491초: 동일.
- Window 1/22, stale reset 8: 동일.
- Vendor exit hysteresis: 동일.
- Spectral weak rejection: 0.

## 10. Stale / Weak-spectrum 비율

- 전체 analysis raw stale: Before/After 모두 `9,929/71,313 = 13.923%`.
- 전체 stale reset: Before/After 모두 `8/128 = 6.25%`.
- After weak-spectrum reset: `5/128 = 3.906%`.
- Weak-spectrum 분포: occupied 31분 2건, distance 0.9 m 1건, paced 20 rpm 2건.
- Gate는 stale 문제를 개선하지 않으며 별도의 5개 window rejection을 추가했다.

## 11. TFLite 결과

- Before: actual TFLite 97, fallback 0.
- After: actual TFLite 92, fallback 0.
- Model ID/version/hash는 동일하고 hash 검증도 통과했다.
- TFLite 자체의 안정성은 유지됐지만 upstream gate로 전달되는 real window가 5개 줄었다.

## 12. 최종 채택 여부

**채택하지 않음.**

이유:

1. 20 rpm valid output 정확도는 개선됐다.
2. 12/15 rpm 및 empty safety는 유지됐다.
3. 그러나 31분 occupied window가 47→45, 최장 연속 inference가 1,230→1,050초로 감소했다.
4. 0.9 m도 8→7 windows, PASS→PARTIAL로 하락했다.
5. 사용자는 장시간 coverage가 악화되면 production 변경을 최종 채택하지 말라고 명시했다.

따라서 `9058af5`는 `e8bdc73`으로 revert했다. 현재 production `PhaseRateEstimator`와 `mmwave_processing.json`에는 peak ratio gate가 남아 있지 않다.

## 13. 다음 권고

고정 threshold를 production에 다시 넣지 않는다. 다음 후보는 별도 승인 후 diagnostic-only로 검증해야 한다.

- hard reset 없이 rolling window를 유지하면서 weak spectrum을 일시 UNKNOWN 처리하는 정책
- 단일 threshold 대신 peak ratio와 temporal consistency를 결합한 품질 판단
- 31분 occupied와 0.9 m에서 거부된 정확한 두/한 창의 시간축 분석
- 어떠한 후보도 12/15, empty, long occupied, distance 전체 suite를 동시에 통과해야 한다.

## 14. 검증

- 동일 12-dataset manifest replay 완료.
- Before/After source와 model hash 일치.
- After output JSON/JSONL parse 및 window count 검증 대상.
- Production gate 관련 focused suite 적용 시 37 passed.
- 변경 관련 전체 mmWave suite 38 passed; historical-only manifest 부재로 기존 `test_mr60_manifest.py` 2건은 범위 밖 `FileNotFoundError`.
- On-device mmWave tests 17 passed.

## 15. 결론

`peak_ratio >= 2.0`은 20 rpm의 잘못된 RPM을 안전하게 제거하는 데는 성공했지만, SafeNest의 중요한 장시간·거리 coverage를 희생했다. 따라서 이 고정 gate는 현재 production에 적합하지 않으며 원복이 올바른 결정이다. After replay 데이터는 향후 temporal quality gate 설계의 근거로만 사용한다.
