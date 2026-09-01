# 웹과 LCD 백엔드 동작 구조

## 1. 데이터 흐름

ESP32가 센서를 직접 읽고, Raspberry Pi가 중앙 수신기와 화면 서버 역할을 하며, Node.js 서버가 웹용 데이터 모델과 사용자 화면을 제공합니다.

```text
MR60BHA2 ─┐
SCD40 ────┤
PIR ──────┼→ ESP32 ── TCP :9000 ─→ raspberry_pi_lcd/server.py
열화상 ───┘                         ├→ LCD Chromium /display
                                   ├→ HTTP :8080 /api/state
                                   └→ HTTP :8080 /api/thermal
                                               ↓ polling/proxy
                                      SafeNest_Web/server.js :3000
                                               ↓
                                      관리자/방문자 브라우저
```

## 2. ESP32 펌웨어

`esp32_sensor_node.ino`는 다음 작업을 수행합니다.

- MR60BHA2를 UART로 읽어 호흡수와 심박수 측정
- SCD4x를 I²C로 읽어 CO₂ 측정
- PIR 디지털 입력으로 움직임 확인
- Waveshare MI48 계열 열화상을 I²C로 제어하고 SPI로 80×62 프레임 수집
- scalar 센서값은 1초 주기의 JSON 패킷으로 전송
- 열화상은 16바이트 메타데이터와 big-endian `uint16` 픽셀 배열로 전송
- 네트워크가 느릴 때 오래된 열화상 대신 가장 최신 프레임만 유지

센서 측정 루프와 네트워크 전송은 분리되어 있어 TCP 지연이 센서 스케줄을 가능한 한 방해하지 않도록 설계되어 있습니다.

## 3. Raspberry Pi LCD·센서 서버

`raspberry_pi_lcd/server.py`는 Python 표준 라이브러리 기반의 멀티스레드 서버입니다.

- TCP 9000: ESP32 연결을 기다리고 프로토콜 헤더·길이·종류를 검증
- 최신값 저장소: 마지막 센서 JSON과 열화상 프레임을 thread-safe하게 보관
- 데이터 신선도: 일정 시간 새 데이터가 없으면 `stale` 또는 `waiting`으로 표시
- 열화상 검증: 해상도, 길이, 최솟값·최댓값, 온도 범위를 검사해 손상 프레임 폐기
- HTTP 8080: LCD 화면과 상태/열화상 API 제공
- GPIO 부저: 상태가 `emergency`이면 GPIO Zero를 통해 부저 작동
- `state.json`: 방 이름과 수동 상태를 원자적으로 저장

주요 경로는 다음과 같습니다.

| 경로 | 역할 |
|---|---|
| `/display` | Raspberry Pi LCD용 전체 화면 |
| `/control` | 상태와 방 이름을 바꾸는 제어 화면 |
| `/thermal` | 열화상 전용 화면 |
| `/api/state` | 화면 상태와 최신 센서값 JSON |
| `/api/thermal` | 최신 80×62 열화상 바이너리 |
| `/health` | 센서 연결, 프레임, 부저, 오류 상태 |

`start_lcd.sh`는 Python 서버를 백그라운드로 시작하고 Chromium을 키오스크 모드로 `/display`에 연결합니다. `stop_lcd.sh`는 PID 파일을 사용해 두 프로세스를 종료합니다.

## 4. Node.js 통합 웹 서버

`SafeNest_Web/server.js`는 Express 기반이며 기본 포트는 3000입니다.

- `RPI_BRIDGE_URL`의 `/api/state`를 기본 1초마다 polling
- Raspberry Pi의 유효성 플래그를 확인해 CO₂·호흡·심박·PIR·열화상 값을 웹 데이터 모델로 변환
- 위험 규칙에 따라 `normal-empty`, `normal-occupied`, `warning`, `danger`, `emergency`, `offline` 판정
- `/api/thermal/:spaceId`에서 Raspberry Pi 열화상 바이너리를 브라우저로 프록시
- Server-Sent Events(`/api/stream`)로 관리자·방문자 화면에 변경을 전송
- JWT 관리자 로그인, 센서 API 키, QR 방문자 주소 제공
- `data/store.json`에 공간과 이벤트를 원자적으로 저장

연결이 잠깐 끊겨도 즉시 `offline`으로 바꾸지 않고 기본 30초 동안 마지막 정상값을 유지합니다. 이 시간은 `RPI_OFFLINE_GRACE_MS`로 조정합니다.

## 5. 브라우저 열화상 처리

`thermal-client.js`는 `/api/thermal/:spaceId`를 반복 요청합니다. 80×62 `uint16` 값을 섭씨로 변환하고 Canvas에 색상 팔레트로 그립니다. `ETag`를 사용해 같은 프레임을 다시 전송하지 않으며, 일정 시간 프레임 번호가 바뀌지 않으면 수신 중단으로 표시합니다.

## 6. 포트 정리

| 포트 | 프로토콜 | 제공자 | 소비자 |
|---:|---|---|---|
| 9000 | TCP | Raspberry Pi Python | ESP32 센서 노드 |
| 8080 | HTTP | Raspberry Pi Python | LCD, 노트북, Node.js 웹 |
| 3000 | HTTP | Node.js Express | 노트북·휴대폰 브라우저 |

## 7. 데이터가 화면에 나타나는 과정

1. ESP32가 센서값을 읽습니다.
2. TCP 패킷을 Raspberry Pi 9000번 포트로 보냅니다.
3. Python 서버가 검증하고 최신값을 메모리에 저장합니다.
4. LCD의 JavaScript가 `/api/state`와 `/api/thermal`을 읽어 표시합니다.
5. Node.js 서버도 `/api/state`를 주기적으로 읽어 위험 상태를 계산합니다.
6. 웹 브라우저는 REST와 SSE를 통해 센서값·이벤트를 받고 열화상 프록시를 Canvas로 표시합니다.

