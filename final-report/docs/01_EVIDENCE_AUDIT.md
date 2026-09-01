# 01_EVIDENCE_AUDIT

Evidence levels: **E0** planned · **E1** source implemented · **E2** software verified ·
**E3** component HW verified · **E4** integrated real-HW / HIL · **E5** repeated quantitative.

Snapshot = `05_Source_Snapshot/safenest-embedded-competition` @ commit `3f22fb1…` (branch `codex/mmwave-m-c0-correspondence`).
"Executed" = actually run by me on this Mac (see `work/test_runs/EXECUTED_TESTS.md`).

| Feature / Claim | Exact source | Status | Level | Verified? | Safe wording (KO) | Missing evidence |
|---|---|---|---|---|---|---|
| ESP32 4-sensor node firmware | `devices/esp32_node/firmware/esp32_sensor_node.ino` (741 lines) | 4 sensors in one node, ESP32 Dev Module | **E1** | source read | 구현 완료 | 실기기 4센서 동시 수신 로그 |
| MCU = ESP32 DevKit V1 (not XIAO) | same file, pin constants L34-47; 유승하 report 대표문제 B | Board changed from XIAO ESP32-C6 | **E1/E3** | source + report | 구현 완료 | 교체 사유 1차 문서 (`[검증 필요]` per 유승하) |
| mmWave MR60BHA2 via **UART2** 115200 | `.ino` L38-39 `PIN_MMWAVE_RX=16/TX=17`, `MMWAVE_BAUD` | implemented + real capture | **E3** | `FINAL_REPORT_KO.md` 9.990 Hz, 1,201 rec | 실기기 검증 | — |
| SCD40 CO₂ via **I2C** 0x62 | `.ino` `SCD4X_ADDRESS=0x62`, SDA21/SCL22 | implemented + real sessions | **E3** | CO₂ 4 sessions 2026-08-12 | 실기기 검증 | 센서 분리(결측) 계약 미완 |
| Thermal MI48xx **I2C ctrl + SPI data** | `.ino` L40-46, `THERMAL_ADDRESS_A/B 0x40/0x41` | implemented | **E1/E3** | thermal v5 real frames | 실기기 검증(별도 리그) | 정식 노드에서의 실측 |
| PIR via **GPIO 13** digital | `.ino` `PIN_PIR=13`, `PIR_PERIOD_MS=20` | implemented | **E1** | source | 구현 완료 | 실 GPIO 수신 증거 (한준우: "실 GPIO 미설치") |
| **SafeNest TCP protocol v1** 16B header `SNST` | `.ino` L113-124; `integration/pi_lcd/server.py` L43-47 `PACKET_HEADER=Struct("!4sBBHII")` | both ends implemented | **E2** | **executed: 13 passed** | SW 검증 | — |
| `recv_exact()` length-prefixed framing | `integration/pi_lcd/server.py` | implemented | **E2** | executed | SW 검증 | — |
| **null ≠ 0** for invalid readings | `.ino` `formatNullableFloat()` L546-553 → emits `"null"` | implemented both ends | **E2** | executed + CO₂ CSV | 구현 완료 · SW 검증 | — |
| Per-channel `valid{}` block | `.ino` L576-583; server L140-145 | implemented | **E2** | executed | 구현 완료 | — |
| Per-sensor freshness TTL (ESP side) | `.ino` `MMWAVE_STALE_MS=5000`, `CO2_STALE_MS=15000`, `THERMAL_STALE_MS=30000` | implemented | **E1** | source | 구현 완료 | — |
| Pi-side stale state machine `waiting/live/stale/error` | `server.py` `SensorStore.snapshot()` L226-258, `stale_seconds=5.0` | implemented | **E2** | executed | SW 검증 | — |
| **CRC-16/CCITT-FALSE** on thermal frames | `.ino` L303-320 `thermalFrameCrc()`, poly 0x1021 init 0xFFFF; counter `thermalCrcErrors` | implemented | **E1** | source read | 구현 완료 | 실측 CRC 오류율 |
| Thermal frame integrity: geometry + inner/outer sequence + recomputed min/max cross-check | `server.py` L175-206 | implemented, corrupt frame discarded | **E2** | executed | SW 검증 | — |
| Dead-pixel band 2332–4231 raw (≈ −40…150 °C), ≥32 live pixels | `.ino` L98-101; `server.py` L199-206 | implemented | **E2** | executed | 구현 완료 | — |
| Robust peak = coolest of 16 hottest | `.ino` `THERMAL_PEAK_SAMPLE_COUNT=16` + comment | implemented | **E1** | source | 구현 완료 | — |
| Thermal auto re-init after 30 s no-frame (GPIO RESET 25) | `.ino` `recoverThermalIfStale()` L418-434, `initializeThermalCamera()` L232-240 | implemented | **E1** | source | 구현 완료 | 실측 복구 로그 |
| **Thermal full-frame streaming DISABLED** | `.ino` L108-111 `THERMAL_STREAM_FRAMES=false` + comment | current canonical state | **E1** | source | 현재 구조: 요약값 전송 | — |
| SPI 1 MHz / I2C 100 kHz (signal integrity) | `.ino` `THERMAL_SPI_HZ=1000000`; `Wire.setClock(100000)` L696 | implemented, from 8 MHz/400 kHz | **E3** | 유승하 report 문제3 | 실기기 검증 | 계측 파형 없음 |
| No `delay()`; millis() scheduling + FreeRTOS network task; 1-slot `xQueueOverwrite` | `.ino` header comment L15-18 | implemented | **E1** | source | 구현 완료 | — |
| Buzzer GPIO18 880 Hz on `emergency` | `server.py` `BuzzerController` L410, args L699-701 | implemented | **E2** | executed (mocked) | SW 검증 | 실기기 부저 증거 |
| **Risk engine (current Pi)** R=100·(0.25·mmWave+0.30·CO₂+0.15·PIR+0.30·Thermal), floors | `RaspberryPi/Runtime/risk/formula_v1.py`, `risk_formula_v1.json` | implemented | **E2** | `test_risk_formula_v1.py` | SW 검증. 보고서 P10 정본 | 구 V4 스냅샷 식과 다름 |
| Thresholds NORMAL<30 / WARNING 30–65 / DANGER ≥65 | same | implemented | **E2** | executed | 주의=WARNING. CAUTION 명칭 폐기 | 30/65는 팀 프로토타입 |
| CO₂ warning floor ≥1500 ppm or baseline+700, immediate danger ≥5000 ppm | `risk_formula_v1.json` `co2` + `CO2BaselineLock`; `docs/09_SAFETY_CRITERIA_V1.md` | implemented | **E2** | `test_indoor_air_quality_anchor_raises_warning_even_when_r_is_low`; `test_relative_rise_warns_below_the_absolute_ceiling`; `test_co2_baseline_lock.py` | 1,500 ppm(별표2 비고)=주의. \(B\)+700=상대 주의. occupancy는 점수 제외 | 인증 기준 아님 |
| **Fail-closed: all sensors invalid → risk_score=None, risk_level=None** | `ondevice_ai/risk/fallback.py` L196-201 | implemented | **E2** | executed | SW 검증 (**핵심 차별성**) | — |
| Weight renormalisation over valid sensors only | `fallback.py` L214-219 | implemented | **E2** | executed | SW 검증 | — |
| STALE excluded (not reused as current) | `fallback.py` L157-163 `_STALE_TIMESTAMP` | implemented | **E2** | executed | SW 검증 | — |
| system_health HEALTHY/DEGRADED/FAILED | `fallback.py` L182-190 | implemented | **E2** | executed | SW 검증 | — |
| Emergency override (thermal=1.0 or mmwave=1.0 → 100/DANGER) | `fallback.py` L203-212 | implemented | **E2** | executed | SW 검증 | — |
| **mmWave model v0.1.0 — deployment BLOCKED** | `ondevice_ai/models/model_manifest.json` | `validation_status: BLOCKED`, `block_reason: CLASS_COLLAPSE_ON_REPOSITORY_NPZ`, acc 0.3996, macroF1 0.19, abnormal/apnea recall 0.0, 468/468 predicted NORMAL | **E2** | manifest | 재현성 검증에서 클래스 붕괴 → 배포 차단 | — |
| mmWave model v0.2.0 candidate acc 1.0 | same manifest | `SYNTHETIC_SMOKE_ONLY`, `real_sensor_performance: NOT_VERIFIABLE`, `hardware_validation: BLOCKED_HARDWARE`, false-alarm `NOT_COMPUTABLE` | **E2** | manifest | **합성 데이터 한정** 후보 | 실센서 평가 전무 |
| Thermal model `thermal_fall_int8_v0.1.0` | manifest: `CONFIRMED_SYNTHETIC_ONLY` (2026-07-25) **superseded by** `03_Evidence/Thermal/*` (2026-08-11) real-HW E2E | real frames → real INT8 TFLite on Pi 5 | **E4** | phase reports | 실기기 E2E 검증 | 정식 4센서 노드 경유는 아님 |
| **HUMAN_FALL = LYING posture proxy** | `phase7_10_scenario_report.md` 시나리오 D "**안전하게 눕기**" → `HUMAN_FALL`; 김태균 report L47,490-491 | proxy only | **E3** | evidence | 눕기(LYING) 자세 기반 위험 후보 상태 | 시간축 낙상 사건 검증 없음 |
| Thermal surface temp ≠ body temp | 김태균 report L502; `.ino` peak comment | — | — | — | 표면 온도 / 열 분포 | 의료 근거 없음 |
| **Real Raspberry Pi 5 E2E latency (thermal)** | `phase11_12_fail_closed_benchmark.md` | 30.06 s, 138 iter, 135 valid (97.8%), 4.6 FPS, mean 167.92 / p50 162.70 / p95 173.90 / max 873.75 ms | **E5** | evidence | 실기기 실측 | 단일 세션·thermal 채널 한정 |
| Thermal fail-closed 6 cases incl. physical disconnect + recovery | `phase11_12_...md` | all PASS on real HW | **E4** | evidence | 실기기 fail-closed 검증 | — |
| Mac-only TFLite latency p50 0.139 ms | `03_Evidence/Thermal/thermal_latest.json` (`platform: macOS`) | model-only, **not Pi** | **E2** | file | macOS 기준 모델 단독 추론 | Pi 단독 추론 수치 없음 |
| CO₂ real sessions (ESP32→Pi TCP 9000) | `03_Evidence/CO2_Data/*.csv` + `VERIFICATION_REPORT_2026-08-12.md` | preflight 30 s (30/30), baseline 5 min attempt02 (300/300, 0% missing), 1st attempt FAIL 7.67% preserved, breath 6 min 360/329 (8.61% missing), peak 1,493 ppm | **E3/E5** | raw CSV | 실기기 검증 (PARTIAL) | 센서 분리 60 s 로그 없음 |
| mmWave live validation (standalone) | `FINAL_REPORT_KO.md` | 199/199 parse, seq loss 0, 9.994 Hz; 1,201 rec @ 9.990 Hz; UART/checksum/parser errors 0/0/0; real INT8 TFLite, fallback 0 | **E3/E5** | evidence | 센서 단위 실기기 검증 | 통합 노드 아님 |
| mmWave fail-closed `MMWAVE_PHASE_SIGNAL_TOO_FLAT` + recovery | `PROJECT_PROGRESS.md`, `FINAL_REPORT_KO.md` | verified live | **E3** | evidence | 실기기 fail-closed | — |
| mmWave replay benchmark (real logs) | `benchmark_summary.csv` | 12 scenarios; presence rate 1.0 @0.6–0.9 m, 0.814 @1.2 m, 0.880 @1.5 m (lock loss, 0 windows); resp MAE 0.270 rpm @12 rpm, 0.275 @15 rpm, 0.550 @20 rpm; model p95 0.14–0.18 ms | **E5** | CSV | 오프라인 리플레이 정량 결과 | 실시간 통합 아님 |
| Long-duration logs 30 min empty / 31 min occupied | `03_Evidence/Logs/*.jsonl` (18.4 MB / 19.0 MB) | sensor-level only | **E3** | files | mmWave 단일 채널 장시간 로그 | 전 센서 통합 내구 시험 없음 |
| ESP32 build footprint | `FINAL_REPORT_KO.md`, `INTEGRATION_PROGRESS.md` | RAM 32,356/327,680 = 9.9%; Flash 268,765/1,310,720 = 20.5% | **E2** | evidence | 실측 빌드 리소스 | — |
| Firmware/config hash-pinned telemetry | `FINAL_REPORT_KO.md` schema 1.2, ESP config SHA-256 `b817e8bf…` | implemented | **E3** | evidence | 구현 완료 | — |
| **FastAPI** in canonical snapshot | searched 401 code files | **NOT PRESENT** | **E0** | verified absent | 미구현 (계획 단계) | — |
| **SQLite** in canonical snapshot | searched 401 code files | **NOT PRESENT** | **E0** | verified absent | 미구현 (계획 단계) | — |
| **WebSocket** in canonical snapshot | searched 401 code files | **NOT PRESENT** | **E0** | verified absent | 미구현 (계획 단계) | — |
| Web layer actually present | `integration/web/package.json` | **Express 5 + bcryptjs + jsonwebtoken + qrcode** (Node.js), `sensor-simulator.js`, `rpi-protocol-simulator.js` | **E1** | source | 구현 완료(시뮬레이터 구동) | 실센서 구동 스크린샷 없음 |
| LCD/API server | `integration/pi_lcd/server.py`, Python **stdlib http.server**, HTTP 8080, 6 states | implemented | **E2** | executed | SW 검증 | 실센서 LCD 사진 없음 |
| Runtime launcher | `integration/start_all.sh`, `install_raspberry_pi.sh` | present (no `run_safenest.sh`) | **E1** | source | 구현 완료 | — |
| Integrated node runtime | `ondevice_ai/integrated_node/run_node.py` (+ mock sensors, provider contract) | implemented, provider injection | **E1/E2** | source | 구현 완료 | 4센서 실기기 주입 미검증 |
| Mock E2E scenario coverage 21 scenarios A–O | `03_Evidence/Test_Results/m_b9_summary.json` | `gate_status: PASS_WITH_WARNINGS`, mock only | **E2** | file | **모의 E2E** | 실 HIL 아님 |
| Test functions in repo | 99 files | **1,483 `def test_`** — count only | — | counted | 소스 내 테스트 함수 수 | 전체 실행 결과 아님 |
| Tests executed by me | see `work/test_runs/EXECUTED_TESTS.md` | **57 passed, 2 failed** (2 = missing packaged dataset manifest) | **E2** | executed | 본 세션 실행 결과 | TF/HW 의존 스위트 미실행 |
| Integrated 4-sensor HIL | — | **NONE FOUND** | **E0** | — | 미검증 | CRITICAL |
| Wi-Fi disconnect/recovery test | — | **NONE FOUND** (thermal cable-disconnect only) | **E0** | — | 미검증 | HIGH |
| Final integrated hardware photo | `03_Evidence/Hardware_Photos/*` = CO₂ bench only | not final build | **E3** | photos | CO₂ 벤치 실물 | CRITICAL |
| Final enclosure (printed) | `hardware/3d_models/*.stl` ×4 + 2 spec txt + 4 CAD renders (강유나 최종본) | design only | **E1** | files/images | 설계 완료 · 출력물 미확인 | 실제 출력물 사진 |
| Web dashboard with real sensor data | `03_Evidence/Dashboard/` **empty** | — | **E0** | — | 미검증 | HIGH |
| GitHub repo naming compliance | official rule `2026ESWContest_free_팀명` vs `safenest-embedded-competition` | noncompliant | — | — | — | CRITICAL |
| Demo video | storyboard PDF only | — | **E0** | — | 미제작 | CRITICAL |

## Datasets / external models (규정 제10조③ 대상)

| Sensor | Dataset | Source | License | Status |
|---|---|---|---|---|
| mmWave | Zenodo vital-sign, 110명·440rec·530window | DOI `10.5281/zenodo.18599983` | **CC BY 4.0** | 지도학습 backbone |
| Thermal | SDT Dataset, 32k train / 8k val / 8k real test, FLIR Lepton 3.5 | TU Wien / Zenodo `4124309` | **CC-BY-4.0 메타 vs 비상업 연구 제한 충돌 — 확인 필요** | T-A/T-B offline |
| CO₂ | UCI Occupancy Detection, 20,560행 | UCI ID 357 / Univ. of Mons | **CC-BY-4.0 VERIFIED** | C-A/C-B6 학습 |
| PIR | 없음 | — | — | 규칙만 |
| mmWave | repository NPZ 468 샘플 | 저장소 테스트 자산 | 내부 | **합성 — 실세계 근거로 사용 금지** |
