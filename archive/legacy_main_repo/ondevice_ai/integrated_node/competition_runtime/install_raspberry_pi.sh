#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sudo apt update
sudo apt install -y python3 python3-gpiozero curl unzip nodejs npm

if apt-cache show chromium >/dev/null 2>&1; then
  sudo apt install -y chromium
elif apt-cache show chromium-browser >/dev/null 2>&1; then
  sudo apt install -y chromium-browser
else
  echo "Chromium 패키지를 찾지 못했습니다. Raspberry Pi OS에 맞는 Chromium을 설치하세요."
fi

cp -a "$PROJECT_DIR/raspberry_pi_lcd" "$HOME/"
cp -a "$PROJECT_DIR/SafeNest_Web" "$HOME/"

cd "$HOME/SafeNest_Web"
npm install

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo ".env를 생성했습니다. 비밀키와 관리자 비밀번호를 변경하세요."
fi

chmod +x "$HOME/raspberry_pi_lcd/start_lcd.sh" \
  "$HOME/raspberry_pi_lcd/stop_lcd.sh" \
  "$PROJECT_DIR/start_all.sh"

echo "설치 완료: ~/raspberry_pi_lcd와 ~/SafeNest_Web에 배치했습니다."
echo "docs/03_INSTALL_AND_RUN.md를 따라 실행하세요."
