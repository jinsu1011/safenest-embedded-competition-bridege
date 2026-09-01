# SafeNest CO₂ C-C0 팀원 SCD40 실측데이터 평가

**평가일:** 2026-08-14
**평가 대상:** 팀 저장소에 이미 존재하는 SCD40 legacy 측정 파일
**현재 판정:** B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE
**문서 성격:** 사람이 읽는 C-C0 평가·인수인계 문서
**이번 평가 범위:** 모델 실행, 신규 실측, 모델/런타임/펌웨어 변경, 팀 저장소 수정은 수행하지 않음.

## 결론부터

이번 데이터는 쓸모없는 데이터가 아닙니다. 실제 SCD40 하드웨어 경로에서 CO₂ 값이 들어왔고, ESP32에서 Raspberry Pi로 전달되는 동안 정상, 지연, 연결 끊김 상태도 기록되었습니다.

다만 이 데이터만으로는 SafeNest의 고정된 B5 모델을 평가할 수 없습니다. B5가 요구하는 입력은 다음 네 가지입니다.

~~~text
CO2 + Temperature + Humidity + CO2_slope
~~~

현재 legacy capture에는 CO₂만 남아 있습니다. Temperature와 Humidity는 SCD40 읽기 함수에서 잠시 읽혔지만 telemetry와 CSV에 전달되지 않았습니다. 또한 CSV의 1초 간격은 logger와 transport의 시간 간격일 뿐, 각 행이 새로운 SCD40 측정 이벤트라는 증거가 아닙니다.

따라서 현재 결론은 다음과 같습니다.

> 실제 장치 CO₂ 근거는 확인됨. 그러나 frozen B5 feature vector가 불완전하므로 B5 inference와 formal device-domain validation은 차단됨.

## 1. 이번 평가에서 확인한 기준점

| 구분 | 기준 |
|---|---|
| standalone 저장소 최신 main | c65d2e32e6f14089790a8c576312eb9873e367f7 |
| team 저장소 최신 main | 5947334d3d0f6c6f7d6100c7ea6af219e5b4c5d5 |
| 활성 master roadmap | [docs/20260810_ChatGPT_SafeNest_Multisensor_Parallel_Execution_Roadmap_01.md](../20260810_ChatGPT_SafeNest_Multisensor_Parallel_Execution_Roadmap_01.md) |
| B5 lock | [datasets/co2/manifests/c_b5_robustness_final_lock/final_candidate_lock.json](../../datasets/co2/manifests/c_b5_robustness_final_lock/final_candidate_lock.json) |
| B5 feature metadata | [models/co2/candidates/c_b5/final_candidate_metadata.json](../../models/co2/candidates/c_b5/final_candidate_metadata.json) |

팀 저장소의 실제 근거 경로는 다음과 같습니다.

~~~text
devices/co2/firmware/logs/
devices/co2/firmware/capture_scd40.py
devices/co2/docs/VERIFICATION_REPORT_2026-08-12.md
display-test2/esp32_sensor_node/esp32_sensor_node.ino
display-test2/raspberry_pi_lcd/server.py
display-test2/docs/COMMUNICATION_PROTOCOL.md
~~~

## 2. 데이터는 어떻게 들어왔는가

이번 raw CSV는 SCD40에서 직접 I²C로 한 행씩 기록한 파일이 아닙니다. 실제 경로는 다음과 같습니다.

~~~text
SCD40
  → ESP32가 측정값 읽기
  → ESP32 telemetry snapshot
  → TCP로 Raspberry Pi 전달
  → Pi가 최신 telemetry를 cache
  → Pi /health 응답
  → capture_scd40.py가 /health를 약 1초마다 기록
  → CSV
~~~

확인된 세부사항:

- SCD40 I²C 주소는 0x62로 기록되어 있습니다.
- ESP32는 SCD4x periodic mode를 사용합니다.
- ESP32는 약 250 ms마다 data-ready 상태를 확인합니다.
- telemetry snapshot은 약 1초마다 발행됩니다.
- Pi는 마지막으로 받은 telemetry를 보관하고, 일정 시간 이상 새 패킷이 없으면 transport를 stale로 표시합니다.
- CSV의 co2_ppm은 이 경로를 거친 CO₂ 값입니다.
- CSV의 device_id인 esp32-01은 ESP32 telemetry 장치 ID이며, 개별 SCD40의 고유 serial number가 아닙니다.

즉, “실제 장치에서 나온 CO₂ telemetry”라고는 할 수 있지만, “각 CSV 행이 새로운 SCD40 conversion을 직접 대표한다”고까지 말할 수는 없습니다.

## 3. 실제 파일별 결과

현재 team main의 raw bytes를 다시 읽어 계산한 결과입니다.

| 파일 | 상황 이름 | 전체 행 | valid | invalid | invalid 사유 | 유효 CO₂ 범위 |
|---|---|---:|---:|---:|---|---:|
| devices/co2/firmware/logs/2026-08-12_preflight_30s.csv | preflight | 30 | 30 | 0 | 없음 | 504–634 ppm |
| devices/co2/firmware/logs/2026-08-12_baseline_5min.csv | baseline | 300 | 277 | 23 | NOT_CONNECTED 14, STALE 9 | 495–506 ppm |
| devices/co2/firmware/logs/2026-08-12_baseline_attempt02_5min.csv | baseline | 300 | 300 | 0 | 없음 | 505–516 ppm |
| devices/co2/firmware/logs/2026-08-12_breath-rise-recovery_6min.csv | breath-rise-recovery | 360 | 329 | 31 | NOT_CONNECTED 16, STALE 15 | 507–1493 ppm |
| **합계** | — | **990** | **936** | **54** | **NOT_CONNECTED 30, STALE 24** | **495–1493 ppm** |

logger의 host interval은 네 파일 모두 대체로 1초였습니다. 파일별 최소/최대/평균 간격은 다음과 같습니다.

| 파일 | 최소 / 최대 / 평균 간격(초) |
|---|---|
| preflight | 0.999363 / 1.000655 / 0.999998 |
| baseline | 0.998974 / 1.000640 / 0.999998 |
| baseline attempt02 | 0.997832 / 1.002460 / 0.999996 |
| breath-rise-recovery | 0.999451 / 1.000536 / 1.000000 |

여기서 valid는 단순히 co2_ppm 숫자가 존재한다는 뜻이 아닙니다. capture script 기준으로 CO₂ 값이 숫자이고, CO₂ valid flag가 true이며, 연결 상태와 transport freshness가 모두 유효해야 valid입니다.

## 4. invalid 행은 버릴 행이 아니라 중요한 증거다

54개 invalid 행은 다음처럼 남아 있습니다.

- NOT_CONNECTED 30개
- STALE 24개

이 행들은 0으로 바뀌거나 정상값으로 대체되지 않았습니다. 따라서 현재 데이터는 연결 끊김과 지연 상태가 존재했다는 사실을 보여줍니다.

다만 이 결과가 새로운 물리적 disconnect 실험을 완료했다는 뜻은 아닙니다. 팀 verification report도 정상 측정과 호흡 상승 반응은 확인했지만, 요구된 형식의 완전한 disconnect 검증은 완료되지 않았다고 기록합니다. 기존의 PARTIAL 경계를 유지해야 합니다.

## 5. CSV 안에 있는 것과 없는 것

CSV에는 다음 정보가 있습니다.

- Pi가 기록한 host timestamp, Unix time, monotonic time
- scenario 이름
- ESP32 device_id, sequence, uptime
- co2_ppm
- valid, connected, fresh, transport_status
- peer, age_seconds, last_received_at
- 당시 /health 응답의 raw_response_json

하지만 다음 정보는 없습니다.

- SCD40의 Temperature
- SCD40의 Humidity
- 각 값이 새 SCD40 conversion에서 나왔다는 fresh measurement event marker
- SCD40 개별 센서 serial number
- 독립적이고 동기화된 occupancy ground truth

ESP32 코드에서는 SCD40의 readMeasurement 호출에 temperature와 humidity 변수가 들어옵니다. 그러나 그 값들은 Snapshot과 telemetry JSON에 넣지 않고, co2Ppm만 발행합니다. 그러므로 “센서가 내부적으로 T/RH를 읽었을 가능성”과 “검증 가능한 raw evidence에 T/RH가 보존되어 있음”은 구분해야 합니다. 이번 평가에서 후자는 NO입니다.

## 6. 1초 간격이 곧 1초 센서 측정은 아니다

이번 데이터에서 가장 조심해야 할 부분입니다.

1. SCD4x periodic mode의 새 측정은 약 5초 주기로 설명되어 있습니다.
2. ESP32는 250 ms마다 data-ready를 확인합니다.
3. ESP32는 최신 CO₂ 값을 약 1초마다 telemetry로 보냅니다.
4. Pi는 마지막 telemetry를 cache하고 /health로 제공합니다.
5. capture script가 그 /health를 약 1초마다 읽습니다.

따라서 CSV의 1초 행 간격은 logger polling cadence를 보여줄 뿐입니다. 연속된 두 행이 서로 다른 SCD40 측정 이벤트에서 왔다는 뜻은 아닙니다.

정리하면:

| 항목 | 상태 |
|---|---|
| logger가 약 1초 간격으로 기록했다 | VERIFIED |
| Pi transport freshness가 기록됐다 | VERIFIED_AS_REPRESENTED |
| SCD40 새 측정 여부가 각 행에 기록됐다 | UNKNOWN |
| 각 행과 새 SCD40 conversion의 1:1 대응 | 확인 불가 |
| H150 slope의 정식 검증 | 불가 |

그래서 host timestamp로 계산한 CO₂ slope는 진단용으로는 볼 수 있어도, frozen B5 입력으로 승격할 수 없습니다.

## 7. Temperature/Humidity 판정은 availability와 semantics를 나눠야 한다

현재 raw evidence에서 정확한 표현은 다음입니다.

| 항목 | 판정 | 의미 |
|---|---|---|
| Temperature availability | NO | CSV와 nested telemetry JSON에 값이 없음 |
| Humidity availability | NO | CSV와 nested telemetry JSON에 값이 없음 |
| Temperature semantic correspondence | UNKNOWN / NOT_ASSESSABLE | 비교할 captured field가 없으므로 semantics 불일치를 확인할 수 없음 |
| Humidity semantic correspondence | UNKNOWN / NOT_ASSESSABLE | 비교할 captured field가 없으므로 semantics 불일치를 확인할 수 없음 |

즉, T/RH를 사용할 수 없다는 것과 T/RH semantics가 서로 맞지 않는다는 것은 다른 주장입니다.

이번 데이터로 말할 수 있는 것은:

> T/RH가 capture되지 않아 B5 입력으로 사용할 수 없다.

이번 데이터로 말할 수 없는 것은:

> T/RH를 비교해 보니 모델 feature semantics와 다르다.

후자의 결론을 내릴 captured T/RH가 없기 때문입니다.

## 8. raw_response_json과 cache의 의미

990개 행의 raw_response_json은 모두 JSON으로 읽혔습니다. 모든 행에 숫자형 cached sensors.co2_ppm과 sensors.valid.co2=true가 있었고, temperature 또는 humidity에 해당하는 nested key는 없었습니다.

그렇다고 990개 행이 모두 fresh valid sample인 것은 아닙니다. 일부 행은 Pi가 이전 CO₂ 값을 가지고 있더라도 현재 transport가 stale이거나 disconnected이기 때문에 capture-level valid가 false입니다.

이 차이는 중요합니다.

~~~text
숫자 CO₂ 값이 존재함
≠
새로운 센서 측정이며 현재 transport가 유효함
~~~

이 차이를 없애고 모든 숫자를 정상 sample로 취급하면 fail-closed evidence contract를 깨게 됩니다.

## 9. checksum 결과와 raw immutability

현재 team main의 raw 파일을 다시 hash한 값과, 과거 analysis summary 및 verification report에 기록된 값은 일치하지 않습니다.

| 파일 | 현재 raw SHA-256 | 과거 기록 SHA-256 | 일치 |
|---|---|---|---|
| preflight_30s.csv | e414be88d5b246411143b7353493565f8fea95bd6fd7f8120804c478f89c41fb | dea523b77258b8cf6f08987e575102c2aa29877fb96b8cbcf05985acd5918f2f | NO |
| baseline_5min.csv | f9fee44ef154bc03ff2c3e0704b3b2c9732841b8510656585b4e7ed9226b6357 | 11f58c3d624cff907f033fdcaa1e1041614a6aad282c3b6005efb052c7af7c42 | NO |
| baseline_attempt02_5min.csv | 741e9a48b77bd8c8a4bbff31f795b1b66f748e8e3dcb36efa2b3470ef60e4d4f | 409b788437e4685f8136f6d6b19c2f47d3ecd081ee56f46d958bf6ab486f9ad1 | NO |
| breath-rise-recovery_6min.csv | b9d01bb96aedd0df68e4f13a8ae2d4512f67e64d359a44a1c4c8c2642d110b32 | 2f5a2b7b6e4baf4d2544baefc3c0e3a65dc082bac7a95565002d784454a096c9 | NO |

따라서 raw에 대한 판정은 다음과 같습니다.

~~~text
RAW_BYTES_AVAILABLE: YES
RAW_IMMUTABILITY: PARTIAL
HISTORICAL_SHA256_MATCH: NO
POST_CAPTURE_BYTE_STABILITY: UNVERIFIED
~~~

현재 파일이 존재하고 읽힌다는 사실은 확인할 수 있습니다. 그러나 과거 분석에 사용된 원본 바이트와 현재 파일이 동일하다고 주장할 수는 없습니다. 이 mismatch를 숨기고 immutable verified로 올리면 안 됩니다.

## 10. Ground truth는 무엇인가

이번 raw 파일에는 독립적이고 시간 동기화된 occupancy ground truth가 없습니다.

다음 항목들은 occupancy ground truth가 아닙니다.

- baseline이라는 파일명이나 scenario 이름
- breath-rise-recovery라는 상황 설명
- CO₂가 올라갔다는 사실
- telemetry에 포함된 PIR motion
- 파일명이나 운영자의 사후 해석
- 나중에 실행할 B5 모델의 출력

따라서 이번 데이터로 occupancy F1, AUROC, accuracy, precision, recall, confusion matrix를 만들 수 없습니다. CO₂ 상승은 센서 반응 evidence이지, 그 자체로 사람의 occupancy label은 아닙니다.

## 11. 왜 B5를 실행하면 안 되는가

standalone의 B5 candidate는 다음 feature order로 lock되어 있습니다.

~~~text
CO2, Temperature, Humidity, CO2_slope
~~~

현재 legacy evidence는:

- CO₂: 숫자 값은 있음. 다만 일부 행은 transport-invalid이므로 PARTIAL.
- Temperature: 없음.
- Humidity: 없음.
- CO2_slope: host chronology는 있으나 fresh SCD40 chronology가 없어 UNKNOWN.
- H150: DIAGNOSTIC_ONLY.

따라서 다음 방식은 허용되지 않습니다.

- T/RH를 0이나 평균값으로 채우기
- T/RH를 CO₂ 값으로 대체하기
- slope를 단순 CSV 차분으로 계산하고 정식 feature라고 부르기
- invalid 행을 정상값으로 바꾸기
- legacy 데이터에 맞춰 threshold나 model을 다시 조정하기

B5 결과를 내기 위해 feature vector를 억지로 완성하면, 그것은 locked candidate의 device-domain validation이 아니라 다른 실험이 됩니다. 이번 C-C0에서는 그 실험을 하지 않습니다.

## 12. 이번 C-C0에서 확정할 수 있는 것

확정 가능한 내용:

1. 실제 SCD40 하드웨어 경로에서 CO₂ telemetry가 생성되었습니다.
2. ESP32에서 Pi로 가는 transport와 Pi cache의 상태 표시가 확인되었습니다.
3. 현재 raw snapshot은 4개 파일, 990개 행입니다.
4. 936개 행은 capture script 기준 valid이고, 54개 행은 명시적으로 invalid입니다.
5. CO₂ baseline과 breath-rise-recovery 양상이 관찰됩니다.
6. T/RH가 최종 raw evidence에 보존되지 않았습니다.
7. legacy evidence만으로는 frozen B5 feature vector를 채울 수 없습니다.

확정할 수 없는 내용:

1. B5가 team 장치 domain에서 어느 정도 성능을 내는지.
2. occupancy 분류 성능이 어떤지.
3. H150 slope가 새 SCD40 conversion 기반인지.
4. 현재 raw bytes가 최초 capture bytes와 동일한지.
5. T/RH semantics가 틀렸는지.
6. 임상/의학적 안전성 또는 성능 결론이 있는지.

## 13. 다음 단계로 남은 측정 설계 gap

다음 C-C1에서 다뤄야 할 gap은 다음과 같습니다. 이것은 최종 protocol freeze가 아니라, 현재 evidence가 부족한 항목의 목록입니다.

- 같은 SCD40 read event의 Temperature와 Humidity를 보존할 것
- 새 측정 여부를 검증할 수 있는 fresh-measurement marker 또는 동등한 계약을 만들 것
- 검증된 fresh event에 대응하는 신뢰 가능한 timestamp를 보존할 것
- 센서와 세션의 고유 identity를 남길 것
- measurement mode와 관련 설정을 남길 것
- 필요 시 calibration, pressure, altitude, temperature offset 등의 설정을 남길 것
- power cycle, reset, disconnect, timeout, recovery를 명시할 것
- ground truth의 출처·소유자·동기화 시각을 명시할 것
- capture-time manifest와 checksum의 관계를 명확히 할 것
- sensor freshness, transport freshness, logger polling cadence를 서로 분리할 것

이 gap 목록은 외부 데이터 수집이나 B5 실행을 자동 승인하지 않습니다. roadmap의 C-C1 protocol freeze와 operator handoff가 먼저입니다.

## 14. C-C0 최종 상태 요약

~~~text
REAL_DEVICE_SOURCE: VERIFIED
SCD40_MODEL_IDENTITY: VERIFIED
UNIQUE_SCD40_DEVICE_IDENTITY: UNKNOWN
RAW_BYTES_AVAILABLE: YES
RAW_IMMUTABILITY: PARTIAL
HISTORICAL_SHA256_MATCH: NO
LOGGER_POLL_CADENCE: VERIFIED_APPROX_1S
TRANSPORT_FRESHNESS: VERIFIED_AS_REPRESENTED
SCD40_FRESH_MEASUREMENT_CADENCE: UNKNOWN
CO2_AVAILABILITY: YES
CO2_SEMANTIC_CORRESPONDENCE: PARTIAL
TEMPERATURE_AVAILABILITY: NO
TEMPERATURE_SEMANTIC_CORRESPONDENCE: UNKNOWN_NOT_ASSESSABLE
HUMIDITY_AVAILABILITY: NO
HUMIDITY_SEMANTIC_CORRESPONDENCE: UNKNOWN_NOT_ASSESSABLE
CO2_SLOPE_TEMPORAL_CORRESPONDENCE: UNKNOWN
ENDPOINT_H150: DIAGNOSTIC_ONLY
OCCUPANCY_GROUND_TRUTH: ABSENT
FORMAL_DEVICE_DOMAIN_VALIDATION: NO
FROZEN_B5_INFERENCE: BLOCKED
C_C0_OUTCOME: B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE
NEXT_STAGE: C_C1_PROTOCOL_FREEZE_AND_OPERATOR_HANDOFF
~~~

## 15. 인수인계 메모

앞으로 이 결과를 사용할 때의 기준은 간단합니다.

- 현재 raw 파일은 legacy evidence로 보존합니다.
- 과거 checksum mismatch를 무시하지 않습니다.
- T/RH를 추정하거나 대체하지 않습니다.
- fresh event 증거가 없는 slope를 B5 입력으로 승격하지 않습니다.
- invalid 행을 정상값으로 만들지 않습니다.
- legacy evidence 축적과 model development를 분리합니다.
- C-C1, C-C2, C-D 순서는 활성 roadmap을 따릅니다.

이번 증거 평가는 모델 실행, 신규 실측, 모델/런타임/펌웨어 변경, 팀 저장소 수정을 수행하지 않았습니다.
