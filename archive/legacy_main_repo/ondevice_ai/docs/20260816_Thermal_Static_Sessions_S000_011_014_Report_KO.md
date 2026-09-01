# Thermal-90 정적 세션 검토 보고서

작성일: 2026-08-16 (KST)
대상: `session_S000_011`~`session_S000_014`
검증 위치: PC 바탕화면 `sessions/`

## 요약

아래는 당시 validator가 header word 0을 authoritative frame counter로 처리해 만든 역사 결과다. PR #22 교정 후 word 0 의미는 `SEMANTICS_UNVERIFIED`이며 중복·역전·gap만으로 sensor acquisition loss나 capture invalid를 확정할 수 없다. 원본 증거를 교정 validator로 다시 평가하기 전까지 학습에는 사용하지 않으며, 새 PASS도 소급 부여하지 않는다.

| 세션 | source label | valid | invalid | validator | 오류 요약 |
|---|---|---:|---:|---|---|
| `S000_011` | `EMPTY` | 171 | 639 | `CAPTURE_INVALID` | gap 2254, duplicate 626, reversal 38 |
| `S000_012` | `STANDING` | 173 | 1709 | `CAPTURE_INVALID` | duplicate 1732, reversal 82 |
| `S000_013` | `SITTING` | 174 | 1 | `CAPTURE_STRUCTURE_VALID_WITH_LIMITATIONS` | frame-counter 오류 없음 |
| `S000_014` | `LYING` | 173 | 614 | `CAPTURE_INVALID` | gap 1147, duplicate 588, reversal 27 |

## 해석 및 조치

- `PREVIOUS_SENSOR_COUNTER_INTERPRETATION_REQUIRES_RECLASSIFICATION`을 네 세션 모두에 적용한다.
- `S000_013`을 유일한 구조 검토 후보로 보던 기존 순위는 확정 근거로 사용하지 않는다.
- `S000_011`, `012`, `014`는 삭제하지 않고 당시 관찰과 transport 진단 증거로 보존한다.
- invalid 세션에서 유효 프레임만 추출해 새 학습 세션을 만들지 않는다.
- 재수집 대상은 `S000_015 EMPTY`, `S000_016 STANDING`, `S000_017 LYING`이다.
- 재수집 시 Pi 수집기를 먼저 시작하고 ESP32를 재시작한다.
- `send_failures` 증가 또는 SNTR transport integrity 오류가 반복되면 대량 수집을 중단한다. header word 0 pattern만으로 중단 사유를 센서 loss로 단정하지 않는다.

## 공통 제한

각 세션은 temporal provenance가 `TEMPORAL_ORDER_ONLY`이며, physical unit/orientation이 아직 검증되지 않았다. 따라서 정적 자세 pilot은 모델 학습 승인이나 낙상 이벤트 성능 검증을 의미하지 않는다.
