# 05_ASSET_INDEX

| # | 자산 | 내용 | 시점 | 증거가치 | 후보 페이지 | 현재/과거 | 직접 사용 |
|---|---|---|---|---|---|---|---|
| A1 | `03_Evidence/Hardware_Photos/2026-08-12_full_sensor_bench.jpg` (9.9 MB, 8064×6048, 90° 회전 필요) | ESP32 + 브레드보드 + SCD40 + 소형 모듈 + LCD 실물 벤치 | 2026-08-12 | 높음 — 유일한 실물 배선 사진 | **5** | 현재(CO₂ 벤치) | ✅ 단, "최종 통합 4센서 완제품 아님" 캡션 필수 |
| A2 | `.../2026-08-12_esp32_board_and_wiring.jpg` (2.1 MB) | ESP32 + SCD40 배선 근접 | 2026-08-12 | 중 | 5 (보조) | 현재 | ✅ |
| A3 | `.../2026-08-12_scd40_module_and_pin_labels.jpg` | SCD40 모듈·핀 라벨 | 2026-08-12 | 중 — 부품 식별 | 5 (보조) | 현재 | ✅ |
| A4 | `.../2026-08-12_scd40_disconnected.jpg` | 물리적 센서 분리 상태 | 2026-08-12 | 중 — 단선 시험 맥락 | 8 (보조) | 현재 | ⚠ "분리 60초 로그 미생성" 명시 |
| A5 | `assets/3d_lcd_housing_front.png` (강유나 최종본 image1) | LCD·부저 사다리꼴 하우징 전면, SafeNest 음각, 부저 그릴 | 2026-08-20 | 높음 — 외함 설계 증거 | **18** | 현재 | ✅ |
| A6 | `assets/3d_trapezoid_T_back_vent.png` | T형 뒤판 환기 구조 | 2026-08-20 | 중 | 18 | 현재 | ✅ |
| A7 | `assets/3d_sensor_housing_sliding_back.png` | 센서 하우징 슬라이딩 뒤판 | 2026-08-20 | 중 | 18 | 현재 | ✅ |
| A8 | `assets/3d_sensor_housing_front_openings.png` | 센서 하우징 전면 개구부 | 2026-08-20 | 높음 — 센서 FOV 개구부 | **5 또는 18** | 현재 | ✅ |
| A9 | `03_Evidence/Thermal/visual_spotcheck.png` (619 KB) | 열화상 전처리 기하 스팟체크 | v5 | 중 | 9 | 현재 | ✅ |
| A10 | `03_Evidence/CO2_Data/*.csv` (4 세션, 994행) | 실측 CO₂ + valid/sensor_state/transport_status | 2026-08-12 | **매우 높음 — 원시데이터** | **11 (차트)** | 현재 | ✅ 차트 생성 |
| A11 | `03_Evidence/Test_Results/benchmark_summary.csv` (12 시나리오) | presence rate / resp MAE / 창 성공률 | 2026-08-08 | **매우 높음 — 원시 정량** | **9 또는 16 (차트)** | 현재 | ✅ 차트 생성 |
| A12 | `03_Evidence/Thermal/phase11_12_fail_closed_benchmark.md` | Pi 5 실측 지연 분포 + fail-closed 6종 | 2026-08-11 | **매우 높음** | **9, 13** | 현재 | ✅ |
| A13 | `03_Evidence/Logs/*.jsonl` (30분/31분, 37 MB) | mmWave 장시간 원시 로그 | 2026-08-01 | 높음 | 16 (표기만) | 현재 | ⚠ 대용량, 수치만 인용 |
| A14 | `hardware/3d_models/*.stl` ×4 | 하우징 STL | — | 중 | 18 | 현재 | 파일 존재 표기 |
| A15 | `integration/web/qr-codes/*.png` ×3 | 밀폐공간 A-01 / 통학차량 B-02 / 창고 C-03 QR | — | 중 — 적용 시나리오 실재 | 17 | 현재 | ✅ |
| A16 | `03_Evidence/Demo_Materials/SafeNest_3분_시연영상_콘티.pdf` | 시연 콘티 | — | 낮음(보고서용) | — | 현재 | ❌ 영상 아님 |
| A17 | `03_Evidence/Dashboard/` | **비어 있음** | — | — | — | — | ❌ 실센서 대시보드 캡처 없음 |
| A18 | `03_Evidence/LCD/LCD_BUZZER_TEAM_GUIDE.html` | LCD/부저 가이드 | — | 낮음 | — | 현재 | ❌ 실동작 증거 아님 |

## 생성 예정 차트 (원시데이터 기반만)
- **CH1** `previews/chart_co2.png` — `2026-08-12_breath-rise-recovery_6min.csv` + `baseline_5min.csv` 원본 파싱. x=경과초, y=co2_ppm, 결측(valid=False) 구간을 값으로 잇지 않고 공백 표시.
- **CH2** `previews/chart_mmwave.png` — `benchmark_summary.csv` 원본 파싱. 거리별 presence_detection_rate + 호흡 MAE.

## 금지
- 스톡 사진, AI 생성 하드웨어 이미지, 산문 수치로부터 만든 곡선, 실센서 대시보드 스크린샷의 대체물.
