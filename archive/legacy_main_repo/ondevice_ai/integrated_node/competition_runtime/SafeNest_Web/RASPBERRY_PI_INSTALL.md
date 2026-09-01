# Raspberry Pi 웹 서버 설치

현재 `~/raspberry_pi_lcd`만 설치된 Raspberry Pi에 SafeNest 웹을 추가하는 방법입니다.

## 1. 노트북에서 ZIP 전송

Windows PowerShell에서 `RPI_IP`를 실제 Raspberry Pi 주소로 바꿔 실행합니다.

```powershell
scp "C:\Users\bma10\Desktop\임베디드\03_웹\SafeNest_Web_RaspberryPi.zip" sandi@RPI_IP:~/
```

## 2. Raspberry Pi에 Node.js 설치

VS Code SSH 터미널에서 실행합니다.

```bash
sudo apt update
sudo apt install -y nodejs npm unzip
node --version
npm --version
```

## 3. 웹 압축 해제 및 최초 설치

```bash
cd ~
mkdir -p SafeNest_Web
unzip -o SafeNest_Web_RaspberryPi.zip -d SafeNest_Web
cd ~/SafeNest_Web
npm install
cp -n .env.example .env
```

현재 Raspberry Pi IP를 `.env`에 자동 반영합니다.

```bash
RPI_IP=$(hostname -I | awk '{print $1}')
sed -i "s|^PUBLIC_BASE_URL=.*|PUBLIC_BASE_URL=http://${RPI_IP}:3000|" .env
```

`RPI_BRIDGE_URL`은 LCD 서버와 웹 서버를 같은 Raspberry Pi에서 실행하므로 다음 값이어야 합니다.

```text
RPI_BRIDGE_URL=http://127.0.0.1:8080
RPI_SPACE_ID=A01
```

## 4. 매번 실행하는 순서

첫 번째 SSH 터미널:

```bash
cd ~/raspberry_pi_lcd
bash start_lcd.sh
```

두 번째 SSH 터미널:

```bash
cd ~/SafeNest_Web
node server.js
```

ESP32 전원을 켠 후 확인합니다.

- 관리자: `http://RPI_IP:3000`
- 방문자: `http://RPI_IP:3000/guest/dashboard/A01`
- 기존 LCD 열화상: `http://RPI_IP:8080/thermal`

두 번째 터미널에 `Raspberry Pi bridge: http://127.0.0.1:8080 → A01`이 표시되면 웹 브리지가 활성화된 것입니다.
