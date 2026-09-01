# SafeNest MR60BHA2 ESP 안정화 보고서

STATUS: **CONDITIONAL PASS — 재실 검증 완료, 팀 통합 USB 확인 대기**

ESP firmware 1.2.0 업로드, schema 1.2 회귀, 빈 공간·정지 인체 장기 물리 검증까지 완료했다. 재실 KPI는 통과했으나 자연호흡 위상 유효률은 장시간 유지되지 않아 FAIL이며, 의료 정확도·심박 정확도·무호흡 검출 완료 상태가 아니다. 팀 통합 노드의 실제 USB 입력 확인만 남았다.

## BASELINE

- 센서: Seeed MR60BHA2, ESP-WROOM-32 UART2(GPIO16 RX, GPIO17 TX), 115200 8N1.
- MR60 펌웨어 버전: 현재 protocol 응답과 기존 로그에서 값을 받지 못해 `UNKNOWN`. 승인 없는 MR60 펌웨어 업데이트는 하지 않았다.
- 기존 ESP collector: `tiny-frame-v1`; 최종 ESP firmware: `safenest-mr60-esp/1.2.0`.
- 빌드 환경: PlatformIO Core, espressif32 7.0.1, Arduino-ESP32 3.20017.241212, Xtensa toolchain 8.4.0+2021r2-patch5.
- 수집 조건:
  - 빈 공간 360초(워밍업 60초 뒤 299.893초 분석).
  - 가슴 정면 약 0.8–1.0m 정지 1인 360초(워밍업 60초 뒤 299.831초 분석).
  - 진입→정지→퇴장 20회.
  - 12/15/20rpm: 각 60초 워밍업+180초 cue 기반 측정.
- 빈 공간: 2,999/2,999 presence=false, 거리/호흡/심박 양수값 0, checksum/parse 오류율 0/0, 관측 재부팅 0.
- 정지 1인: 2,998/2,998 presence=true, 거리 평균/중앙값/표준편차 85.46/86.10/1.80cm, checksum/parse 오류율 0/0, 관측 재부팅 0.
- 정지 1인 vendor 호흡수 평균/중앙값/표준편차 22.68/24.0/4.88rpm. 기준 호흡계가 없는 자연호흡 구간이므로 정확도 근거로 사용하지 않는다.
- 정지 1인 vendor 심박수 평균/중앙값/표준편차 83.56/84.0/13.38bpm. 기준 심박계가 없어 `UNVERIFIED`다.

## CHANGES

- ESP 상태 `WARMUP/VALID/UNKNOWN/FAULT`와 원시·stable 재실, field age, error code, firmware/config hash 텔레메트리를 구현했다.
- ESP 유효성 설정:
  - frame timeout 1,000ms(실측 frame rate 약 60–76 frame/s 대비 보수적 한계).
  - 연속 UART 오류 5회 시 FAULT.
  - 재실 최근 3샘플 중 2개.
  - 대상 재실 후 WARMUP 60초.
  - phase age 500ms, 거리 age 1,000ms, vital age 2,000ms.
  - 호흡 유효거리 40–150cm.
- vendor rate에 raw/MA5/median5/EMA0.3/median+EMA를 동일 로그로 비교했다.
- 평활 필터는 채택하지 않았다. 가장 좋은 median+EMA도 표준편차·MAE 개선이 미미하고 평균 0.433초 지연 및 추가 이상치를 만들었다.
- Pi adapter에서 30초 `breath_phase` FFT를 최종 호흡수로 선택했다. vendor 호흡수는 원시 진단값만 전달한다.
- 심박은 원시 표시값만 전달하고 `heart_verified=false`, confidence 최대 0.25로 제한했다.
- 0/NaN/null/timeout/부재/gap은 window를 초기화하고 UNKNOWN 또는 FAULT로 유지한다.
- 미검증 무호흡/AI 후보는 DEGRADED이며 `apnea_verified=true`인 별도 검증 경로만 위험 오버라이드를 허용한다.

## RESULTS

| 항목 | raw/기준 | 채택 결과 |
|---|---:|---:|
| vendor pooled 표준편차 | 4.396rpm | 필터 미채택(phase FFT 사용) |
| median+EMA pooled 표준편차 | 4.359rpm | 미채택 |
| vendor pooled MAE | 3.804rpm | 필터 미채택 |
| median+EMA pooled MAE | 3.791rpm | 미채택 |
| raw 유효률 | 99.481% | 결측 보간 안 함 |
| median+EMA 유효률 | 99.296% | 결측 보간 안 함 |
| median+EMA 추가 지연 | - | 약 0.433초 |
| phase FFT 12/15/20rpm | - | 12.34/15.01/20.01rpm |
| 빈 공간 오탐 | 0/2,999 | 0 |
| 정지 1인 미탐 | 0/2,998 | 0; 100% 감지 |
| 진입 raw 지연 | 평균 1.134초, 최대 2.449초 | 2-of-3 계산상 20/20이 2초 이내 |
| 퇴장 raw 해제 | 평균 약 15.49초 | MR60 내부 지연 한계, 19/20 완료 |
| UART checksum/parse 오류율 | 채택 로그 | 0% / 0% |
| 빈 공간 30분 ESP 안정성 | reboot/UART 오류/오탐 0 | PASS |
| 정지 1인 30분 재실 | stable presence 98.77% | PASS |
| 정지 1인 자연호흡 지속성 | filtered 유효률 21.58% | FAIL/DEGRADED 유지 |

테스트 결과:

- ESP PlatformIO build 성공: RAM 32,356/327,680 bytes(9.9%), Flash 268,765/1,310,720 bytes(20.5%).
- Pi 전체 회귀: LiteRT 2.1.6 환경에서 80 tests PASS, Thermal NPZ 미포함 테스트 2개 SKIP.
- 실측 로그 replay: 12/15/20rpm 중앙 추정값이 각 목표 ±1rpm 이내.

## FILES

- ESP firmware/config: `devices/mmwave/firmware/src/main.cpp`, `include/mmwave_config.h`, `config/mmwave_sensor_config.json`.
- filter 분석: `compare_breath_filters.py`, `analysis/breath/2026-07-28_breath_filter_comparison.json`.
- Pi adapter/config: `devices/mmwave/src/mr60_esp_adapter.py`, `run_mr60_serial_adapter.py`, `devices/mmwave/config/mmwave_processing.json`.
- 위험도 안전 계약: `ondevice_ai/src/risk/`, `ondevice_ai/src/integrated_node/safenest_risk_engine.py`, `sensors/mmwave/mmwave_adapter.py`.
- 원본 manifest: `datasets/mmwave/mr60_20260728_manifest.json`.
- 통합 절차: `docs/ai/MR60_INTEGRATION.md`.
- 채택 원본 로그: manifest에 SHA-256과 함께 명시된 6개 JSONL. 중단·사전시험 로그는 보존하되 제출 manifest에서 제외했다.

## RISKS

- MR60 vendor 호흡수는 실측 속도별 편향이 달라 고정 보정할 수 없다.
- phase FFT는 30초 창이 필요하므로 대상 진입 직후에는 WARMUP이며 즉시 생체값을 제공하지 않는다.
- MR60 자체 퇴장 해제 지연이 약 15초로, ESP 시간필터만으로 2초 퇴장 목표를 달성할 수 없다. Pi에서 PIR/Thermal과 융합해야 한다.
- 심박은 외부 기준기기 동시 로그 전까지 정확도를 주장하거나 단독 위험 근거로 사용할 수 없다.
- 현재 데이터는 1인 정면 축소 프로토타입 조건이다. 천장/광각/다인 환경으로 일반화할 수 없다.
- 무호흡 실험은 수행하지 않았으며 위험한 숨참기 시험을 해서는 안 된다.

## NEXT

다음 세션은 `MMWAVE_NEXT_SESSION_CHECKLIST.md`와 `MR60_FINAL_HANDOFF_PROMPT_2026-08-01.md`만 기준으로 진행한다. 완료된 빈 공간·정지 인체 장기 로그, 거리 4종, 진입·퇴장 20회, 12/15/20rpm은 재수집하지 않는다. 팀 통합 노드에서 실제 ESP USB JSONL 입력만 확인하며 MR60 센서 자체 펌웨어는 업데이트하지 않는다.

## 2026-08-01 SCHEMA 1.2 최종 물리 검증

- ESP `safenest-mr60-esp/1.2.0`, config SHA-256 `b817e8bfd5e52b18275626f7b6a9bd60098ea4b108428a5aaf63600dbc987834` 업로드와 75초 healthcheck를 통과했다.
- 빈 공간 30분은 17,995패킷에서 raw/stable presence·생체신호·freeze 오탐, reboot, checksum/parse 오류가 전부 0으로 PASS다.
- 최신 정지 1인 30분은 stable presence 98.77%(17,753/17,974), reboot·checksum/parse 오류 0으로 재실 ≥95% KPI를 PASS했다.
- 같은 30분의 filtered breath 유효률은 21.58%, 저진폭은 58.92%여서 자연호흡 지속성은 FAIL이다. 마지막 5분을 제외해도 유효률 25.90%, 저진폭 69.95%로 결론이 바뀌지 않는다.
- 마지막 5분의 센서 보고 거리 166.46cm는 피험자 이동 증거로 단정하지 않고 MR60의 타깃 전환 또는 거리 추적 이상 후보로 기록한다.
- 심박은 동시 기준기기가 없어 `heart_verified=false/UNVERIFIED`, 무호흡은 안전한 정답 데이터가 없어 `apnea_verified=false/UNVERIFIED`를 유지한다.
- 거리 4종, 진입·퇴장 20회, 페이싱 12/15/20rpm 원본과 SHA-256은 재검증했으며 재측정하지 않는다.
- 최종 증거 manifest: `devices/mmwave/firmware/analysis/final/2026-08-01_mr60_final_validation_manifest.json`.
