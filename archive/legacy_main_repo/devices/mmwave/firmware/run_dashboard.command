#!/bin/zsh

SCRIPT_DIR="${0:A:h}"
PYTHON="$SCRIPT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  PYTHON="python3"
fi

cd "$SCRIPT_DIR" || exit 1
exec "$PYTHON" mmwave_dashboard.py \
  --port "${1:-/dev/cu.usbserial-10}" \
  --baud 115200
