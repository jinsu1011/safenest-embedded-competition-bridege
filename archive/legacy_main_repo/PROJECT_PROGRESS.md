# SafeNest mmWave ESP Live Validation 진행 기록

## 목표와 완료 조건

MR60 firmware·production 알고리즘·TFLite 모델을 변경하지 않고 standalone ESP firmware부터 실제 V5 provider까지 live 경로, 반복성, fail-closed, 회귀 테스트를 검증해 세 가지 허용 판정 중 하나를 내린다.

## 체크리스트와 결과

- [x] 통합 firmware backup 시도 중단 — 사용자가 조원 보관을 확인했고 추가 조사 금지를 지시했다.
- [x] standalone firmware compile/flash — ESP32 build와 hash-verified upload가 성공했다. MR60 firmware는 건드리지 않았다.
- [x] production JSONL 확인 — schema 1.2, 기대 firmware/config hash, 199/199 parse, 약 9.994 Hz를 확인했다.
- [x] serial 품질 확인 — 주 세션 1,201 records, 9.990 Hz, sequence drop과 UART/checksum/parser 오류가 모두 0이었다.
- [x] 실제 300-sample/TFLite 반복 검증 — 정상 창 3/3, 실제 INT8 TFLite 3회, fallback 0이었다.
- [x] fail-closed 및 회복 검증 — 무인 평탄 입력은 `MMWAVE_PHASE_SIGNAL_TOO_FLAT`으로 차단됐고 복귀 후 새 창이 성공했다.
- [x] V5 provider 계약 증거 확보 — 추가 300-sample 창에서 `sensor_id=mmwave`, 전체 metadata, model hash 일치를 보존했다.
- [x] 테스트와 무변경 확인 — devices 46 passed, on-device/provider 23 passed, production/model diff 없음.
- [x] 한국어 최종 보고서 작성 — `FINAL_REPORT_KO.md`에 판정·근거·한계·생성 파일을 기록했다.

## 결정과 이유

- 최종 판정은 `MMWAVE_LIVE_VALIDATION_PASS`다. 요구된 live pipeline, fallback 0, provider, fail-closed, 관련 테스트 조건을 모두 충족했다.
- vendor presence 고정은 해결된 것으로 보지 않는다. 다만 lock-loss 평탄 phase가 실제 추론으로 넘어가지 않는 fail-closed는 확인했다.
- confidence 1.0을 정확도 100%로 해석하지 않는다. 실제 ABNORMAL/APNEA ground truth 검증은 수행하지 않았다.
- 검증 모니터의 terminal 오류 집계와 provider 증거 보존만 수정했으며 production 코드·모델은 변경하지 않았다.

## 최종 상태와 다음 단계

- ESP32 현재 상태: standalone `safenest-mr60-esp/1.2.0`; 통합 firmware로 복원하지 않음.
- 근거 디렉터리: `devices/mmwave/validation_results/final_live/2026-08-08_standalone_mmwave_attempt01/`
- 최종 보고서: 위 디렉터리의 `FINAL_REPORT_KO.md`
- stage/commit/push/merge 없음.
- 다음 단계는 사용자가 원할 때 조원이 보관한 통합 firmware를 복원하는 것이며, 이번 검증 범위에서는 수행하지 않는다.
