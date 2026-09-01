# SafeNest 웹·열화상 실행 절차

## 1. 네트워크와 포트

ESP32와 Raspberry Pi를 같은 2.4 GHz 네트워크에 연결한다. 방화벽을 사용하면 TCP `8000`·`9000`과 UDP `5005`를 허용한다.

```text
ESP32 scalar  → TCP 9000 → Pi runtime
ESP32 Thermal → UDP 5005 → Pi runtime → HTTP 8000 → Browser
```

## 2. ESP32 설정과 플래시

1. `ESP32/secret.h.example`을 Arduino sketch 폴더의 `secrets.h`로 복사한다.
2. `WIFI_SSID`, `WIFI_PASSWORD`, `RPI_HOST`를 실제 환경에 맞춘다.
3. `RPI_PORT`는 `9000`으로 유지한다.
4. `ESP32/Arduino/esp32_sensor_node/esp32_sensor_node.ino`의 `THERMAL_UDP_PORT`와 Pi 설정을 동일한 `5005`로 유지한다.
5. Arduino IDE에서 `ESP32 Dev Module`을 선택해 업로드하고 Serial Monitor를 `115200` baud로 연다.

## 3. Raspberry Pi 최초 설치

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-dev build-essential
git clone https://github.com/jinsu1011/safenest-embedded-competition.git
cd safenest-embedded-competition
./run_safenest.sh --install
```

`--install`은 `<repository>/.venv`를 만들고 backend·AI 의존성을 설치한 뒤 preflight와 runtime을 실행한다. 설치 후에는 다음 명령만 사용한다.

```bash
cd ~/safenest-embedded-competition
./run_safenest.sh
```

## 4. 수신 상태 확인

```bash
curl -fsS http://127.0.0.1:8000/health | python3 -m json.tool
curl -fsS http://127.0.0.1:8000/api/status | python3 -m json.tool
curl -sS -D - -o /dev/null http://127.0.0.1:8000/api/thermal/A01
```

`/health`의 `receiver.thermal_udp`에서 완료 프레임과 effective FPS가 증가해야 한다. `/api/thermal/A01`은 완성 프레임이 있으면 `200 application/octet-stream`, 아직 없으면 `204`를 반환한다.

## 5. 브라우저 접속

```text
관리자 웹:          http://RPI_IP:8000/admin
A01 방문자 열화상:  http://RPI_IP:8000/guest/dashboard/A01
통합 대시보드:      http://RPI_IP:8000/dashboard
```

웹 열화상 패널에서 컬러 프레임, `실시간 수신`, 증가하는 Frame 번호와 온도 범위를 확인한다. 동일 프레임만 3초 이상 유지되면 `열화상 수신 중단`으로 전환되는 것이 정상이다.

## 6. 장애 구분

| 증상 | 우선 확인 |
| --- | --- |
| 웹에 접속할 수 없음 | runtime 실행, Pi IP, TCP 8000 |
| 모든 센서가 끊김 | ESP32 Wi-Fi, `RPI_HOST`, TCP 9000 |
| Thermal만 없음 | UDP 5005, Thermal READY/SPI 배선, ESP 전송 카운터 |
| Thermal API가 204 | Pi가 완성된 80×62 프레임을 아직 받지 못함 |
| 오류 문구 표시 | 패킷 크기, 80×62 shape, CRC32, min/max 검증 |
| 프레임이 자주 멈춤 | Wi-Fi 품질과 `/health`의 incomplete/timeout 통계 |

현재 단일 Thermal 장치는 공간 `A01`에 연결된다. 다른 공간에 별도 Thermal 장치를 연결하려면 backend에 공간과 장치 간 명시적 매핑을 추가해야 한다.
