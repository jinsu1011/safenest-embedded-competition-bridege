# Existing MR60 Evidence Audit

## 감사 범위와 방법

- 원본: `jinsu1011/safenest-embedded-competition`
- 기준 ref: `main`
- 기준 commit: `fdf34b804f35e5868356f0ed6f804a248aa69131`
- 대상: 현재 `devices/mmwave/firmware/logs/` 아래 JSONL 78개
- 메인 저장소는 read-only로 읽었고, 원본 JSONL은 수정하지 않았다.
- 각 줄의 JSON 파싱, schema version, 필드 존재, sequence, `ts_monotonic_ms`, timestamp 간격, UART/checksum 상태, presence, breath/heart validity를 다시 계산했다.
- SHA-256은 내려받은 원본 bytes로 계산했고, 기존 final manifest의 주요 artifact 선언과 대조했다.

## 실제 raw scan 결과

| 검사 | 결과 |
|---|---:|
| 현재 logs 아래 JSONL | 78개 |
| 물리 줄 수 | 172,390 |
| 정상 JSON object | 172,387 |
| 잘못된 JSON 줄 | 3개 |
| schema 1.0 record | 75,476개 |
| schema 1.1 record | 13,868개 |
| schema 1.2 record | 69,750개 |
| timestamp 역행 | 0 |
| timestamp 중복 | 683개 전체 로그 기준 / schema 1.2 기준 0 |
| 500 ms 초과 gap | 0 |
| sequence 역행 | 0 |
| schema 1.2 sequence gap | 2회, 최대 gap 2 |
| schema 1.2 `uart_frame_ok=false` | 0 |
| schema 1.2 `checksum_ok=false` | 0 |
| schema 1.2 `heart_verified=true` | 0 |

잘못된 JSON 줄은 다음 세 곳이다.

1. `devices/mmwave/firmware/logs/baseline/2026-07-13_empty_desk_collector_v1_30s.jsonl:1`
2. `devices/mmwave/firmware/logs/final/2026-08-01_occupied_d09_v120_31min.jsonl:9000`
3. `devices/mmwave/firmware/logs/kpi/2026-08-01_heartrate_watch_s2_recovery_v120_480s.jsonl:607`

기존 final manifest는 68개 JSONL, 154,413줄, 잘못된 줄 2개라고 기록한다. 현재 main의 실제 `devices/mmwave/firmware/logs/` 전체 scan은 78개, 172,390줄, 잘못된 줄 3개다. 따라서 기존 manifest와 현재 저장소의 감사 범위가 일치하지 않는다. 기존 manifest가 참조하는 경로도 현재 `devices/mmwave/...`가 아니라 이전 `firmware/esp_wroom32_mr60_monitor/...` 경로다. 이 차이는 M-C0 evidence lineage에서 별도로 표시해야 한다.

## 현재 schema 1.2 raw 결과

현재 schema 1.2 record 69,750개는 모두 다음 firmware/config 조합이었다.

- firmware: `safenest-mr60-esp/1.2.0`
- config hash: `b817e8bfd5e52b18275626f7b6a9bd60098ea4b108428a5aaf63600dbc987834`
- sample rate: 파일별 약 9.98–10.00 Hz
- 최대 timestamp gap: 200 ms
- timestamp 역행/중복: 없음
- `heart_verified`: true 없음

다만 schema 1.2 record 중 heart-watch 보조 세션에서는 누적 `parse_errors`와 `checksum_errors` 값이 0보다 큰 record가 각각 9,048개 있었다. 동시에 해당 record의 `uart_frame_ok`와 `checksum_ok`는 false가 아니었다. 이는 즉시 전송 실패로 단정하지 않고, 누적 카운터의 의미와 보조 세션 범위를 추가 확인해야 하는 상태다.

주요 raw 파일을 다시 계산한 값은 다음과 같다.

| 파일 | records | duration | rate | 핵심 결과 |
|---|---:|---:|---:|---|
| `final/2026-08-01_empty_v120_30min.jsonl` | 17,995 | 1,799.781 s | 9.997883 Hz | presence 0%, state `UNKNOWN` |
| `final/2026-08-01_occupied_d09_v120_31min_attempt02.jsonl` | 18,574 | 1,859.840 s | 9.986343 Hz | stable presence 98.8102%, `breath_filtered_valid` 21.7939% |
| `final/2026-08-01_occupied_d09_v120_31min.jsonl` | 18,588 valid + invalid 1 | 1,859.865 s | 9.993736 Hz | corrupted line 1개, sequence gap 1 |
| `final/2026-08-01_healthcheck_v120_75s.jsonl` | 749 | 74.848 s | 9.993587 Hz | stable presence 100%, `breath_filtered_valid` 69.0254% |

`attempt02_after60s_summary.json`의 17,974 records와 stable presence 98.7704%는 첫 60초를 제외한 summary다. 위 raw scan의 18,574 records와 98.8102%는 전체 raw 파일 기준이므로 서로 다른 window다.

주요 raw SHA-256은 기존 final manifest 선언과 일치했다.

- empty 30 min: `32ee3ae455ccf46029840f71268fdda37a88a963eed7ac7c7f9dfb269d00b3b2`
- empty preflight: `2f3d0b6657381f697f50dab396cb0dfb8a44354f6e86c30ab0ccde5ee7a95dfd`
- healthcheck v1.2: `eb4c57a16ea00d6b4314364f298cac2420a0f9cf3023eed15d02dcdd95835382`
- occupied attempt02: `7f9e9ac65377c6dc217af92f9dee2401b6162540e2245fce97acf2ed49368a34`

## 기존 CSV delivery manifest와의 대조

기존 v2 manifest는 9개 session을 선언한다.

- 정상 거리 조건: D06, D09, D12, D15
- paced breathing: 12, 15, 20 rpm 계열
- 모든 session의 subject ID: `S001`
- 기존 진단 cadence: 약 10 Hz, 최대 gap 약 101–103 ms, timestamp 역행/중복 없음

기존 manifest의 해석도 그대로 보존해야 한다.

- D12: presence 81.4%인 range-limit case
- D15: 원본 CSV의 finite `range_m` 2,639개는 변동했다. 모집단 표준편차(`ddof=0`)는 `2.937040294cm`, 표본 표준편차(`ddof=1`)는 `2.937596920cm`다. corrected 문서는 표본 값을 사용한다. 반면 finite `resp_phase` 2,999개는 모두 `-0.01`로 표준편차 0이었다. 따라서 D15는 vitals/phase freeze 또는 lock-loss 탐색 증거로 남지만, 거리 분산 0을 근거로 삼지 않는다. source: `devices/mmwave/firmware/csv/2026-07-26_han_junwoo_delivery_v2/2026-07-25_occupied_d15_v1_360s__S001_NORMAL_D15.csv`; 결측/비유한 값 제외, 단위 `range_m × 100 = cm`, Python `statistics.pstdev/stdev`로 재현.
- 최초 12 rpm 시도: 실제 약 6.06 rpm인 failure case
- 20 rpm shallow: low-amplitude failure case
- preferred 12/15/20 rpm 세션은 별도로 표시되어 있음

이 자료는 기존 device-domain evidence로는 유용하지만 M-C0 formal evidence로 바로 승격할 수 없다. 현재 manifest에는 M-C0가 요구하는 operator ID, 센서 높이, 각도/방향, 자세, 의복/이불, background movement, 다른 사람의 존재·거리, workplace permission을 세션별 필드로 연결한 기록이 없다. 또한 모든 세션이 `S001`이므로 subject generalization 근거가 아니다.

## reference와 signal semantics

기존 breath 비교 파일의 reference는 독립 생체 reference가 아니라 `paced cue target`이다. 따라서 phase가 paced cue를 따라간다는 근거는 있지만, 정상 자발 호흡의 실제 호흡수 정확도 reference는 아니다.

기존 heart-watch 비교는 exploratory reference로 표시되어 있고 `heart_verified=false`다. 10개 paired point의 MAE는 16.6 bpm, within-5-bpm rate는 0%로 기록되어 있다. 따라서 heart rate는 M-C0에서 검증 완료로 표시할 수 없다.

offline candidate와의 비교에서 확인되는 것은 입력 계약뿐이다.

- preprocessing: `BPF_ZSCORE`
- input: `int8`, shape `[1, 300, 1]`
- window: 30초
- model lock: `MR60_device_validation_complete=false`, `deployment_ready=false`

현재 raw phase 값의 단위·스케일·firmware filtering·reset·missing semantics가 offline phase와 동등하다는 것은 이 정적 감사만으로 확인할 수 없다.

## M-C0 판정

| 항목 | 판정 |
|---|---|
| 기존 raw 파일이 존재하고 재분석 가능함 | `VERIFIED` |
| schema 1.2의 firmware/config 고정값 | `VERIFIED` |
| schema 1.2 timestamp/sequence 기본 건전성 | `VERIFIED_WITH_EXCEPTIONS` |
| 기존 final manifest와 현재 raw tree의 범위 일치 | `NOT_VERIFIED` |
| 기존 로그의 M-C0 세션 메타데이터 완비 | `NOT_VERIFIED` |
| 정상 자발 호흡의 독립 reference | `UNKNOWN` |
| phase 단위·스케일·reset/missing semantics | `UNKNOWN` |
| subject generalization | `NOT_VERIFIED` |
| heart-rate accuracy | `NOT_VERIFIED` |
| MR60 → ESP32 → USB → Pi 실시간 동작 | `BLOCKED_HARDWARE` |
| 새 환경에서 다른 사람/background movement 영향 | `BLOCKED_HARDWARE` |

결론적으로 기존 raw는 버릴 자료가 아니다. 다만 현재 상태에서 할 수 있는 오프라인 작업은 여기까지다. M-C0를 완성하려면 기존 거리/entry-exit/paced 테스트를 전부 반복하는 것이 아니라, 부족한 세션 metadata·독립 reference·현재 설치 환경·Pi end-to-end 증거만 새로 채워야 한다.
