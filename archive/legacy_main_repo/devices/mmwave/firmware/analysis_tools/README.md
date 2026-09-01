# analysis_tools — 2026-07-26 세션 분석 스크립트

이 세션에서 도출한 결론(호흡 KPI 통과, 심박 용도 확정, freeze 판정 조건)을
**다른 컴퓨터에서 그대로 재현**하기 위한 스크립트 모음이다.
작업 당시 임시 디렉터리에서 실행하던 것을 검증된 상태 그대로 옮겼다.
로그 원본만 있으면 하드웨어 없이 전부 재실행 가능하다.

실행에 필요한 건 표준 라이브러리뿐이다 (json, statistics). pyserial·rich는 캡처용이지 분석용이 아니다.

```bash
PY=devices/mmwave/firmware/.venv/bin/python   # 또는 시스템 python3
L=devices/mmwave/firmware/logs
T=devices/mmwave/firmware/analysis_tools
```

## 호흡 (핵심 결론)

### phase_rate_zerocross.py — **ESP 채택 알고리즘**
breath_phase 영교차 + 히스테리시스(진폭 15%). 창 30초에서 15rpm·20rpm 모두 ±2rpm 100%.
두 세션을 한 번에 비교한다.

```bash
$PY $T/phase_rate_zerocross.py \
  $L/breath/2026-07-26_breath_paced_15rpm.jsonl 15 \
  $L/breath/2026-07-26_breath_paced_20rpm_deep.jsonl 20
```
출력에 `breath_phase std`가 함께 나온다. 이 값이 **진폭 게이트 임계(0.2)** 의 근거다.

### phase_rate_autocorr_octave.py — 교차검증용
자기상관 + 옥타브 보정("임계 이상인 가장 짧은 주기" 규칙). 인자 형식은 위와 동일.

### phase_rate_autocorr.py — 옥타브 보정 **없는** 버전 (보존용)
20rpm에서 6.0초(2배 주기)에 락하는 실패를 재현한다. 왜 보정이 필요한지 보여주는 자료.

### phase_period.py — 단일 세션 실제 호흡 주기
영교차와 자기상관을 나란히 출력. 피험자가 메트로놈을 제대로 따랐는지 판정할 때 쓴다.
2026-07-25 12rpm 세션이 실제로는 6.06rpm이었음(절반 호흡)을 밝힌 스크립트.

```bash
$PY $T/phase_period.py $L/breath/2026-07-26_breath_paced_15rpm.jsonl 15
```

### phase_any_session.py — 구버전(schema 1.0) 로그용
`stage` 필드가 없는 2026-07-25 로그를 처리한다. cue 전체 구간을 측정창으로 삼는다.

## 심박

### vital_presence_discrim.py — **생체신호 유무 판별력**
빈 공간 vs 인체 세션의 심박·호흡 신호 검출률 비교. 0.0% vs 94~100% 분리를 보여준다.
schema 1.0/1.1 필드명 차이를 자동 처리한다.

### hr_ref_compare.py — 애플워치 대조 (±5초 창)
스크립트 안 `watch=[...]` 리스트에 워치 실측 10개를 넣고 실행. 로그 경로는 스크립트 위치(`Path(__file__)`) 기준으로 자동 계산한다.

### hr_window_sweep.py — 중앙값 창 크기별 오차
창을 키워도 계통 오차가 안 줄어드는 것을 보여준다.

### hr_corr_bias.py — 상관계수 + 오프셋 보정
r ≈ 0 (추종 없음), 보정해도 상수 예측보다 나쁨. **심박 절대값 폐기 근거.**

## 진단 / 운용

### session_bin_diag.py — 30초 구간별 거리·심박 유효율
lock-loss freeze 탐지용. 2026-07-26 1차 캡처의 149.24cm 150초 고착을 찾아낸 스크립트.

### freeze_watchdog.py — 실시간 freeze 감시
캡처와 동시에 백그라운드로 돌린다. `거리 std=0 AND 심박 무효` 동시 성립 시 음성 경고(macOS).

```bash
$PY $T/freeze_watchdog.py <출력_jsonl_경로> <감시_초>
```

### hr_ref_capture_run.sh — 심박 대조 캡처 러너
300초 캡처 + 30초마다 Yuna 음성 체크 신호 + watchdog 동시 실행.
**macOS 전용** (`say`, `afplay`). 저장소 경로는 스크립트 위치 기준으로 자동 계산하며, 임시 작업 디렉터리는 환경변수 `SCR`로 덮어쓸 수 있다.

## 다른 컴퓨터에서 쓸 때 주의

1. **로그 스키마 2종** — 2026-07-25 파일은 schema 1.0으로
   `human_detected_stable` / `heart_raw_valid` / `breath_raw_valid` 필드가 **없다**.
   그대로 읽으면 전부 0%로 나온다. `human_detected_raw` + 값>0 으로 판정할 것.
2. **시계 2종** — cue 레코드는 `host_monotonic_ns`(맥), 센서는 `ts_monotonic_ms`(ESP).
   서로 변환 불가. **파일 기록 순서로 정렬**해야 한다. 모든 스크립트가 이 방식을 쓴다.
3. **음성 스크립트는 macOS 전용.** 분석 스크립트는 OS 무관.
4. **하드웨어 캡처는 실물 ESP+MR60 필요.** 포트는 재연결마다 바뀐다.
