#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="${SAFENEST_PYTHON_BIN:-/usr/bin/python3}"
PORT="${SAFENEST_LCD_PORT:-8080}"
SENSOR_PORT="${SAFENEST_SENSOR_PORT:-9000}"
URL="http://127.0.0.1:${PORT}/display"
LOG_DIR="${ROOT}/logs"
mkdir -p "${LOG_DIR}"

if [[ -f "${ROOT}/.server.pid" ]] && kill -0 "$(cat "${ROOT}/.server.pid")" 2>/dev/null; then
  echo "SafeNest 서버가 이미 실행 중입니다."
else
  if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "Python 실행 파일을 찾을 수 없습니다: ${PYTHON_BIN}" >&2
    exit 1
  fi
  nohup "${PYTHON_BIN}" -u "${ROOT}/server.py" --host 0.0.0.0 --port "${PORT}" \
    --sensor-host 0.0.0.0 --sensor-port "${SENSOR_PORT}" \
    >"${LOG_DIR}/server.log" 2>&1 &
  echo $! > "${ROOT}/.server.pid"
fi

for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.2
done

if ! curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
  echo "서버가 시작되지 않았습니다. ${LOG_DIR}/server.log를 확인하세요." >&2
  exit 1
fi

if command -v chromium >/dev/null 2>&1; then
  BROWSER="$(command -v chromium)"
elif command -v chromium-browser >/dev/null 2>&1; then
  BROWSER="$(command -v chromium-browser)"
else
  echo "Chromium을 찾을 수 없습니다. 서버만 실행 중입니다." >&2
  echo "노트북 제어 주소: http://$(hostname -I | awk '{print $1}'):${PORT}/control"
  exit 2
fi

if [[ -f "${ROOT}/.browser.pid" ]] && kill -0 "$(cat "${ROOT}/.browser.pid")" 2>/dev/null; then
  kill "$(cat "${ROOT}/.browser.pid")" 2>/dev/null || true
  sleep 1
fi

export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export LIBGL_ALWAYS_SOFTWARE=1
BROWSER_PLATFORM_ARGS=()
if [[ -S "${XDG_RUNTIME_DIR}/wayland-0" ]]; then
  export WAYLAND_DISPLAY="${WAYLAND_DISPLAY:-wayland-0}"
  export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"
  BROWSER_PLATFORM_ARGS+=(--ozone-platform=wayland)
  echo "Chromium 화면 세션: Wayland (${WAYLAND_DISPLAY})"
else
  export DISPLAY="${DISPLAY:-:0}"
  BROWSER_PLATFORM_ARGS+=(--ozone-platform=x11)
  echo "Chromium 화면 세션: X11 (${DISPLAY})"
fi
nohup "${BROWSER}" \
  "${BROWSER_PLATFORM_ARGS[@]}" \
  --disable-gpu \
  --disable-gpu-compositing \
  --disable-gpu-rasterization \
  --disable-accelerated-2d-canvas \
  --user-data-dir="${ROOT}/.chromium-kiosk" \
  --kiosk \
  --start-fullscreen \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  "${URL}" >"${LOG_DIR}/chromium.log" 2>&1 &
BROWSER_PID=$!
echo "${BROWSER_PID}" > "${ROOT}/.browser.pid"

sleep 5
if ! kill -0 "${BROWSER_PID}" 2>/dev/null; then
  echo "Chromium이 시작 직후 종료되었습니다. ${LOG_DIR}/chromium.log를 확인하세요." >&2
  tail -n 30 "${LOG_DIR}/chromium.log" >&2 || true
  exit 3
fi
echo "Chromium 렌더링: CPU 소프트웨어 모드"

PI_IP="$(hostname -I | awk '{print $1}')"
echo "SafeNest LCD를 시작했습니다."
echo "노트북 제어 주소: http://${PI_IP}:${PORT}/control"
echo "ESP32 센서 입력: ${PI_IP}:${SENSOR_PORT} (TCP)"
echo "종료: bash ${ROOT}/stop_lcd.sh"
