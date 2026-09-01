#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SERVER_PID_FILE="/tmp/safenest-lcd-showcase-server.pid"

if [[ -r "$SERVER_PID_FILE" ]]; then
  pid="$(<"$SERVER_PID_FILE")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    if tr '\0' ' ' <"/proc/${pid}/cmdline" | grep -Fq "$ROOT/server.py"; then
      kill "$pid"
    fi
  fi
fi

pkill -f 'chromium.*127\.0\.0\.1:8090/display\.html' 2>/dev/null || true
echo "LCD showcase stopped"
