# 문제 해결

## Raspberry Pi 로그

```bash
tail -n 100 ~/raspberry_pi_lcd/logs/server.log
tail -n 100 ~/raspberry_pi_lcd/logs/chromium.log
```

## 프로세스와 포트

```bash
ps -ef | grep -E '[p]ython.*server.py|[n]ode.*server.js'
ss -ltn | grep -E ':3000|:8080|:9000'
curl -s http://127.0.0.1:8080/health
```

## ESP32가 연결되지 않음

- ESP32와 Raspberry Pi가 같은 2.4 GHz 네트워크인지 확인
- `secrets.h`의 `RPI_HOST`가 `hostname -I` 결과와 같은지 확인
- `start_lcd.sh`를 ESP32보다 먼저 실행
- Raspberry Pi에서 9000 포트가 LISTEN 상태인지 확인
- ESP32 Serial Monitor를 115200 baud로 열어 네트워크 로그 확인

## 웹은 열리지만 센서값이 갱신되지 않음

```bash
curl -s http://127.0.0.1:8080/api/state
curl -s http://127.0.0.1:3000/api/thermal/A01 -o /tmp/thermal.bin
```

- Python API에 값이 없으면 ESP32↔Raspberry Pi 구간 문제입니다.
- Python API는 정상인데 웹만 멈추면 `RPI_BRIDGE_URL`과 Node.js 터미널 오류를 확인합니다.
- 웹을 노트북에서 실행할 때는 `127.0.0.1`이 노트북 자신을 뜻하므로 `RPI_BRIDGE_URL=http://RPI_IP:8080`으로 지정합니다.

## LCD가 검은 화면 또는 열리지 않음

- `logs/chromium.log` 확인
- Raspberry Pi OS Desktop 세션에서 실행했는지 확인
- `chromium` 또는 `chromium-browser` 명령 존재 여부 확인
- LCD 자체 해상도·HDMI/DSI 연결과 전원 확인

## 열화상이 멈춤

`/health`에서 `thermal_frames_received`와 열화상 `sequence`가 계속 증가하는지 확인합니다. ESP32 로그의 `crc_errors`, `range_errors`가 증가하면 SPI 배선 길이, GND 공통 연결, CS/READY/RESET 핀, 전원 안정성을 점검합니다.

## 포트가 이미 사용 중

```bash
sudo ss -ltnp | grep -E ':3000|:8080|:9000'
```

기존 SafeNest 프로세스라면 정상 종료 스크립트 또는 해당 터미널의 `Ctrl+C`로 종료한 뒤 다시 시작합니다.

