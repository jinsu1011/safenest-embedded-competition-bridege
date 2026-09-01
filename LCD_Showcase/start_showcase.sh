#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8090}"
BACKEND="${BACKEND:-http://127.0.0.1:8000}"
AUDIO_DEVICE="${SAFENEST_TTS_AUDIO_DEVICE:-plughw:CARD=Audio,DEV=0}"
DISPLAY="${DISPLAY:-:0}"
XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
SERVER_PID_FILE="/tmp/safenest-lcd-showcase-server.pid"
SERVER_LOG="/tmp/safenest-lcd-showcase-server.log"
CHROMIUM_LOG="/tmp/safenest-lcd-showcase-chromium.log"
URL="http://127.0.0.1:${PORT}/display.html"

stop_previous_server() {
  if [[ ! -r "$SERVER_PID_FILE" ]]; then
    return
  fi
  local pid
  pid="$(<"$SERVER_PID_FILE")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    if tr '\0' ' ' <"/proc/${pid}/cmdline" | grep -Fq "$ROOT/server.py"; then
      kill "$pid"
      for _ in {1..20}; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.1
      done
    fi
  fi
}

stop_previous_server
nohup python3 "$ROOT/server.py" \
  --host "$HOST" \
  --port "$PORT" \
  --backend "$BACKEND" \
  --audio-device "$AUDIO_DEVICE" \
  >"$SERVER_LOG" 2>&1 &
SERVER_PID="$!"
printf '%s\n' "$SERVER_PID" >"$SERVER_PID_FILE"

for _ in {1..40}; do
  if curl --fail --silent --max-time 2 \
    "http://127.0.0.1:${PORT}/health" >/dev/null; then
    break
  fi
  sleep 0.25
done
curl --fail --silent --show-error --max-time 2 \
  "http://127.0.0.1:${PORT}/health" >/dev/null

# The previous field setup used a Restart=always transient unit for port 8000.
# Stop it first so it cannot cover the showcase window after being killed.
systemctl --user stop safenest-kiosk.service 2>/dev/null || true

# Stop only the SafeNest kiosk instances that point at the old or showcase LCD URL.
pkill -f 'chromium.*127\.0\.0\.1:8000/display' 2>/dev/null || true
pkill -f "chromium.*127\\.0\\.0\\.1:${PORT}/display\\.html" 2>/dev/null || true

PROFILE_DIR="$(mktemp -d /tmp/safenest-lcd-showcase-profile.XXXXXX)"
export DISPLAY XDG_RUNTIME_DIR
nohup chromium \
  --kiosk \
  --app="$URL" \
  --noerrdialogs \
  --no-first-run \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-pinch \
  --disable-features=TranslateUI,Translate \
  --overscroll-history-navigation=0 \
  --force-device-scale-factor=1 \
  --high-dpi-support=1 \
  --window-position=0,0 \
  --window-size=1024,600 \
  --ozone-platform=x11 \
  --user-data-dir="$PROFILE_DIR" \
  >"$CHROMIUM_LOG" 2>&1 &
CHROMIUM_PID="$!"

sleep 2
if ! kill -0 "$CHROMIUM_PID" 2>/dev/null; then
  echo "Chromium failed to stay running. See $CHROMIUM_LOG" >&2
  exit 1
fi

echo "LCD showcase ready"
echo "URL=$URL"
echo "SERVER_PID=$SERVER_PID"
echo "CHROMIUM_PID=$CHROMIUM_PID"
echo "SERVER_LOG=$SERVER_LOG"
echo "CHROMIUM_LOG=$CHROMIUM_LOG"
