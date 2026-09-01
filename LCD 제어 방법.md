# LCD 제어 방법

이 문서는 라즈베리파이 LCD에서 **연출용 화면**과 **통합용 화면**을 켜고 끄는 방법을 정리한다.

두 화면을 동시에 실행하지 말고, 화면을 바꿀 때는 현재 화면을 먼저 종료한 뒤 다른 화면을 실행한다.

## 1. 연출용 LCD 화면

연출용 화면은 `LCD_Showcase`의 전용 서버(`:8090`)와 Chromium 키오스크를 함께 실행한다.

### 켜기

```bash
cd /home/sandi/safenest-team-main/LCD_Showcase
./start_showcase.sh
```

### 끄기

```bash
cd /home/sandi/safenest-team-main/LCD_Showcase
./stop_showcase.sh
```

### 실행 확인

```bash
curl -fsS http://127.0.0.1:8090/health
pgrep -af 'chromium.*8090/display.html'
```

## 2. LCD 통합용 화면

통합용 화면은 SafeNest 통합 백엔드의 `http://127.0.0.1:8000/display`를 Chromium 키오스크로 표시한다.

### 켜기

먼저 연출용 화면을 종료한다.

```bash
cd /home/sandi/safenest-team-main/LCD_Showcase
./stop_showcase.sh
```

통합 백엔드가 실행 중인지 확인한다.

```bash
pgrep -af run_backend.py || true
curl -fsS http://127.0.0.1:8000/health
curl -fsS -o /dev/null http://127.0.0.1:8000/display
```

백엔드가 실행 중이 아니면 다음과 같이 시작한다.

```bash
cd /home/sandi/safenest-team-main
mkdir -p logs
nohup bash ./run_safenest.sh > logs/runtime.log 2>&1 &
echo $! > .runtime.pid
```

백엔드가 준비되면 통합용 LCD 화면을 연다.

```bash
export DISPLAY=:0
export WAYLAND_DISPLAY=wayland-0
export XDG_RUNTIME_DIR=/run/user/1000
[ -f "$HOME/.Xauthority" ] && export XAUTHORITY="$HOME/.Xauthority"

pkill -f "chromium.*8000/display" 2>/dev/null || true

nohup chromium --kiosk --noerrdialogs --disable-infobars \
  --check-for-update-interval=31536000 \
  --user-data-dir=/tmp/safenest-chromium-display \
  --ozone-platform=x11 \
  http://127.0.0.1:8000/display \
  >/tmp/chromium-display.log 2>&1 &
```

### 화면만 끄기

통합 백엔드는 유지하고 LCD의 Chromium 화면만 종료한다.

```bash
pkill -f "chromium.*8000/display" 2>/dev/null || true
```

### 화면과 통합 백엔드 모두 끄기

```bash
cd /home/sandi/safenest-team-main

pkill -f "chromium.*8000/display" 2>/dev/null || true
kill "$(cat .runtime.pid)" 2>/dev/null || true
pkill -f "backend/run_backend.py" 2>/dev/null || true
```

### 실행 확인

```bash
pgrep -af "chromium.*8000/display" | head -3
curl -fsS http://127.0.0.1:8000/health
```

## 3. 화면 전환 요약

### 통합용 화면에서 연출용 화면으로 전환

```bash
pkill -f "chromium.*8000/display" 2>/dev/null || true
cd /home/sandi/safenest-team-main/LCD_Showcase
./start_showcase.sh
```

### 연출용 화면에서 통합용 화면으로 전환

```bash
cd /home/sandi/safenest-team-main/LCD_Showcase
./stop_showcase.sh
```

그다음 위의 **2. LCD 통합용 화면 → 켜기** 절차를 실행한다.

## 4. 문제 확인

```bash
# 연출용 화면 로그
tail -n 100 /tmp/safenest-lcd-showcase-server.log
tail -n 100 /tmp/safenest-lcd-showcase-chromium.log

# 통합용 화면 로그
tail -n 100 /tmp/chromium-display.log

# 통합 백엔드 로그
tail -n 100 /home/sandi/safenest-team-main/logs/runtime.log
```

SSH에서 실행하더라도 Chromium은 Pi의 그래픽 세션인 `DISPLAY=:0`으로 열어야 물리 LCD에 표시된다.
