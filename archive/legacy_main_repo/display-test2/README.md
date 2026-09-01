# SafeNest LCD · Raspberry Pi 통신 핵심 코드 공유본

이 폴더는 팀원이 SafeNest의 센서 통신과 LCD 표시 흐름을 빠르게 이해하고 재현할 수 있도록 핵심 파일만 모은 공유본입니다.

## 전체 흐름

```text
ESP32 센서 노드
  └─ SafeNest TCP protocol v1 / TCP 9000
       └─ Raspberry Pi server.py
            ├─ 센서 최신값 저장
            ├─ 상태 제어 API / HTTP 8080
            ├─ LCD 표시 화면 /display
            ├─ 노트북 제어 화면 /control
            └─ emergency 상태에서 GPIO18 부저 제어
```

## 폴더 구성

```text
Code_Share/
├─ README.md                         # 이 문서
├─ .gitignore                       # 비밀번호·실행 중 생성 파일 제외
├─ docs/
│  └─ COMMUNICATION_PROTOCOL.md     # TCP 패킷과 HTTP API 명세
├─ esp32_sensor_node/
│  ├─ esp32_sensor_node.ino         # 센서 읽기 및 Raspberry Pi 송신
│  └─ secrets.example.h             # Wi-Fi/Raspberry Pi 주소 설정 예시
└─ raspberry_pi_lcd/
   ├─ server.py                     # TCP 수신 + HTTP API + LCD/부저 서버
   ├─ start_lcd.sh                  # 서버와 Chromium 키오스크 시작
   ├─ stop_lcd.sh                   # 서버와 Chromium 안전 종료
   ├─ state.example.json            # 화면 상태 예시
   ├─ static/
   │  ├─ display.html               # Raspberry Pi LCD 전용 화면
   │  ├─ control.html               # 노트북 원격 제어 화면
   │  └─ common.css                 # 공통 화면 스타일
   └─ tests/
      ├─ test_sensor_receiver.py    # TCP 수신/센서 상태 테스트
      └─ test_buzzer.py             # emergency-부저 연동 테스트
```

## 1. Raspberry Pi에 복사하고 실행

현재 확인된 Raspberry Pi 예시 주소는 `192.168.1.44`, 계정은 `sandi`입니다. 네트워크가 바뀌면 실제 주소로 바꾸세요.

Windows PowerShell:

```powershell
scp -r .\display-test2\raspberry_pi_lcd sandi@192.168.1.44:~/
ssh sandi@192.168.1.44
```

Raspberry Pi:

```bash
cd ~/raspberry_pi_lcd
bash start_lcd.sh
```

실행 후 주소:

- Raspberry Pi LCD: `http://127.0.0.1:8080/display`
- 같은 네트워크의 노트북: `http://192.168.1.44:8080/control`
- 상태/API 확인: `http://192.168.1.44:8080/health`
- ESP32 수신 포트: `192.168.1.44:9000` TCP

필요 구성은 Python 3, `curl`, Chromium입니다. 실제 GPIO 부저를 쓸 때는 `gpiozero`도 필요합니다. 부저 없이 서버만 시험하려면 다음처럼 실행할 수 있습니다.

```bash
python3 server.py --disable-buzzer
```

## 2. ESP32 설정과 업로드

1. `esp32_sensor_node/secrets.example.h`를 같은 폴더의 `secrets.h`로 복사합니다.
2. `WIFI_SSID`, `WIFI_PASSWORD`, `RPI_HOST`를 실제 환경에 맞게 수정합니다.
3. Arduino IDE에서 `esp32_sensor_node.ino`를 열고 ESP32에 업로드합니다.
4. 시리얼 모니터를 115200 baud로 열어 연결 로그를 확인합니다.

```text
[network] connecting to 192.168.1.44:9000
[network] Raspberry Pi connected
[health] wifi=up rpi=192.168.1.44 ...
```

일반 ESP32는 2.4 GHz Wi-Fi를 사용합니다. Raspberry Pi와 ESP32가 서로 통신 가능한 같은 네트워크에 있어야 합니다. `secrets.h`에는 비밀번호가 들어가므로 공유하거나 Git에 올리지 마세요.

Arduino 라이브러리:

- Sensirion I2C SCD4x
- Seeed Arduino mmWave
- ESP32 보드 패키지에 포함된 WiFi, Wire, SPI

## 3. 정상 동작 확인

Raspberry Pi에서:

```bash
curl -s http://127.0.0.1:8080/health
ss -ltn | grep ':9000 '
tail -f logs/server.log
```

`health` 응답의 `sensors.status` 의미:

- `live`: ESP32 연결 상태이며 최근 센서 패킷을 받음
- `waiting`: 아직 센서 패킷을 받은 적이 없음
- `stale`: 이전 값은 있으나 연결이 끊겼거나 5초 이상 새 값이 없음
- `error`: TCP 수신 포트를 열지 못함

공유본 자체 테스트:

```bash
cd ~/raspberry_pi_lcd
python3 -m unittest discover -s tests -v
```

## 4. 종료

```bash
cd ~/raspberry_pi_lcd
bash stop_lcd.sh
```

이 스크립트는 Chromium과 Python 서버의 PID를 확인해 함께 종료합니다. 강제 종료 후에는 부저가 남지 않았는지도 확인하세요.

## 배선 메모

현재 코드 기준 주요 핀:

| 장치 | ESP32/Raspberry Pi 핀 |
|---|---|
| Raspberry Pi 피에조 부저 `+` | BCM GPIO18, 물리 12번 |
| Raspberry Pi 피에조 부저 `-` | GND, 물리 14번 |
| ESP32 I2C SDA / SCL | GPIO21 / GPIO22 |
| ESP32 PIR | GPIO13 |
| ESP32 MR60BHA2 RX / TX | GPIO16 / GPIO17 |
| ESP32 Thermal SCLK/MISO/MOSI | GPIO18 / GPIO19 / GPIO23 |
| ESP32 Thermal CS/READY/RESET | GPIO27 / GPIO26 / GPIO25 |

## 현재 구현 범위

- 호흡수, 심박수, CO₂, PIR 값은 LCD 상단 센서 영역에 표시됩니다.
- 열화상 프레임은 TCP로 수신하고 `thermal_frames_received` 횟수를 기록하지만, 현재 LCD에 열화상 영상을 그리지는 않습니다.
- 이 공유본의 Python 통신/부저 단위 테스트는 2026-08-03에 6개 모두 통과했습니다.
- 실제 센서, LCD, 부저의 물리 동작은 각 팀원의 배선과 네트워크 환경에서 별도로 확인해야 합니다.

## 공유본 기준

- GitHub `display-test` 브랜치의 `display-test2/` 폴더가 팀 공유 위치입니다.
- 기능 수정 시 `display-test2/`를 기준으로 작업하고, 실제 장비에 배포한 버전과 Git 커밋을 함께 기록하세요.
