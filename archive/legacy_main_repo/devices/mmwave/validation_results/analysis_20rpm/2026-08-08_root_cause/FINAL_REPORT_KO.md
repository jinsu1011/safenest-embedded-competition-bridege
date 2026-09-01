# mmWave 20 rpm 호흡수 추정 오차 원인 분석

## 1. 최종 판정

- Root cause: **I. MULTIPLE_CONTRIBUTING_FACTORS**
- Code change: **CHANGE_RECOMMENDED**
- 생산 코드 변경 여부: 이 분석에서는 변경하지 않음
- TFLite 재학습: 필요 없음. 오차는 TFLite 이전의 호흡수 estimator에서 발생한다.

20 rpm의 약 16 rpm 결과는 네 유효 창 `14.331, 10.754, 19.904, 18.996 rpm`의 산술평균 `15.996 rpm`이다. 처음 두 창의 raw phase에는 신뢰할 만한 단일 20 rpm peak가 없었지만, 현재 estimator가 낮은 spectral peak ratio를 유효성 판단에 사용하지 않아 가장 큰 저주파 peak를 그대로 정상값으로 내보냈다. 이후 두 창에서는 같은 알고리즘이 20 rpm을 정상적으로 찾았다.

## 2. 사용한 실측 데이터

- 12 rpm: `devices/mmwave/firmware/logs/breath/2026-07-28_breath_paced_12rpm_explicit_v2_attempt03.jsonl`
- 15 rpm: `devices/mmwave/firmware/logs/breath/2026-07-28_breath_paced_15rpm_explicit_full_v3.jsonl`
- 20 rpm: `devices/mmwave/firmware/logs/breath/2026-07-28_breath_paced_20rpm_explicit_full_v2.jsonl`

모두 실제 MR60BHA2 로그이며, cue가 명시한 `measurement` 시작부터 180초를 사용했다. 세 조건은 같은 피험자, 착석, 흉부 정면, 약 0.8–0.9 m, 60초 paced warmup 뒤 180초 paced measurement 조건이다. 원본 JSONL은 수정하지 않았다.

## 3. 데이터 품질 비교

| GT | 레코드 | 기간 | Effective Hz | dt min/median/max | 유효 phase | Sequence gap | Stream gap | Presence | Distance | phase std | 스펙트럼 분석 |
|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|---|
| 12 | 1,800 | 179.981 s | 9.99550 | 0.100/0.100/0.101 s | 100% | 0 | 0 | 100% | 100% | 0.377 | 적합 |
| 15 | 1,800 | 179.968 s | 9.99622 | 0.100/0.100/0.102 s | 100% | 0 | 0 | 100% | 100% | 0.393 | 적합 |
| 20 | 1,800 | 179.963 s | 9.99650 | 0.100/0.100/0.102 s | 100% | 0 | 0 | 98.611% | 98.611% | 0.252 | 구간별 적합; presence loss 2.5 s 존재 |

- NaN/Inf: 0.
- stale phase: 0.
- 20 rpm은 전체 phase 표준편차가 12/15 rpm보다 각각 약 33%, 36% 낮다.
- 20 rpm의 continuous usable segment는 1,310 samples와 465 samples로 나뉜다. 중간 25 samples의 presence/distance loss가 window를 reset하고 이후 60초 warmup 때문에 후반부 valid output을 제한한다.

## 4. 현재 알고리즘 구조

`devices/mmwave/src/mr60_esp_adapter.py`의 `PhaseRateEstimator.estimate()`는 다음 순서다.

```text
real breath_phase + timestamps
→ 300 samples / nominal 10 Hz / 30 s
→ 10 Hz uniform grid로 np.interp
→ 1차 직선 detrending
→ phase std >= 0.05 검사
→ Hann window
→ nfft=4096 zero-padded rFFT
→ 5–40 rpm band
→ magnitude가 가장 큰 bin 선택
→ 인접 3-bin 포물선 보간
→ peak / band median으로 peak_ratio 및 confidence 계산
→ rpm 반환
```

중요한 사실은 `peak_ratio`와 `confidence`를 계산하지만 이를 validity gate로 사용하지 않는다는 것이다. smoothing, 이전 rate prior, harmonic/subharmonic 판별, 복수 후보 quality ranking도 없다.

## 5. 12 rpm 분석

- Expected frequency: `12/60 = 0.200 Hz`.
- 6개 선택값: `12.162, 11.912, 11.701, 12.566, 11.631, 11.862 rpm`.
- 평균 estimate: `11.972 rpm`.
- MAE: `0.270 rpm`; max error: `0.566 rpm`; ±2 rpm: `6/6`.
- peak ratio 범위: `8.175–31.677`.
- 대표 1번 창의 선택 peak: `12.162 rpm`; 두 번째 peak `17.282 rpm`은 선택 peak의 17.8%에 불과했다.

12 rpm은 모든 창에서 목표 주파수 주변 peak가 명확했다.

## 6. 15 rpm 분석

- Expected frequency: `15/60 = 0.250 Hz`.
- 6개 선택값: `15.060, 15.090, 14.642, 15.657, 14.670, 14.847 rpm`.
- 평균 estimate: `14.994 rpm`.
- MAE: `0.275 rpm`; max error: `0.657 rpm`; ±2 rpm: `6/6`.
- peak ratio 범위: `5.088–10.107`.
- 대표 1번 창의 선택 peak: `15.060 rpm`; 두 번째 peak `20.549 rpm`은 선택 peak의 20.2%였다.

15 rpm도 모든 창에서 목표 peak가 지배적이었다.

## 7. 20 rpm 분석

- Expected frequency: `20/60 = 0.333333 Hz`.
- 유효 replay 창: 4개. Presence loss reset 1개와 후반 insufficient history가 있었다.

| 창 | phase std | 선택 peak | 주요 다른 peak | GT bin 상대 크기 | peak ratio | 오차 | 판정 |
|---:|---:|---:|---|---:|---:|---:|---|
| 1 | 0.164 | 14.331 rpm | 6.509(94.5%), 18.677(81.7%), 23.777(77.3%) | 58.1% | 1.660 | 5.669 | 저품질인데 유효 처리 |
| 2 | 0.208 | 10.754 rpm | 18.298(89.2%), 26.774(66.7%) | 75.5% | 1.595 | 9.246 | 저품질인데 유효 처리 |
| 3 | 0.223 | 19.904 rpm | 12.312(20.7%), 24.953(19.8%) | 99.6% | 10.995 | 0.096 | 정상 |
| 4 | 0.271 | 18.996 rpm | 9.955(42.8%), 23.583(36.4%) | 85.0% | 5.057 | 1.004 | 정상 |

첫 두 창은 대역 전체가 평탄하고 여러 후보가 비슷하다. 코드의 `np.argmax`는 구현된 규칙대로 14.331과 10.754 rpm을 선택했지만, 해당 peak가 호흡을 대표한다고 볼 spectral concentration이 없었다. 반대로 뒤 두 창은 19–20 rpm peak가 명확하다.

과거 전체 180초 분석의 dominant phase rate는 `20.011 rpm`이었다. 따라서 원본 전체에서 20 rpm 정보가 사라졌거나 search band 밖에 있는 것이 아니다. 짧은 창별 신호 품질이 비균일하며, 현재 validity logic이 이를 걸러내지 않는 것이 약 16 rpm 평균의 직접 원인이다.

## 8. 가설별 검증

- FFT resolution: 30초 관측의 독립 해상도는 약 `1/30 = 0.03333 Hz = 2 rpm`. 16과 20 rpm은 4 rpm 차이이므로 구분 가능하다. 4096 zero-padding의 표시 bin 간격 `0.002441 Hz = 0.1465 rpm`은 실제 정보 해상도를 높이지 않는다. 주원인 아님.
- Search band: 5–40 rpm이며 20 rpm/0.333 Hz는 완전히 포함된다. 원인 아님.
- Sampling-rate mismatch: 실측 9.9955–9.9965 Hz를 사용해도 20 rpm MAE가 `4.0036 → 4.0032 rpm`만 변했다. 원인 아님.
- Spectral leakage/window: Rectangular는 일부 개선했지만 20 rpm 첫 창이 `12.573 rpm`, max error `7.427 rpm`으로 남았다. Blackman은 20 rpm MAE `6.066 rpm`으로 악화됐다. Hann 단독 문제가 아님.
- Subharmonic: 14.331 rpm은 20 rpm의 정수 subharmonic이 아니며, 10.754 rpm도 정확한 1/2인 10 rpm이 아니다. 코드에도 subharmonic 선택 규칙이 없다. 저품질 창의 별도 저주파 성분이다.
- Detrending: mean/linear/quadratic의 전체 MAE가 각각 `1.2058/1.2054/1.2049 rpm`으로 동일하다. 원인 아님.
- Window length: 90초 diagnostic은 20 rpm 한 창을 `20.229 rpm`으로 만들었지만 출력 지연 증가, 창 수 감소, 300-sample TFLite 계약 불일치 때문에 현재 구조의 최소 수정이 아니다.
- SNR: 20 rpm 첫 두 창의 peak ratio `1.660/1.595`가 12 rpm 최저 `8.175`, 15 rpm 최저 `5.088`, 정상 20 rpm 창 `5.057/10.995`보다 현저히 낮다. 핵심 원인.
- Presence loss: 잘못된 첫 두 값을 만들지는 않았지만 후반 valid 창을 줄여 평균과 연속성을 악화시키는 보조 요인이다.

## 9. 원인

**I. MULTIPLE_CONTRIBUTING_FACTORS**로 분류한다.

1. `DATASET_QUALITY_ISSUE`: 20 rpm 처음 60초의 raw breath_phase가 비정상적으로 낮은 spectral concentration과 여러 경쟁 peak를 보였다.
2. `PEAK_SELECTION/VALIDITY ISSUE`: estimator는 어떤 peak든 대역 내 최댓값이면 유효 rate로 반환한다. 이미 계산한 peak ratio와 confidence가 rejection에 사용되지 않는다.
3. Presence loss와 60초 재-warmup이 뒤쪽 양질 창의 수를 줄였다.

주원인을 하나의 단계로 표현하면 **frequency 계산 자체가 아니라, 저-SNR spectrum을 유효값으로 승인하는 estimator validity 단계**다.

## 10. 수정 후보 비교

| Method | 12 rpm MAE | 15 rpm MAE | 20 rpm MAE | Overall MAE | Max error | ±2 rpm | Coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| Current Hann + no spectral gate | 0.270 | 0.275 | 4.004 | 1.205 | 9.246 | 14/16 | 16/16 |
| Candidate A: peak ratio ≥2.0 fail-closed | 0.270 | 0.275 | 0.550 | 0.312 | 1.004 | 14/14 | 14/16 |
| Candidate B: Rectangular window | 0.286 | 0.096 | 2.107 | 0.670 | 7.427 | 15/16 | 16/16 |
| Actual sample rate | 0.271 | 0.274 | 4.003 | 1.205 | 9.245 | 14/16 | 16/16 |
| Blackman window | 0.284 | 0.283 | 6.066 | 1.729 | 13.395 | 14/16 | 16/16 |

Candidate A만 기존 12/15 rpm 12개 창을 모두 유지하면서 잘못된 20 rpm 두 창을 fail-closed했다. 이는 20 rpm 값을 억지로 보정하는 방식이 아니다. 다만 threshold `2.0`은 세 paced 로그에서 얻은 diagnostic 후보이며, production 확정값으로 채택하기 전에 전체 기존 실측 suite를 재검증해야 한다.

## 11. 회귀 위험

- spectral gate가 너무 높으면 약한 정상 호흡 창을 과도하게 UNKNOWN으로 만들 수 있다.
- gate 실패 시 estimator buffer를 즉시 reset하면 회복 시간이 길어질 수 있다. Rolling window를 유지하고 다음 sample에서 재평가하는 편이 안전하다.
- confidence mapping `(peak_ratio-1)/9`와 새 validity threshold의 의미가 중복될 수 있으므로 하나의 명시적 config 계약이 필요하다.
- 12/15 paced만으로 threshold를 일반화하면 안 된다. distance 0.6–1.2 m, occupied 6/31분, empty fail-closed, gap/stale/NaN/presence-loss 테스트를 모두 재실행해야 한다.
- window function을 rectangular로 바꾸는 것은 leakage와 noise susceptibility를 늘리며 첫 실패도 제거하지 못하므로 권고하지 않는다.

## 12. 수정 권고

- File: `devices/mmwave/src/mr60_esp_adapter.py`
- Class/function: `PhaseRateEstimator.estimate()`
- Config: `devices/mmwave/config/mmwave_processing.json`
- 현재 동작: `peak_ratio`와 `confidence`를 계산한 뒤 threshold 없이 `valid=True`를 반환한다.
- 최소 변경안: config에 검증된 `minimum_spectral_peak_ratio`를 추가하고, `peak_ratio`가 기준 미만이면 rpm을 반환하지 않고 `MMWAVE_SPECTRAL_PEAK_WEAK`로 fail-closed한다. 기존 buffer를 유지해 rolling 재평가가 가능하도록 설계한다.
- 현재 diagnostic 후보: `peak_ratio >= 2.0`.
- 기대 효과: 잘못된 20 rpm 창 14.331/10.754를 제외하고, 남은 20 rpm 창을 19.904/18.996 rpm으로 유지한다. 12/15 rpm 창에는 변화가 없다.
- Production 적용 여부: **아직 적용하지 않음. 사용자 승인 후 전체 historical regression과 함께 별도 변경해야 한다.**

## 13. 테스트/분석 명령

```text
/opt/anaconda3/bin/python devices/mmwave/tools/mmwave_20rpm_root_cause.py \
  --output-dir devices/mmwave/validation_results/analysis_20rpm/2026-08-08_root_cause

PYTHONPATH=/opt/anaconda3/lib/python3.12/site-packages \
  /private/tmp/safenest-mmwave-v5-env/bin/python -m pytest -q \
  devices/mmwave/tests/test_mmwave_20rpm_root_cause.py \
  devices/mmwave/tests/test_mmwave_v5_replay_benchmark.py \
  devices/mmwave/tests/test_mmwave_performance_monitor.py \
  devices/mmwave/tests/test_mmwave_v5_provider.py \
  devices/mmwave/tests/test_mr60_esp_adapter.py \
  ondevice_ai/tests/test_mmwave_interpreter.py

python3 -m py_compile \
  devices/mmwave/tools/mmwave_20rpm_root_cause.py \
  devices/mmwave/tests/test_mmwave_20rpm_root_cause.py
```

- 결과: `36 passed`.
- Pure synthetic 20 rpm sanity test는 current FFT가 20 rpm을 ±0.1 rpm 안에서 분해할 수 있음을 확인하는 unit test에만 사용했으며, 실측 성능 통계에는 포함하지 않았다.
- Real integration test는 20 rpm 창의 peak ratio가 `[<2, <2, ≥2, ≥2]`이고 12/15 rpm 12개 창은 모두 ≥2임을 확인했다.

## 14. 생성한 분석 파일

- `devices/mmwave/tools/mmwave_20rpm_root_cause.py`: diagnostic-only 분석 도구.
- `devices/mmwave/tests/test_mmwave_20rpm_root_cause.py`: 해상도와 real-window 분리 회귀 테스트.
- `analysis_summary.json`: dataset quality, 창별 spectrum, 후보 비교.
- `production_windows.csv`: production-equivalent 창별 수치.
- `time_domain_12_15_20rpm.png`: 세 실측 phase 시간축.
- `spectrum_12rpm.png`, `spectrum_15rpm.png`, `spectrum_20rpm.png`: 목표/선택 peak 시각화.

원본 로그, production estimator, config, TFLite 모델, ESP/MR60 firmware는 수정하지 않았다.

## 15. 최종 결론

1. **20 rpm이 왜 약 16 rpm인가?** 네 창 중 처음 두 저-SNR 창에서 14.331과 10.754 rpm이 선택됐고, 뒤의 정상 19.904와 18.996 rpm을 함께 평균해 15.996 rpm이 됐다.
2. **센서 신호 문제인가, 알고리즘 문제인가?** 둘 다 기여했다. 첫 두 창의 raw signal 품질이 낮았고, 알고리즘이 그 낮은 품질을 감지하고도 유효값으로 통과시켰다. 직접 고칠 지점은 estimator validity gate다.
3. **AI/TFLite 재학습이 필요한가?** 아니다. 호흡수 오차는 TFLite 입력 이전에 발생한다.
4. **코드 수정이 필요한가?** 권고한다. 단, 이번 분석에서는 적용하지 않았다.
5. **최소 변경은 무엇인가?** 현재 계산 중인 `spectral_peak_ratio`에 fail-closed threshold를 추가하고 약한 peak에서는 rpm을 반환하지 않는 것이다.
6. **12/15 rpm을 유지하며 20 rpm을 ±2 안으로 개선할 수 있는가?** 기존 세 paced 실측에서는 가능했다. 후보 gate는 12/15의 12개 창을 모두 유지하고, 신뢰 가능한 20 rpm 2개 창을 모두 ±2 안에 남겼다. 다만 이는 잘못된 창을 수정하는 것이 아니라 안전하게 거부하는 방식이며, production 승인 전 전체 historical real-data regression이 필요하다.
