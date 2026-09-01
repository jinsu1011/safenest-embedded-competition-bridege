# MR60 HR Sideband Stage 1 — S1 Offline Result

## 판정

- H1 최종 판정: `PENDING_S2`
- S1 예비 판정: `PRELIMINARY_NOT_SUPPORTED`
- `heart_verified=false` 유지
- vendor 호흡수 사용: 없음
- vendor 심박/호흡 고정 오프셋 적용: 없음
- 시리얼 포트 및 신규 측정: 없음(Stage 1)

## 사전등록 기준 대비

| 항목 | S1 실측 | 충족 여부 |
|---|---:|---|
| 오차 vs 자체 호흡수 회귀 기울기 | 0.340 | FAIL (0.7~1.3 아님) |
| Pearson r | 0.117 | FAIL (0.6 미만) |
| 자체 호흡 유효 cue | 10/10 | PASS, 제외율 0% |
| vendor 오차가 ±f_resp/±2f_resp와 3bpm 이내 매칭 | 5/10 | 부분 일치 |
| vendor 오차 차수와 raw spectrum 지배피크 차수 동시 일치 | 0/10 | FAIL |
| +25bpm cue 8의 +2f_resp 매칭 | 잔차 9.30bpm(+2 기준) | FAIL |
| +28bpm cue 9의 +2f_resp 매칭 | 잔차 7.14bpm | FAIL |
| −11bpm cue 5의 −f_resp 매칭 | 잔차 5.71bpm | FAIL |

> cue 8은 가장 가까운 차수가 +1이지만 잔차 7.85bpm이며, +2 차수와의 잔차는 9.30bpm이다.

## 직접 스펙트럼 증거

- 분석 raw source는 ESP schema가 제공하는 `total_phase`다. `heart_phase`는 vendor 분리 보조 비교로만 사용했다.
- 대표 cue 3(최소 양의 오차 +9), cue 5(음의 이상치 −11), cue 9(최대 오차 +28)의 0.8~2.0Hz 스펙트럼에서 vendor bpm 위치가 일관된 지배 피크가 아니었다.
- 10개 cue 중 vendor 오차의 측대파 차수와 `total_phase` 지배 피크의 측대파 차수가 동시에 3bpm 이내로 일치한 경우는 0개였다.
- 따라서 S1에서는 “vendor가 호흡 측대파를 일관되게 선택한다”는 직접 증거가 확보되지 않았다.

## 호흡 강도와 오염 결합

| 비교 | Pearson r |
|---|---:|
| |심박 오차| vs breath phase std | −0.147 |
| 최대 측대파/기본파 비 vs breath phase std | +0.323 |
| 최대 측대파/기본파 비 vs breath spectral peak ratio | +0.116 |
| 최대 측대파/기본파 비 vs firmware breath valid rate | −0.378 |

강한 양의 결합이나 호흡 유효성과의 상보 구조는 S1에서 관찰되지 않았다. 이는 장기 자연호흡 유효률 FAIL과 동일 원인이라고 결론낼 근거가 현재 없다는 뜻이다.

## 이상치 해석

| Cue | Watch | Vendor | Error | 자체 호흡 | 최근접 차수 | 잔차 | 판정 |
|---:|---:|---:|---:|---:|---:|---:|---|
| 5 | 75 | 64 | −11 | 16.71 | −1 | 5.71 | 불일치 |
| 8 | 71 | 96 | +25 | 17.15 | +1 | 7.85 | 불일치 |
| 9 | 81 | 109 | +28 | 17.57 | +2 | 7.14 | 불일치 |

## 제한 및 다음 단계

S1의 Watch 범위는 68~81bpm으로 좁아 최종 H1 판정에는 검정력이 부족하다. 사전등록 기준은 S1+S2 통합 회귀에 적용하므로 H1을 아직 최종 기각하지 않는다. S2 회복 구간을 홀드아웃으로 수집·분석한 뒤 H1을 최종 지지 또는 기각한다. Stage 1 결과가 사전 지지를 보이지 않으므로 notch 구현은 현재 금지한다.
