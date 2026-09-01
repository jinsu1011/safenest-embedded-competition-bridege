# mmWave rolling 품질 정책 Historical Replay 최종 보고서

## 1. 최종 결론

**Candidate A–E를 모두 production 후보로 채택하지 않는다.**

기존 historical real dataset만으로 20 rpm 저품질 출력을 차단하면서 paced 12/15 rpm, empty safety, 31분 occupied coverage와 연속성, distance coverage, entry/exit 및 기존 fail-closed 동작을 모두 유지하는 회귀 없는 정책을 찾지 못했다.

Production `PhaseRateEstimator`, `mmwave_processing.json`, TFLite model, ESP firmware, MR60 firmware는 변경하지 않았다. 현재 production은 `e8bdc73` 원복 이후의 gate 없는 상태를 유지한다.

## 2. 검증 범위와 방법

- 12개 historical real dataset 전체를 사용했다.
- Baseline과 Candidate A–E, 총 72 dataset replay를 실행했다.
- 실제 `mmwave_resp_int8` v0.1.0 INT8 TFLite를 사용했다.
- 모델 SHA-256은 `43cdd6f321c2b645232162233e098c2b65549388cbc9e680a17a0eccdc8f0158`이며 모든 replay에서 일치했다.
- Baseline 재실행은 기존 보고서와 dataset별 source hash, attempted/completed/rejected window, RPM estimate, fallback이 모두 일치하여 parity PASS였다.
- 품질 reject는 diagnostic layer에서만 수행했고, presence loss, stale, gap, NaN 등 production adapter의 기존 invalid/reset 판단 뒤에만 적용했다.

## 3. 후보 정의

| 후보 | 정책 |
|---|---|
| A | `peak_ratio >= 2.0`; reject 시 rolling buffer 유지 |
| B | prehistory RPM prior와 `peak_ratio >= 1.5`, RPM ±2 temporal consistency 결합 |
| C | enter `2.0`, remain `1.5` hysteresis |
| D | `peak_ratio >= 2.0`과 1·2위 local peak dominance `>= 2.0` 결합 |
| E | prior 없음/재동기화 `peak_ratio >= 5.0`, 유지 시 `peak_ratio >= 1.5`와 RPM ±2 결합 |

## 4. 핵심 비교

| 정책 | 20 rpm valid | 20 rpm MAE | 20 rpm max error | ±2 rpm | occupied windows | occupied 최장 연속 | 0.6/0.9/1.2 m | accepted occupied | entry/exit AI window | 판정 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Baseline | 4/6 | 4.004 | 9.246 | 2/4 | 47/49 | 1,230 s | 9/8/7 | 9/10 | 1/22 | 기준 |
| A | 4/6 | 3.566 | 13.035 | 3/4 | 47/49 | 1,080 s | 9/9/7 | 9/10 | 1/22 | 거부 |
| B | 3/5 | 0.807 | 1.330 | 3/3 | 11/13 | 60 s | 6/5/2 | 7/8 | 1/22 | 거부 |
| C | 4/6 | 4.004 | 9.246 | 2/4 | 47/49 | 1,230 s | 9/8/7 | 9/10 | 1/22 | 거부 |
| D | 3/5 | 0.233 | 0.448 | 3/3 | 34/36 | 120 s | 8/4/4 | 4/5 | 1/22 | 거부 |
| E | 3/5 | 0.351 | 0.527 | 3/3 | 42/44 | 240 s | 7/5/3 | 8/9 | 0/21 | 거부 |

거리 열은 각각 0.6/0.9/1.2 m의 completed window 수다. 1.5 m는 모든 정책에서 기존과 동일하게 0 window였다.

## 5. 후보별 판정 근거

### Candidate A: rolling buffer만으로는 불충분

처음 weak 20 rpm 창은 `peak_ratio=1.660`에서 reject됐지만 1.6초 뒤 `peak_ratio=2.039`를 처음 넘을 때 선택 RPM이 `6.965`였다. 따라서 rolling buffer 유지와 최초 threshold 통과만으로는 spectral recovery를 보장하지 못했다. 20 rpm max error가 오히려 13.035 rpm이었고, occupied completed count는 유지했지만 품질 UNKNOWN 때문에 최장 연속 inference가 1,230초에서 1,080초로 줄었다.

### Candidate B: temporal locking 회귀

20 rpm의 세 출력은 모두 ±2 rpm에 들어왔지만 이전 RPM prior에 고착됐다. occupied가 47→11, 최장 연속 inference가 1,230→60초로 감소했고 거리도 0.6 m 9→6, 0.9 m 8→5, 1.2 m 7→2로 악화됐다. 실제 호흡 변화 감지 지연 위험도 historical suite만으로 해소할 수 없다.

### Candidate C: coverage는 유지하지만 오류를 차단하지 못함

Prehistory에서 valid latch가 형성된 뒤 remain threshold `1.5`가 처음 두 20 rpm 오류 `14.331`, `10.754`를 그대로 허용했다. 모든 주요 coverage는 baseline과 같았지만 핵심 안전 목표를 달성하지 못했다.

### Candidate D: 정확도 개선과 심각한 availability 손실

경쟁 peak dominance를 추가하자 20 rpm MAE는 0.233 rpm으로 가장 좋아졌지만 occupied가 47→34, 최장 연속 inference가 1,230→120초, 0.9 m가 8→4, accepted occupied가 9→4로 감소했다. paced 15 rpm도 6→5로 줄었다.

### Candidate E: re-anchor로 B를 완화했지만 회귀 잔존

20 rpm MAE는 0.351 rpm이었으나 occupied 47→42, 최장 연속 inference 1,230→240초, 거리 9/8/7→7/5/3, entry/exit AI window 1→0으로 감소했다. B보다 낫지만 완료 조건에는 미달했다.

## 6. 안전성과 모델 동작

- Empty 30분과 accepted empty 6분은 모든 정책에서 AI window 0으로 fail-closed를 유지했다.
- Entry 20/20, exit 19/20과 vendor hysteresis 기반 release latency는 모든 정책에서 동일했다. 다만 Candidate E는 entry/exit dataset의 유일한 AI window를 잃었다.
- Candidate 전부 fallback 0이었다.
- 실제 TFLite run 수와 저장된 window JSONL 수는 각 dataset의 completed window와 일치했다.
- 신뢰 가능한 ABNORMAL/APNEA real class ground truth가 없으므로 3-class accuracy는 계산하지 않았다.

## 7. 해석과 다음 결정

20 rpm 실패 구간의 잘못된 저주파 peak는 순간 glitch가 아니었다. rolling 관측에서 약 20초 이상 부드럽게 이동했고 median 기반 peak ratio가 약 4.3까지 상승했다. 따라서 단일 threshold, 짧은 persistence, 또는 단순 temporal smoothness는 이를 안전하게 구분하지 못한다.

현재 historical suite 안에서 threshold를 더 조정하면 20 rpm 한 로그에 과적합될 가능성이 높다. Production 변경을 승인할 근거가 없으므로 현행 gate 없는 production을 유지한다. 추가 품질 정책은 실제 rate transition과 약한 정상 호흡에 대한 독립 ground truth가 확보되기 전까지 diagnostic-only로 남겨야 한다.

## 8. 산출물

- `diagnostic_summary.json`: provenance, baseline parity, 자동 판정, 전체 dataset 결과
- `windows/<policy>/<dataset>.jsonl`: accepted 실제 TFLite window와 품질 지표
- `FINAL_REPORT_KO.md`: 본 보고서
- `devices/mmwave/tools/mmwave_quality_policy_diagnostic.py`: 재현 가능한 diagnostic 도구
- `devices/mmwave/tests/test_mmwave_quality_policy_diagnostic.py`: 정책 state machine 단위 테스트

## 9. 검증 요약

- Diagnostic 및 기존 replay focused tests: 13 passed.
- `devices/mmwave/tests`에서 알려진 historical-only manifest 테스트 제외: 44 passed.
- On-device mmWave tests: 17 passed.
- Baseline parity: 12/12 datasets PASS.
- Production peak gate 부재와 production file 무변경을 재확인했다.
