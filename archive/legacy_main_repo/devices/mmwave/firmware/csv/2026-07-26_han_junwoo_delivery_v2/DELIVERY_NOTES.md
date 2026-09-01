# 한준우 전달 메모 — mmWave CSV 배치 v2

이 폴더는 세션별 CSV, 원본 JSONL 사본, 원본·CSV SHA-256과 진단을 담은
`manifest.json`으로 구성된다. CSV의 `resp_phase`는 ESP `breath_phase` 원값이며
정규화·평활·재샘플링하지 않았다.

## 반드시 반영할 해석

- `2026-07-25_breath_paced_12rpm`은 라벨과 달리 피험자가 한 호흡에 10초를 써서
  실제 약 6.06rpm인 실패 사례다. 12rpm 정답 데이터로 학습하거나 평가하지 않는다.
- 유효 12rpm 기준은 `2026-07-28_breath_paced_12rpm_explicit_v2_attempt03`이다.
- 20rpm은 얕은 호흡 실패본과 deep 성공본이 모두 있다. 성공 기준은
  `2026-07-26_breath_paced_20rpm_deep`이고, 얕은 본은 저진폭 실패 탐지용이다.
- MR60 내장 `breath_rate_raw`는 속도별 편향이 일정하지 않아 신뢰할 수 없다.
  모델 입력은 `resp_phase` 원값을 사용하고 도메인 정렬은 팀 어댑터에서 처리한다.
- D15의 거리 `std=0`은 측정 거리 한계가 아니라 lock-loss 고착 시그니처다.
  거리 고정만으로 부재를 판정하지 않는다.
- 심박 bpm 절대값은 쓰지 않는다. `heart_raw_valid=true`는 사람 존재의 단방향
  양성 증거일 뿐이며, false를 사람 부재나 심정지로 해석하면 안 된다.

세션별 `preferred_validation`, `failure_case`, `lock_loss_case` 구분은
`manifest.json`의 `sessions[].interpretation`을 따른다.
