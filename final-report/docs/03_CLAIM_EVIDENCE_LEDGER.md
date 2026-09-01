# 03_CLAIM_EVIDENCE_LEDGER

보고서에 실릴 강한 주장만 등록한다. 여기에 없는 강한 주장은 PPT에 넣지 않는다.

| # | 주장 (보고서 표현) | 근거 파일 | 등급 | 허용 표현 | 금지 과장 | 상태 |
|---|---|---|---|---|---|---|
| 1 | 유효하지 않은 측정값은 0이 아니라 `null`로 보내고 `valid` 플래그를 함께 전달한다 | `devices/esp32_node/firmware/esp32_sensor_node.ino` `formatNullableFloat()` L546-553, L576-583 | E2 (실행 13 tests) | "구현 완료 · SW 검증" | "결측을 완벽히 처리" | ✅ |
| 2 | 모든 증거가 무효·결측이면 위험도를 **산출하지 않는다**(`risk_score=None`) | `RaspberryPi/Runtime/risk/formula_v1.py` fuse(); 구 스냅샷 `fallback.py` L196-201 | E2 | "미산출/UNKNOWN 반환" | "항상 안전을 보장" | ✅ |
| 3 | TTL 초과 입력은 STALE로 분리되어 현재 증거로 재사용되지 않는다 | `formula_v1.py` LIVE 게이트; `.ino` STALE 상수 | E2 (실행) | "SW 검증" | "실시간 보장" | ✅ |
| 4 | 유효 센서 가중치만으로 재정규화하여 위험도를 계산하고, 심한 채널은 플로어로 희석을 막는다 | `formula_v1.py` fuse(); `risk_formula_v1.json` `escalation_floors` | E2 | "SW 검증" | — | ✅ |
| 5 | 열화상 프레임에 CRC-16/CCITT-FALSE와 헤더 min/max 재계산 대조를 적용해 손상 프레임을 버린다 | `.ino` L303-320, L366-367; `server.py` L175-206 | E1 + E2 (실행) | "구현 완료 · SW 검증" | "무결성 100%" | ✅ |
| 6 | 30초간 프레임이 없으면 GPIO RESET으로 카메라를 자동 재초기화한다 | `.ino` `recoverThermalIfStale()` L418-434 | E1 | "구현 완료" | "복구 성공률 N%" | ✅ (실측 로그 없음) |
| 7 | 브레드보드 배선 신호 무결성을 고려해 SPI 8 MHz→1 MHz, I2C 400→100 kHz로 조정했고 1 MHz에서 프레임당 약 81 ms | `.ino` L50-53 주석, `Wire.setClock(100000)` L696; 유승하 문제#3 | E3 | "실기기 기반 조정" | "파형 측정으로 입증" | ✅ |
| 8 | 열화상 전 프레임 스트리밍이 1초 telemetry 주기를 침해하여 송신측 요약 방식으로 전환했다 | `.ino` L108-111 + 주석; 유승하 대표문제 A (9,952 B × ~6.25 fps ≈ 60 KB/s) | E1 + E3 | "구조 재설계" | "대역폭 문제 완전 해결" | ✅ |
| 9 | XIAO ESP32-C6의 사용 가능 GPIO 부족으로 ESP32 DevKit V1으로 교체, 열화상 RESET 제어를 확보했다 | 유승하 대표문제 B; `.ino` 핀 상수 | E1 + E3 | "자원 제약 → 보드 결정" | 인과 단정(원 보고서 `[검증 필요]`) | ⚠ 표현 주의 |
| 10 | mmWave 모델 v0.1.0은 재현성 검증에서 클래스 붕괴가 확인되어 **배포를 차단**했다 | `ondevice_ai/models/model_manifest.json` (`BLOCKED`, `CLASS_COLLAPSE_ON_REPOSITORY_NPZ`, acc 0.3996, macroF1 0.19, recall 0.0/0.0, 468/468 NORMAL) | E2 | "배포 차단" | "문제를 해결했다" | ✅ |
| 11 | 열화상 채널은 실제 센서 프레임이 Pi 5에서 실제 INT8 TFLite까지 관통했다 | `03_Evidence/Thermal/Final_Validation_Report.md`, `phase4_6`, `phase7_10` | E4 | "실기기 E2E 검증" | "전 시스템 통합 검증" | ✅ |
| 12 | 열화상 채널 Pi 5 실측 E2E 지연 p50 162.70 ms / p95 173.90 ms, 4.6 FPS, 유효 프레임 97.8% (30.06 s, 138회) | `phase11_12_fail_closed_benchmark.md` | E5 | "열화상 채널 실측" | "시스템 경보 지연 ≤2초 달성" | ✅ 범위 명시 필수 |
| 13 | 열화상 fail-closed 6종(순서위반·NaN/Inf·형식오류·물리적 단선·복구·close후 read) 실기기 통과 | `phase11_12_...md` | E4 | "실기기 fail-closed 검증" | "모든 장애 대응" | ✅ |
| 14 | mmWave 실기기 스트림 9.990 Hz, 1,201 레코드, UART/checksum/parser 오류 0, 시퀀스 누락 0 | `03_Evidence/Test_Results/FINAL_REPORT_KO.md` | E5 | "센서 단위 실기기 검증" | "시스템 가용성 99%" | ✅ |
| 15 | 무신호 평탄 입력은 `MMWAVE_PHASE_SIGNAL_TOO_FLAT`으로 추론이 차단되고 복귀 후 정상 회복 | `FINAL_REPORT_KO.md`, `PROJECT_PROGRESS.md` | E3 | "실기기 fail-closed" | — | ✅ |
| 16 | 실제 로그 리플레이에서 호흡수 MAE 0.270 rpm(12 rpm)·0.275(15 rpm)·0.550(20 rpm) | `benchmark_summary.csv` | E5 | "오프라인 리플레이 정량" | "호흡수 오차 ±2 rpm 달성" | ✅ 범위 명시 |
| 17 | 거리 1.2 m에서 presence 0.814, 1.5 m에서 lock loss로 유효 창 0 | `benchmark_summary.csv` | E5 | "거리 한계 실측" | — | ✅ (한계 공개) |
| 18 | SCD40 실측: baseline 5분 재측정 300/300(결측 0%), 호기 시 최고 1,493 ppm | `03_Evidence/CO2_Data/*.csv`, `VERIFICATION_REPORT_2026-08-12.md` | E3/E5 | "실기기 검증" | "CO₂ 정확도 검증 완료" | ✅ |
| 19 | 최초 baseline은 전송 경로 문제로 7.67% 결측 → **실패로 판정하고 원본 보존**, 재측정에서 0% | 동일 | E3 | "실패 기록 보존" | — | ✅ (신뢰도 상승 요소) |
| 20 | ESP32 빌드 RAM 9.9%(32,356/327,680), Flash 20.5%(268,765/1,310,720) | `FINAL_REPORT_KO.md`, `INTEGRATION_PROGRESS.md` | E2 | "실측 빌드 리소스" | — | ✅ |
| 21 | 3D 하우징 4종 STL + 설계사양 2종을 설계·전달 (센서 137×80×60 mm, LCD 240×140 mm, 슬롯 3.5 mm, 편측 유격 0.25 mm) | `hardware/3d_models/*`, 강유나 최종본 Ⅱ-6 | E1 | "설계 완료" | "하우징 제작 완료" | ✅ 출력물 사진 없음 |
| 22 | 본 세션에서 하드웨어 없이 실행 가능한 테스트 57건 통과, 2건 실패(패키지 내 데이터 파일 부재) | `work/test_runs/EXECUTED_TESTS.md` | E2 | "본 문서 작성 시점 실행 결과" | "1,483 tests 통과" | ✅ |
| 23 | CO₂ 절대 주의 천장은 **1,500 ppm**(별표2 비고: 자연환기 불가+기계환기)이며 주의 구간이다. 별표2 **기본 1,000 ppm은 절대 트립이 아니다**. 5,000 ppm 비상은 OSHA/NIOSH/ACGIH 8h TWA와 같은 값이다 | `docs/09_SAFETY_CRITERIA_V1.md`; `risk_formula_v1.json`; 별표2; 제618조; OSHA Chemical Data 183 | E2 | "팀 프로토타입 조기경보. 출처는 09" | "안전기준 준수" | ✅ |
| 24 | HUMAN_FALL은 눕기(LYING) 정적 자세 프록시다 | `phase7_10_scenario_report.md` 시나리오 D; 김태균 L47 | E3 | "정적 자세 기반 위험 후보" | "낙상 감지" | ✅ |

## 등록 거부 (증거 없음 → 보고서 사용 금지)
정지 인체 감지 정확도 ≥95% · 경보 지연 ≤2초 · 시간당 오탐률 ≤5% · AI 추론 지연 ≤100 ms(Pi) · 가용성 ≥99% ·
4센서 동시 수신 · 통합 HIL · Wi-Fi 재접속 복구 · 실센서 대시보드/LCD 화면 · 완성 하우징 · 상용화/판매가/시장규모 단정.
