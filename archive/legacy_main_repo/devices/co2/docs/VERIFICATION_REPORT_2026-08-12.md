# SCD40 실기기 검증 리포트 — 2026-08-12

## 1. 최종 판정

**종합 판정: PARTIAL — 정상 측정과 호기 응답은 확인, 센서 분리 계약은 미완료**

- 실내 baseline 5분: **PASS** (`attempt02`, 결측률 0%)
- 호기 상승·복귀 방향: **PASS_WITH_WARNINGS** (최고 1,493 ppm, TCP 결측률 8.61%)
- 센서 분리 시 `valid=false + SensorState`: **NOT VERIFIED** (사용자 결정으로 추가 분리 측정 생략)
- 로그 기반 `InferenceResult + SensorHealth/SensorState` 계약 테스트: **PASS** (4/4)

이 결과는 SCD40 실기기와 ESP32→Raspberry Pi 실시간 경로의 정상 측정 증거다. 센서 분리 결측 계약이 완료되지 않았으므로 CO2 증거 세트 전체를 최종 완료로 판정하지 않는다.

## 2. 하드웨어·통신 조건

| 항목 | 조건 |
|---|---|
| 센서 | SCD40, I2C 주소 `0x62` |
| 수집 보드 | ESP-WROOM-32 |
| 전원 | 3.3V |
| I2C | SDA GPIO21, SCL GPIO22 |
| 풀업 | 모듈 내장, 외부 풀업 없음 |
| 전송 | ESP32 `192.168.1.16` → Raspberry Pi 5 `192.168.1.44:9000` TCP |
| Pi API | `http://192.168.1.44:8080/health` |
| 캡처 주기 | 약 1초 |
| 캡처 필드 | host timestamp, monotonic clock, seq, uptime, CO2, valid, SensorState, transport 상태, 원시 API JSON |

## 3. 측정 결과

### 3.1 프리플라이트 30초

| 항목 | 실측 |
|---|---:|
| 표본 | 30 |
| 유효/결측 | 30 / 0 |
| CO2 최소/최대/평균 | 504 / 634 / 560.367 ppm |
| 판정 | PASS |

원본: `firmware/logs/2026-08-12_preflight_30s.csv`
SHA-256: `dea523b77258b8cf6f08987e575102c2aa29877fb96b8cbcf05985acd5918f2f`

### 3.2 실내 baseline 5분

| 시도 | 표본 | 유효 | 결측률 | CO2 최소/최대/평균 | 판정 |
|---|---:|---:|---:|---:|---|
| 최초 | 300 | 277 | 7.67% | 495 / 506 / 500.108 ppm | FAIL |
| attempt02 | 300 | 300 | 0% | 505 / 516 / 511.067 ppm | PASS |

최초 측정은 Pi TCP 수신이 `STALE` 또는 `NOT_CONNECTED`로 전이된 23개 표본 때문에 실패했다. 원본은 실패 증거로 보존했다. Pi 연결 사전검사 후 다시 측정한 attempt02는 300개 표본이 모두 `NORMAL`이었다.

- 최초 SHA-256: `11f58c3d624cff907f033fdcaa1e1041614a6aad282c3b6005efb052c7af7c42`
- attempt02 SHA-256: `409b788437e4685f8136f6d6b19c2f47d3ecd081ee56f46d958bf6ab486f9ad1`

### 3.3 호기 상승·복귀 6분

| 항목 | 실측 |
|---|---:|
| 전체/유효/결측 표본 | 360 / 329 / 31 |
| 결측률 | 8.61% |
| 호기 전 평균 | 약 509 ppm |
| 최고값 | 1,493 ppm |
| 상승량 | 약 +984 ppm |
| 종료값 | 634 ppm |
| 최고점 이후 감소량 | 859 ppm |
| 판정 | PASS_WITH_WARNINGS |

호기 주입 후 ppm 급상승과 최고점 이후 감소 방향은 확인했다. 종료 시 634 ppm으로 초기 수준까지 완전히 복귀하지는 않았고, TCP 상태 전이로 결측 31개가 발생했다.

원본: `firmware/logs/2026-08-12_breath-rise-recovery_6min.csv`
SHA-256: `2f5a2b7b6e4baf4d2544baefc3c0e3a65dc082bac7a95565002d784454a096c9`

### 3.4 센서 분리

**판정: NOT VERIFIED**

- 분리 사진은 저장했지만 60초 원시 CSV는 생성하지 않았다.
- 첫 시도는 ESP32 전원이 꺼져 있어 유효한 센서 분리 시험이 아니었다.
- 재연결 후 ESP32 부팅, SCD40 판독, Wi-Fi는 정상으로 확인됐다.
- COM3 부팅 로그에서 ESP32가 TCP `192.168.1.44:9000` 재연결을 반복했고, Pi 서비스 재시작 후 정상 수신이 복구됐다.
- 이후 사용자가 추가 분리 측정은 불필요하다고 결정해 시나리오를 종료했다.

따라서 센서 분리 시 ESP32가 `co2_ppm=null`, `valid.co2=false`를 보내고 어댑터가 비정상 `SensorState`를 반환하는지는 확인되지 않았다. 마지막 정상값 반복이나 transport stale을 센서 결측 통과로 간주하지 않는다.

## 4. 계약 테스트

`devices/co2/tests/test_co2_evidence_contract.py` 결과:

- 정상 실측 행 → `valid=true`, `state=NORMAL`, `metadata.co2_ppm` 보존
- 분리 형식 행 → `valid=false`, `state=NOT_CONNECTED`, 0 ppm 대체 없음
- 비숫자 CO2 → `INVALID_FORMAT` fail-closed
- 저장소 내 모든 실측 로그 → 공용 결과 계약 검증
- 결과: **4 tests OK**

이 테스트는 로그와 소프트웨어 계약을 검증한다. 실제 센서 분리 완료를 대신하지 않는다.

## 5. 증거 파일

### 사진

- `docs/images/2026-08-12_scd40_module_and_pin_labels.jpg`
- `docs/images/2026-08-12_esp32_board_and_wiring.jpg`
- `docs/images/2026-08-12_full_sensor_bench.jpg`
- `docs/images/2026-08-12_scd40_disconnected.jpg`

모든 사진은 사용자 제공 원본을 재인코딩 없이 복사하고 원본/목적지 SHA-256 일치를 확인했다.

### 분석

- `firmware/analysis/2026-08-12_preflight_30s_summary.json`
- `firmware/analysis/2026-08-12_baseline_5min_summary.json`
- `firmware/analysis/2026-08-12_baseline_attempt02_5min_summary.json`
- `firmware/analysis/2026-08-12_breath-rise-recovery_6min_summary.json`

## 6. 남은 조치

1. ESP32 telemetry에 SCD40 판독 실패를 나타내는 `co2_ppm=null`, `valid.co2=false`, 오류 코드가 실제로 출력되는지 구현·확인한다.
2. Pi 수신기가 TCP 재접속 시 이전 연결을 신속하게 정리하는지 점검한다.
3. 구현 후 분리 상태 60초 원시 로그를 새 파일로 측정하고 summary를 생성한다.
4. 위 작업 전에는 SCD40 증거 세트 상태를 `PARTIAL`로 유지한다.
