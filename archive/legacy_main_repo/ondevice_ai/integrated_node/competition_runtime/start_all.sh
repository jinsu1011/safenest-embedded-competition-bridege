#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/raspberry_pi_lcd"
bash start_lcd.sh

cd "$HOME/SafeNest_Web"
export RPI_BRIDGE_URL="${RPI_BRIDGE_URL:-http://127.0.0.1:8080}"
exec node server.js
