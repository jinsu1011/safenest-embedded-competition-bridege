# SafeNest Embedded Competition

> Repository mapping: the ESP32 sketch is stored in
> `devices/mmwave/firmware/competition_sensor_node/`, while the Raspberry Pi
> LCD receiver, web dashboard, and installation scripts are stored in
> `ondevice_ai/integrated_node/competition_runtime/`.

ESP32에서 호흡수, 심박수, CO₂, PIR 움직임, 80×62 열화상 데이터를 수집하고 Raspberry Pi의 LCD 및 통합 웹 화면에 표시하는 프로젝트입니다.

## 전체 구성

```text
센서 → ESP32 → Wi-Fi/TCP 9000 → Raspberry Pi Python 서버
                                      ├─ LCD 화면 /display
                                      ├─ 열화상 화면 /thermal
                                      └─ REST API /api/state, /api/thermal
                                                   ↓
                                     Node.js 통합 웹 서버 :3000
                                                   ↓
                                     노트북·휴대폰 웹 브라우저
```

## 폴더 구조

```text
SafeNest_GitHub_Package/
├─ esp32_sensor_node/       ESP32 Arduino 소스와 네트워크 설정 예제
├─ raspberry_pi_lcd/        ESP32 수신, LCD, 열화상, GPIO 부저 서버
├─ SafeNest_Web/            관리자·방문자 통합 웹과 Raspberry Pi 브리지
├─ docs/                    설치, 실행, 백엔드 및 통신 규격 문서
├─ install_raspberry_pi.sh  Raspberry Pi 최초 설치 보조 스크립트
└─ start_all.sh             LCD 서버와 웹 서버 일괄 시작 스크립트
```

## 처음 사용하는 순서

1. [docs/01_ESP32_ARDUINO_SETUP.md](docs/01_ESP32_ARDUINO_SETUP.md)를 따라 Arduino IDE와 ESP32 보드, 라이브러리를 설치합니다.
2. `esp32_sensor_node/secrets.example.h`를 `secrets.h`로 복사하고 Wi-Fi와 Raspberry Pi IP를 입력한 뒤 ESP32에 업로드합니다.
3. [docs/02_VSCODE_RASPBERRY_PI_SSH.md](docs/02_VSCODE_RASPBERRY_PI_SSH.md)를 따라 VS Code로 Raspberry Pi에 접속합니다.
4. 이 프로젝트의 `raspberry_pi_lcd`, `SafeNest_Web` 폴더를 Raspberry Pi 홈 폴더에 복사합니다.
5. [docs/03_INSTALL_AND_RUN.md](docs/03_INSTALL_AND_RUN.md)를 따라 의존성을 설치하고 실행합니다.

## 대회 당일 실행 요약

1. 노트북 Wi-Fi를 `YOUR_2_4_GHZ_WIFI_SSID`에 연결합니다.
2. Raspberry Pi 전원을 켜고 VS Code에서 SSH로 접속합니다.
3. 첫 번째 터미널에서 실행합니다.

```bash
cd ~/raspberry_pi_lcd
bash start_lcd.sh
```

4. 두 번째 터미널에서 실행합니다.

```bash
cd ~/SafeNest_Web
RPI_BRIDGE_URL=http://127.0.0.1:8080 node server.js
```

5. ESP32 전원을 켭니다.
6. `hostname -I`로 확인한 Raspberry Pi IP가 `192.168.0.50`이라면 다음 주소를 엽니다.

- 열화상: `http://192.168.0.50:8080/thermal`
- 통합 웹: `http://192.168.0.50:3000`
- 상태 점검: `http://192.168.0.50:8080/health`

## 종료 요약

1. `node server.js` 터미널에서 `Ctrl+C`
2. `cd ~/raspberry_pi_lcd && bash stop_lcd.sh`
3. ESP32 전원 분리
4. `sudo shutdown -h now`
5. SSH 연결이 끊어지고 Raspberry Pi 동작 LED가 멈춘 다음 전원선 분리

## 중요 보안 안내

실제 Wi-Fi 비밀번호가 담긴 `secrets.h`와 실제 웹 비밀키가 담긴 `.env`는 GitHub에 올리지 마세요. 이 패키지는 예제 파일만 포함하며 `.gitignore`가 실제 설정 파일을 제외합니다.

## 세부 문서

- [ESP32와 Arduino IDE 설치](docs/01_ESP32_ARDUINO_SETUP.md)
- [VS Code Raspberry Pi SSH 접속](docs/02_VSCODE_RASPBERRY_PI_SSH.md)
- [설치·실행·종료](docs/03_INSTALL_AND_RUN.md)
- [웹·LCD 백엔드 동작](docs/04_BACKEND_ARCHITECTURE.md)
- [통신 프로토콜](docs/COMMUNICATION_PROTOCOL.md)
- [문제 해결](docs/05_TROUBLESHOOTING.md)
