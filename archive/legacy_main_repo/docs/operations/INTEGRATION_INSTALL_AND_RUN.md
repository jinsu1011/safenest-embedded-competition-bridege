# Raspberry Pi 설치·실행·종료

## 최초 1회 설치

지원 기준은 Raspberry Pi OS 64-bit와 Node.js 18 이상입니다. 저장소 루트에서 실행합니다.

```bash
cd ~/safenest-embedded-competition
bash integration/install_raspberry_pi.sh
```

스크립트는 `integration/pi_lcd`와 `integration/web`을 각각 `~/raspberry_pi_lcd`와 `~/SafeNest_Web`으로 복사합니다. 아래 실행 절차의 경로는 모두 복사된 홈 폴더 기준입니다.

스크립트는 `unzip`, `curl`, Chromium, `python3-gpiozero`, Node.js/npm 존재 여부를 점검하고 웹 의존성을 설치합니다. 배포판에 따라 Chromium 패키지 이름이 다르면 안내에 따라 직접 설치해야 할 수 있습니다.

수동 설치는 다음과 같습니다.

```bash
sudo apt update
sudo apt install -y python3 python3-gpiozero chromium-browser curl unzip nodejs npm
cd ~/SafeNest_Web
npm install
```

`chromium-browser`가 없으면 `chromium`을 설치합니다.

## 웹 환경 설정

```bash
cd ~/SafeNest_Web
cp .env.example .env
nano .env
```

최소한 `JWT_SECRET`, `SENSOR_API_KEY`, `ADMIN_PASSWORD`를 예측하기 어려운 값으로 변경합니다. LCD와 웹을 같은 Raspberry Pi에서 실행할 때 `RPI_BRIDGE_URL=http://127.0.0.1:8080`을 사용합니다.

## 정상 실행 순서

1. 노트북 Wi-Fi를 `YOUR_2_4_GHZ_WIFI_SSID`로 맞춥니다.
2. Raspberry Pi 전원을 켜고 30~60초 기다립니다.
3. VS Code로 Raspberry Pi SSH에 연결합니다.
4. 첫 번째 터미널을 열어 LCD·센서 수신 서버를 시작합니다.

```bash
cd ~/raspberry_pi_lcd
bash start_lcd.sh
```

5. 상태를 확인합니다.

```bash
curl -s http://127.0.0.1:8080/health
ss -ltn | grep -E ':8080|:9000'
```

6. 두 번째 터미널을 열어 통합 웹을 시작합니다.

```bash
cd ~/SafeNest_Web
RPI_BRIDGE_URL=http://127.0.0.1:8080 node server.js
```

7. ESP32 전원을 켭니다. ESP32가 부팅되면 9000번 포트로 Raspberry Pi에 연결합니다.
8. Raspberry Pi IP를 확인합니다.

```bash
hostname -I
```

9. 노트북 브라우저에서 엽니다.

```text
열화상: http://RPI_IP:8080/thermal
통합 웹: http://RPI_IP:3000
상태 API: http://RPI_IP:8080/health
```

## 일괄 실행 선택 사항

저장소를 `~/safenest-embedded-competition`에 두었다면 다음으로 두 서버를 함께 실행할 수 있습니다.

```bash
cd ~/safenest-embedded-competition
bash integration/start_all.sh
```

대회 현장에서는 로그를 바로 볼 수 있는 두 개의 VS Code 터미널 방식이 문제 파악에 더 편리합니다.

## 정상 종료 순서

1. `node server.js`가 실행된 터미널에서 `Ctrl+C`를 누릅니다.
2. LCD 서버를 종료합니다.

```bash
cd ~/raspberry_pi_lcd
bash stop_lcd.sh
```

3. ESP32 전원을 분리합니다.
4. Raspberry Pi를 안전 종료합니다.

```bash
sudo shutdown -h now
```

5. SSH 연결이 끊기고 Raspberry Pi 동작 LED가 멈춘 뒤 전원선을 분리합니다. 파일시스템 손상을 막기 위해 종료 명령 전에 전원선을 뽑지 않습니다.

