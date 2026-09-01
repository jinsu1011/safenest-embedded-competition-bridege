# MR60BHA2 다음 세션 실행 체크리스트

이 파일은 다음 채팅 또는 다른 팀원이 **기존 시험을 반복하지 않고 남은 물리 검증만 이어가기 위한 단일 기준 문서**다.

## 0. 시작 상태

- Git branch: `codex/mmwave-phase-integration`
- 기준 commit: `41af82b89ef8b47a15e380583ea0eac37384406e`
- ESP 대상: ESP-WROOM-32 (`esp32dev`), MR60은 UART2 RX=GPIO16/TX=GPIO17
- 새 ESP firmware: `safenest-mr60-esp/1.2.0`
- ESP config SHA-256: `b817e8bfd5e52b18275626f7b6a9bd60098ea4b108428a5aaf63600dbc987834`
- 2026-08-01 해소: A·B단계 완료. 포트 `/dev/cu.usbserial-10` (CH340 `1A86:7523`), 칩 ESP32-D0WD-V3 rev v3.1, MAC `cc:7b:5c:f2:1f:ec`.
- 현재 상태: C단계 빈 공간 30분 PASS. D단계 최신 정지 1인 30분은 stable presence 98.77%로 재실 KPI PASS이나 filtered breath 유효률 21.58%로 자연호흡 지속성은 FAIL이다.
- 최신 인수인계 우선 규칙: 12/15/20rpm, 거리 4종, 진입·퇴장 20회는 재측정하지 않는다. 심박 하강은 기준기기 없이는 탐색용이며 정확도 근거로 사용하지 않는다.
- 주의: 2026-08-01 세션 중 ESP32-C6(`cu.usbmodem101`, ESP32-C6FH4)를 잠시 연결했으나 본 펌웨어와 비호환(`board=esp32dev`, `HardwareSerial(2)`, USB CDC 미설정)이라 원래 WROOM-32으로 되돌렸다. 보드를 바꾸려면 펌웨어 포팅과 config 해시 갱신이 선행되어야 한다.
- MR60 센서 자체 firmware는 승인 없이 업데이트하지 않는다.
- 2026-08-03: USB 포트가 `/dev/cu.usbserial-110`으로 바뀌었다. 위의 `-10`을 포함해 문서에 적힌 옛 포트 값은 스테일이다. 매 세션 `find /dev -maxdepth 1 -name 'cu.usb*' -print`로 다시 확인한다.
- 2026-08-03 미처리 잠재 결함(캡처 세션 종료 후 처리): `windowReady()`(`src/main.cpp:97`)가 phase 프레임 288초 두절 뒤에도 `true`를 유지하고, `filteredBreathValid`(`src/main.cpp:328`)가 phase 신선도를 검사하지 않는다. 실제 오출력은 0건이나 조건이 맞으면 묵은 호흡수를 유효값으로 내보낼 수 있다. 펌웨어를 고치면 config 해시가 바뀌므로 진행 중인 캡처 비교가 끝난 뒤에만 수정한다.

## 1. 다시 하지 않을 작업

다음 항목은 완료됐으므로 처음부터 재수집하거나 임계값을 다시 고르지 않는다.

- [x] 빈 공간 6분과 0.8–1.0m 정지 1인 6분 기준선
- [x] 진입→정지→퇴장 20회 기존 기준선
- [x] 12/15/20rpm 각 60초 warmup+180초 측정
- [x] raw/이동평균/중앙값/EMA/중앙값+EMA 동일 로그 비교
- [x] vendor 호흡수 필터 미채택 결정
- [x] Pi `breath_phase` 30초 FFT 선택
- [x] 0/null/NaN/timeout/부재의 UNKNOWN/FAULT 처리
- [x] 심박 `UNVERIFIED`, 무호흡 `apnea_verified=false` 안전 계약
- [x] Pi 전체 회귀 80 PASS, 2 SKIP
- [x] **R1 펌웨어 C++ ↔ Python 동치성 (2026-08-03 완료)** — 포팅 버그 없음. 다시 하지 않는다.
  - 도구: `devices/mmwave/firmware/analysis_tools/r1_fw_python_equivalence.py`
  - `breath_filtered_valid` 게이트 판정 불일치 51/18,276 (0.279%), std p99 0.00609, rate p50 0.0328rpm
  - 잔여 불일치는 전부 (a) replay 워밍업 300패킷, (b) 26~30분 phase 두절 구간,
    (c) 로그 `breath_phase` 소수 2자리 양자화로 설명된다. 상세는 `docs/operations/PROJECT_PROGRESS.md` 2026-08-03 절.
  - 파생 제약: 자연 대역(std 0.10~0.20)에서 Python 후처리 재현은 3% 수준의 큰 꼬리를 가지므로
    호흡수 정확도의 1차 근거는 ESP가 직접 출력한 `breath_rate_filtered`로 한다.

채택된 원본 6개의 경로와 SHA-256은 `datasets/mmwave/mr60_20260728_manifest.json`이 기준이다. `preflight`, `attempt02`, `quickcheck`, `retry` 파일은 실패·진단 기록이므로 최종 통계에 넣지 않는다.

## 2. 사용자가 준비할 것

- [ ] ESP-WROOM-32 + MR60 기존 4선 배선 유지
- [ ] USB **데이터** 케이블
- [ ] 센서를 흔들리지 않게 고정할 거치대
- [ ] 가슴 중심과 센서 안테나 면을 같은 높이로 맞출 공간
- [ ] 바닥 거리표시 0.6/0.9/1.2/1.5m
- [ ] 전방 1.5m 안의 움직이는 물체·선풍기 바람·커튼 제거
- [ ] 심박 검증 단계에서 Apple Watch와 착용자 1명

금지 시험: 숨참기, 과호흡, 밀폐공간, 가스 주입. 평소처럼 자연 호흡한다.

## 3. 실행 순서

모든 명령은 저장소 최상위에서 실행한다. Python은 반드시 아래 프로젝트 가상환경을 사용한다.

```bash
devices/mmwave/firmware/.venv/bin/python
```

명령의 `YYYY-MM-DD`는 실제 시험일, `/dev/cu.usbserial-XXXX`는 A단계에서 확인한 실제 포트로 한 번만 치환한다.

### A. USB 포트 확인과 점유 해제

- [x] 2026-08-01 확인 완료: `/dev/cu.usbserial-10` 1개. 다음 명령에서 `/dev/cu.usb...` 포트 1개를 확인한다.

```bash
pio device list
ls /dev/cu.usb*
```

- [x] 2026-08-01 `lsof` 결과 점유 프로세스 없음. 대시보드·시리얼 모니터가 실행 중이면 `Ctrl+C`로 종료한다. 캡처와 대시보드는 같은 포트를 동시에 열지 않는다.

```bash
lsof /dev/cu.usb*
```

종료 기준: 포트가 보이고, 업로드 직전 다른 프로세스가 점유하지 않는다.

### B. 새 ESP firmware 업로드

- [x] 2026-08-01 업로드 완료(해시 검증 통과, RAM 6.7%/Flash 20.3%). MR60 firmware가 아니라 ESP firmware만 업로드한다.

```bash
cd devices/mmwave/firmware
pio run
pio run -t upload --upload-port /dev/cu.usbserial-XXXX
cd ../..
```

- [x] 2026-08-01 완료: schema 1.2 최종 로그 `logs/final/2026-08-01_healthcheck_v120_75s.jsonl`, SHA-256 `eb4c57a16ea00d6b4314364f298cac2420a0f9cf3023eed15d02dcdd95835382`, 통과 기준 충족.

```bash
devices/mmwave/firmware/.venv/bin/python \
  devices/mmwave/firmware/capture_serial.py \
  --port /dev/cu.usbserial-XXXX --duration 15 \
  --output devices/mmwave/firmware/logs/final/YYYY-MM-DD_healthcheck_v120_75s.jsonl
```

통과 기준:

- boot event의 firmware가 `safenest-mr60-esp/1.2.0`
- config hash가 이 문서 0절과 동일
- JSON이 연속 출력됨
- `checksum_errors`, `parse_errors`가 증가하지 않음
- `sensor_state`가 계속 `FAULT`가 아님

실패 시: RX/TX 교차, 공통 GND, 5V, 포트 점유를 한 번씩 확인한다. 같은 업로드/배선을 두 번 확인해도 실패하면 반복하지 말고 로그와 원인을 `PROJECT_PROGRESS.md`에 기록한다.

### C. 빈 공간 30분 — 2026-08-01 완료

- [x] 감지 원뿔에서 사람과 반려동물이 완전히 벗어난 상태로 1,800초 수집했다.
  - 사전 확인: `logs/final/2026-08-01_empty_v120_preflight_60s.jsonl`, 600패킷, raw/stable presence 오탐 0.
  - 본 로그: `logs/final/2026-08-01_empty_v120_30min.jsonl`, SHA-256 `32ee3ae455ccf46029840f71268fdda37a88a963eed7ac7c7f9dfb269d00b3b2`.
  - 17,995패킷/1,799.781초, reboot·checksum/parse 오류·raw/stable presence·생체신호·freeze 오탐 전부 0.

```bash
devices/mmwave/firmware/.venv/bin/python \
  devices/mmwave/firmware/capture_serial.py \
  --port /dev/cu.usbserial-XXXX --duration 1800 \
  --output devices/mmwave/firmware/logs/final/YYYY-MM-DD_empty_v120_30min.jsonl

devices/mmwave/firmware/.venv/bin/python \
  devices/mmwave/firmware/analyze_mmwave_log.py \
  devices/mmwave/firmware/logs/final/YYYY-MM-DD_empty_v120_30min.jsonl \
  --output devices/mmwave/firmware/analysis/final/YYYY-MM-DD_empty_v120_30min_summary.json
```

통과 기준: ESP reboot 0, UART checksum/parse 오류율 보고, stable presence 오탐 0 목표, 호흡·심박 0을 유효값으로 세지 않음.

### D. 정지 1인 30분 — 2026-08-01 재실 KPI 통과, 호흡 지속성 미통과

- [x] 센서 안테나 면–가슴 약 0.9m, 정면, 평소 호흡으로 1,860초 수집했다. 처음 60초는 제외했다.
  - 원본: `logs/final/2026-08-01_occupied_d09_v120_31min.jsonl`, SHA-256 `bcd947ed341944065fe47ca21b7cfedd30a37064eea78b5c496ef1c190597f0d`.
  - 분석 17,988패킷/1,799.839초, reboot·checksum/parse 오류 0, stable presence 84.84%로 95% 기준 미달.
  - 해제 9구간/총 271.858초/최장 176.041초, filtered breath 유효률 29.76%, 저진폭 43.22%.
  - 불완전 JSON 1줄은 원본 그대로 보존하고 분석에서 제외했다. 같은 설치로 즉시 반복하지 않고 해제 구간·위상 진폭·설치 정렬을 먼저 진단한다.
  - 위치 조정 후 3분 게이트도 전체 stable presence 90.77%, 첫 60초 제외 86.16%로 미통과했다. 거리 중앙값 74.62cm, 저진폭 42.41%였으므로 단순 거리 조정 반복은 중단한다.
  - 높이·각도 정렬 후 최종 3분 게이트는 raw/stable presence 100%, 오류·freeze 0으로 재실 기준을 통과했다. 그러나 저진폭 90.43%, filtered breath 유효률 9.57%로 호흡 기준은 미통과해 31분 반복은 보류한다.
  - 이후 사용자 재배치 상태의 1분 확인(`positioncheck_attempt03_60s`)은 599패킷 모두 raw/stable/vital presence 및 filtered breath 유효 100%, 전 패킷 VALID, 오류·freeze·저진폭 0으로 통과했다. 거리 중앙값은 97.58cm였다. 이 설치 상태를 유지하되 1분 결과만으로 30분 KPI를 통과 처리하지 않는다.
  - 같은 상태로 수행한 31분 재검증(`occupied_d09_v120_31min_attempt02`, 첫 60초 제외)은 stable presence 98.77%로 재실 95% 기준을 통과했다. 그러나 filtered breath 유효률 21.58%, 저진폭 58.92%였고 마지막 5분에 거리 중앙값이 97.58cm에서 166.46cm로 바뀌며 vital presence 4.10%, freeze 85.59%가 되어 전체 장기 검증은 미통과다.
  - 마지막 5분을 제외한 가운데 25분 재분석에서도 stable/vital presence 98.52%, freeze·통신 오류 0으로 재실은 통과했지만 filtered breath 유효률 25.90%, 저진폭 69.95%로 호흡 지속성은 미통과다. 따라서 마지막 5분만 제외해 전체 PASS로 바꾸지 않는다.

```bash
devices/mmwave/firmware/.venv/bin/python \
  devices/mmwave/firmware/capture_serial.py \
  --port /dev/cu.usbserial-XXXX --duration 1860 \
  --output devices/mmwave/firmware/logs/final/YYYY-MM-DD_occupied_d09_v120_31min.jsonl

devices/mmwave/firmware/.venv/bin/python \
  devices/mmwave/firmware/analyze_mmwave_log.py \
  devices/mmwave/firmware/logs/final/YYYY-MM-DD_occupied_d09_v120_31min.jsonl \
  --skip-seconds 60 \
  --output devices/mmwave/firmware/analysis/final/YYYY-MM-DD_occupied_d09_v120_after60s_summary.json
```

통과 기준: 분석 30분, ESP reboot 0, stable presence 감지율 95% 이상, UART 오류율 보고. 자연호흡 vendor 값은 정확도 기준으로 사용하지 않고 Pi phase 추정의 유효률·표준편차를 함께 계산한다.

### E. 거리 4종 — 기존 원본 검증 완료, 재측정 금지

- [x] 0.6/0.9/1.2/1.5m에서 워밍업 60초+본 측정 약 300초 원본을 확보했다. 기존 6분 원본이 계획된 2분보다 길어 재수집하지 않는다.
- [x] D06/D09/D12/D15 원본 SHA-256이 CSV delivery v2 manifest와 일치함을 2026-08-01 재검증했다.
  - D06: 거리 중앙값 74.62cm, 재실 100%.
  - D09: 거리 중앙값 97.58cm 기준선, 재실 100%.
  - D12: 거리 중앙값 132.02cm, 재실 81.4%로 범위 한계 사례.
  - D15: 거리 중앙값 183.68cm, 재실 88.0% 및 lock-loss 사례.

파일명:

```text
YYYY-MM-DD_occupied_d06_v120_120s.jsonl
YYYY-MM-DD_occupied_d09_v120_120s.jsonl
YYYY-MM-DD_occupied_d12_v120_120s.jsonl
YYYY-MM-DD_occupied_d15_v120_120s.jsonl
```

각 파일은 `capture_serial.py --duration 120`으로 수집하고 `analyze_mmwave_log.py --skip-seconds 60`으로 분석한다.

기록할 값: 줄자 거리, 센서 거리 평균/중앙값/표준편차, stable presence 감지율, phase 호흡 유효률, UART 오류율. 40–150cm 범위는 이 결과를 보기 전에는 변경하지 않는다.

### F. 진입·퇴장 20회 — 기존 원본 재검증 완료, 재측정 금지

- [x] `logs/kpi/2026-07-28_entry_exit_20_v2.jsonl`의 20회 원본과 SHA-256 `f28c41166a0da3104c74b207014aae4ff7be508876175f4881eb72bdb94d5164`를 확인하고 분석기를 재실행했다.
  - 진입 지연 평균/중앙값/최대 1.134/1.073/2.449초, 2초 이내 16/20.
  - 보행·반응 0.8초 차감 참고값은 20/20이 2초 이내다.
  - 퇴장 해제는 19/20, 평균 15.491초이며 2초 기준 0/19이다. MR60 vendor hysteresis 한계로 기록하고 Pi Thermal/PIR 융합으로 보완한다.

```bash
devices/mmwave/firmware/.venv/bin/python \
  devices/mmwave/firmware/entry_exit_trial.py \
  --port /dev/cu.usbserial-XXXX --trials 20 \
  --output devices/mmwave/firmware/logs/final/YYYY-MM-DD_entry_exit_v120_20.jsonl
```

기록할 값: raw와 stable 진입 지연, raw와 stable 퇴장 해제 지연, 미탐 횟수. 진입 전달 2초 목표를 확인한다. MR60 자체 퇴장 해제가 약 15초면 ESP 필터를 억지로 바꾸지 말고 `센서 한계/PI 융합 필요`로 기록한다.

### G. 외부 기준 심박 검증 — 기준기기 없음, UNVERIFIED 유지

- [x] 사용자가 Apple Watch 등 동시 기준기기를 보유하지 않아 정확도 시험을 수행하지 않는 것으로 확정했다.
- [x] `heart_verified=false`, `UNVERIFIED`를 유지하고 MR60 심박 bpm을 위험도·심정지·사람 없음의 단독 근거로 사용하지 않는다.
- [ ] 향후 외부 기준기기를 확보할 때만 0.9m 정면, 60초 warmup+10분 동시 측정으로 MAE·bias·상관·유효률을 계산한다. 현재 MR60 완료를 막는 필수 항목은 아니다.

심박 채택 기준은 팀과 합의해 보고서에 명시한다. 기준을 통과하지 못하면 `heart_verified=false`를 유지하고 표시용으로만 사용한다.

## 4. 시험 중단 기준

- ESP reboot 발생
- `sensor_state=FAULT`가 연속 발생
- checksum/parse counter가 지속 증가
- 포트 연결 해제
- 사람이 없는 상태에서 stable presence가 계속 true
- 사용자 불편·어지러움·호흡 곤란

중단된 로그는 삭제하거나 덮어쓰지 않는다. 파일명에 `_failed_원인`을 붙이거나 manifest에서 `accepted=false`로 분리한다.

## 5. 최종 완료 조건

- [x] 새 ESP firmware 1.2.0 업로드 증거 (2026-08-01, 헬스체크 로그의 `firmware_version`·`config_hash`가 증거)
- [x] 빈 공간 30분 reboot 0, raw/stable presence·생체신호·freeze 오탐 0
- [x] 정지 1인 최신 30분 reboot 0, stable presence 98.77%로 ≥95% 통과. 자연호흡 filtered 유효률 21.58%는 별도 FAIL 한계로 명시
- [x] UART frame/parse/checksum 오류율 계산: 최신 빈 공간·정지 인체 장기 로그 모두 checksum/parse 증가 0
- [x] 거리 4종 결과표와 원본·CSV manifest 해시 재검증
- [x] 진입·퇴장 20회 결과 재분석
- [x] 필터 전후 표준편차·결측률·유효률·지연표
- [x] Apple Watch 없음에 따른 `UNVERIFIED 유지` 결론
- [x] 새 로그 SHA-256 최종 검증 manifest: `analysis/final/2026-08-01_mr60_final_validation_manifest.json`
- [x] `MMWAVE_TUNING_REPORT_2026-07-29.md`에 schema 1.2 최종 물리 검증 결과 갱신
- [ ] 팀 통합 노드에서 실제 ESP USB JSONL 입력 확인

팀 통합 노드 실 USB 입력 확인 전 통합 상태는 `BLOCKED`. MR60 단독 재실 검증은 PASS지만 자연호흡 지속성·심박·무호흡은 각각 FAIL/UNVERIFIED/UNVERIFIED로 제한해 보고한다.

## 6. 다음 세션에 보낼 한 줄

```text
MMWAVE_NEXT_SESSION_CHECKLIST.md를 먼저 읽고, 완료된 로그는 재수집하지 말고 A단계 USB 포트 확인부터 이어서 진행해. 각 단계가 끝날 때 PROJECT_PROGRESS.md와 이 체크리스트를 즉시 갱신해.
```
