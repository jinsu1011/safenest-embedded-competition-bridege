# mmWave rolling 품질 정책 Historical Replay Diagnostic

- Production 변경: 없음
- 모델 SHA-256: `43cdd6f321c2b645232162233e098c2b65549388cbc9e680a17a0eccdc8f0158`
- Baseline parity: **PASS**

## 후보 판정

| 후보 | 최종 판정 | 20 rpm windows | 20 rpm MAE | occupied | 0.9 m | quality recovery p95 | fallback |
|---|---|---:|---:|---:|---:|---:|---:|
| baseline | 기준 | 4/6 | 4.003609485080938 | 47/47 | 8/8 | 0.000s | 0 |
| candidate_a_rolling_peak | 거부 | 4/6 | 3.5660945067649426 | 47/47 | 9/8 | 2.699s | 0 |
| candidate_b_temporal | 거부 | 3/5 | 0.8066140125459628 | 11/47 | 5/8 | 215.029s | 0 |
| candidate_c_hysteresis | 거부 | 4/6 | 4.003609485080938 | 47/47 | 8/8 | 0.000s | 0 |
| candidate_d_peak_dominance | 거부 | 3/5 | 0.23303602385223363 | 34/47 | 4/8 | 44.114s | 0 |

## 자동 판정 상세

### candidate_a_rolling_peak: FAIL

- [ ] `20rpm_all_valid_within_2rpm`
- [x] `paced_12_coverage_preserved`
- [x] `paced_15_coverage_preserved`
- [x] `paced_12_all_within_2rpm`
- [x] `paced_15_all_within_2rpm`
- [x] `coverage_preserved`
- [x] `empty_fail_closed`
- [x] `fallback_zero`
- [x] `model_hash_valid`

### candidate_b_temporal: FAIL

- [x] `20rpm_all_valid_within_2rpm`
- [x] `paced_12_coverage_preserved`
- [x] `paced_15_coverage_preserved`
- [x] `paced_12_all_within_2rpm`
- [x] `paced_15_all_within_2rpm`
- [ ] `coverage_preserved`
- [x] `empty_fail_closed`
- [x] `fallback_zero`
- [x] `model_hash_valid`

### candidate_c_hysteresis: FAIL

- [ ] `20rpm_all_valid_within_2rpm`
- [x] `paced_12_coverage_preserved`
- [x] `paced_15_coverage_preserved`
- [x] `paced_12_all_within_2rpm`
- [x] `paced_15_all_within_2rpm`
- [x] `coverage_preserved`
- [x] `empty_fail_closed`
- [x] `fallback_zero`
- [x] `model_hash_valid`

### candidate_d_peak_dominance: FAIL

- [x] `20rpm_all_valid_within_2rpm`
- [x] `paced_12_coverage_preserved`
- [ ] `paced_15_coverage_preserved`
- [x] `paced_12_all_within_2rpm`
- [x] `paced_15_all_within_2rpm`
- [ ] `coverage_preserved`
- [x] `empty_fail_closed`
- [x] `fallback_zero`
- [x] `model_hash_valid`

## 해석 제한

Temporal consistency와 hysteresis는 historical suite에서 실제 호흡수 전환 ground truth가 없으므로 전환 지연 안전성을 완전히 입증하지 못한다. 이 결과는 production 변경 승인이 아니라 후보 선별 근거다.
