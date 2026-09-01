#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

stop_pid_file() {
  local file="$1"
  local label="$2"
  if [[ -f "${file}" ]]; then
    local pid
    pid="$(cat "${file}")"
    if kill -0 "${pid}" 2>/dev/null; then
      kill "${pid}" 2>/dev/null || true
      echo "${label} 종료 요청 완료 (PID ${pid})"
    fi
    rm -f "${file}"
  fi
}

stop_pid_file "${ROOT}/.browser.pid" "LCD 브라우저"
stop_pid_file "${ROOT}/.server.pid" "SafeNest 서버"
echo "SafeNest LCD를 종료했습니다."
