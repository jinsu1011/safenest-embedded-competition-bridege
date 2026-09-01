# SafeNest MR60BHA2 + ESP-WROOM-32 인수인계

## 현재 목표

MR60BHA2의 재실·거리·호흡·심박 원시값을 ESP-WROOM-32에서 안정적으로 수집·검증·안정화·패킷화하여 Raspberry Pi 5로 전달한다. 최종 정상/주의/위험 판단, 센서융합, AI, SQLite, LCD/대시보드는 Pi가 담당한다.

## 반드시 먼저 읽을 문서

- `PROJECT_PROGRESS.md`
- `HARDWARE_RUNBOOK.md`
- `MMWAVE_TUNING.md`
- `TEAM_OPERATING_MODEL.md`
- 프로젝트 PDF: `/Users/kimjinsu/Desktop/대외활동 및 기타/2026/창의혁신공모전/중간보고서/2.가만있어도SANDI_김진수_창의혁신공모전_중간계획서.pdf` (실제 파일 경로는 macOS에서 분해형 한글일 수 있음)

## 확정된 하드웨어와 배선

- 보드: ESP-WROOM-32 기반 ESP32 DevKit, PlatformIO `esp32dev`
- 확인된 칩: ESP32-D0WD-V3 rev 3.1, 4MB flash
- MR60BHA2 전원은 Mac USB → ESP VIN/5V를 사용하고 별도 5V 전원은 동시에 연결하지 않는다.

```text
MR60BHA2          ESP-WROOM-32 DevKit
5V       ───────  VIN/5V
GND      ───────  GND
TX       ───────  GPIO16/RX2
RX       ───────  GPIO17/TX2
```

- UART는 115200bps이다.
- `RX0/TX0`은 사용하지 않는다. 현재 펌웨어는 UART2의 GPIO16/17을 사용한다.

## 현재 코드

- 펌웨어: `devices/mmwave/firmware/src/main.cpp`
- PlatformIO 설정: `devices/mmwave/firmware/platformio.ini`
- 캡처 도구: `devices/mmwave/firmware/capture_serial.py`
- 분석 도구: `devices/mmwave/firmware/analyze_mmwave_log.py`
- 대시보드: `devices/mmwave/firmware/mmwave_dashboard.py`
- 현재 펌웨어는 MR60 Tiny Frame을 직접 파싱하고 10Hz JSONL을 USB로 출력한다. 아직 새 필터나 최종 유효성 임계값을 적용하지 않은 raw 모니터 단계다.

## 버전

- Arduino core: 3.2.0
- Espressif PlatformIO platform: 54.3.20
- MR60 센서 펌웨어는 업데이트하지 않았고 승인 없이 업데이트하면 안 된다.
- MR60 펌웨어 버전 프레임은 아직 수신하지 못해 버전은 미확인이다.

## 2026-07-25 연결 확인 결과

- 현재 Mac 포트: `/dev/cu.usbserial-110` (`/dev/tty.usbserial-110`도 존재). 재연결 시 번호가 달라질 수 있으므로 항상 다시 검색한다.
- 첫 두 번의 15초 캡처에서는 ESP JSON은 나왔지만 MR60 `uart_frames_total=0`, 모든 센서값 null이었다. 원인은 UART 배선 불일치였고 같은 방식 두 번 실패 후 배선을 물리적으로 다시 확인했다.
- 올바르게 재배선한 뒤 15초 캡처 성공:
  - ESP JSON 150개
  - MR60 UART 프레임 1,128개 (`uart_frames_total` 3,604→4,732)
  - 해당 캡처 중 checksum 오류 증가 0
  - 해당 캡처 중 parse 오류 증가 0
  - 누적 checksum/parse 오류 7개는 캡처 시작 전에 이미 존재
  - raw presence 150/150 true
  - 거리 143.5cm
  - 호흡 0~1rpm
  - 심박 97~111bpm
- 사용자는 센서를 통제 조건으로 설치하지 않고 단순히 놓아둔 상태였다고 확인했다. 따라서 presence=true와 생체값은 정확도 또는 오탐 근거가 아니며 UART 통신 성공 증거로만 사용한다.
- 성공 캡처 임시 원본: `/private/tmp/mr60_uart_after_rewire.jsonl`

## Python 실행 환경

- 시스템 Python에는 `pyserial`이 없었다.
- 임시 가상환경 `/private/tmp/safenest-mmwave-venv`에 `pyserial==3.5`를 설치했다. 재부팅/정리 후 사라질 수 있다.
- 성공한 캡처 명령:

```bash
/private/tmp/safenest-mmwave-venv/bin/python \
  devices/mmwave/firmware/capture_serial.py \
  --port /dev/cu.usbserial-110 \
  --baud 115200 \
  --duration 15 \
  --output /private/tmp/mr60_uart_after_rewire.jsonl
```

## 과거 기준선과 실패에서 배운 점

- 약 63cm 정지 인체 5분에서는 raw presence 100%, checksum/parse 오류 0, ESP 재부팅 0이었다.
- 같은 위치 빈 공간 5분에서는 재실 오탐 두 번(약 3.2초, 2.5초)이 있었다.
- 진입·퇴장 시험 두 번 모두 사람이 나간 뒤에도 약 86~98cm 환경물을 사람으로 계속 감지했다.
- 시간 필터만으로는 오탐 제거와 2초 응답 목표를 동시에 만족하지 못했다.
- 결론: 필터 전에 개방 공간, 고정 거치, 전방 반사체 제거, 거리 표식이 필요하다. 과거 로그는 보존하되 새 설치 기준선과 섞지 않는다.

## 현재 체크리스트 상태

- [x] PDF에서 mmWave와 ESP/Pi 역할 확인
- [x] ESP USB 포트와 JSON 출력 확인
- [x] MR60 UART 실제 수신 확인
- [x] 15초 구간 checksum/parse 오류 증가 0 확인
- [ ] 통제된 빈 공간 설치 게이트
- [ ] 무필터 새 기준선 수집
- [ ] WARMUP/VALID/UNKNOWN/FAULT 상태 머신과 유효성 판정
- [ ] 동일 원본 로그로 필터 후보 비교
- [ ] 선택된 최소 필터와 텔레메트리 스키마 구현
- [ ] Pi 수신·융합·위험도 연동
- [ ] 30분/거리/진입·퇴장 최종 검증

## 다음 채팅에서 바로 할 단 한 단계

통제된 빈 공간 게이트부터 한다.

1. MR60을 비금속 고정대에 고정한다.
2. 센서 전방 1.5~2m에서 노트북, 모니터, 금속판, 유리, 벽 근접, 선풍기, 커튼 등 반사·움직임 요인을 제거한다.
3. 사람은 센서 정면에서 완전히 벗어난다.
4. 장기 로그를 시작하지 말고 먼저 60~120초 진단 캡처를 수행한다.
5. raw presence가 연속 false인지 확인한다. true가 나오면 필터를 적용하지 말고 설치물을 바꾼다.

## 이후 실행 순서

1. 빈 공간 5분 무필터 원본
2. 0.8~1.0m 가슴 정면 정지 1인 5분 무필터 원본
3. 진입→정지→퇴장 20회
4. UART 수신률, checksum/parse 오류율, 결측률, 오탐/미탐, 호흡 통계, 진입/퇴장 지연 계산
5. 결측/timeout/0/NaN/범위 밖을 `UNKNOWN`으로 처리하는 상태 머신 구현
6. 원시/이동평균/중앙값/EMA/중앙값+EMA를 동일 로그로 비교
7. 한 번에 필터 또는 임계값 하나만 바꾸고 가장 단순하게 KPI를 통과하는 방식 선택
8. raw와 filtered를 함께 Pi로 전송
9. Pi가 열화상/PIR/CO2와 융합해 정상/주의/위험을 판단
10. 빈 공간 30분, 정지 인체 30분, 진입·퇴장 20회, 0.6/0.9/1.2/1.5m, ESP 재부팅 0회 검증

## 절대 하지 말 것

- 실제 로그 없이 임계값을 확정하지 않는다.
- `0`, null, NaN, timeout을 정상 호흡이나 무호흡으로 바꾸지 않는다.
- 환경 오탐을 긴 시간 필터로 숨기지 않는다.
- ESP에서 최종 정상/주의/위험을 결정하지 않는다.
- 승인 없이 MR60 펌웨어를 업데이트하지 않는다.
- 위험한 숨참기, 과호흡, 밀폐공간, 가스 주입 시험을 하지 않는다.
