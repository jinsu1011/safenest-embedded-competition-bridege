#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HEALTH_URL="http://127.0.0.1:8080/health"
STATE_URL="http://127.0.0.1:8080/api/state"
ALARM_ACTIVE=0

safe_alarm_off() {
  if [[ "${ALARM_ACTIVE}" == "1" ]]; then
    if ! curl -fsS -X POST "${STATE_URL}" \
      -H 'Content-Type: application/json' \
      -d '{"state":"normal-empty"}' >/dev/null; then
      bash "${ROOT}/stop_lcd.sh"
    fi
    ALARM_ACTIVE=0
  fi
}

trap safe_alarm_off EXIT INT TERM

cd "${ROOT}"
python3 -m unittest -v test_buzzer.py
python3 -c 'import gpiozero; print("gpiozero import: OK")'

bash stop_lcd.sh
sleep 1
bash start_lcd.sh

HEALTH_JSON="$(curl -fsS "${HEALTH_URL}")"
python3 -c '
import json, sys
health = json.loads(sys.argv[1])
buzzer = health["buzzer"]
assert buzzer["enabled"] is True, buzzer
assert buzzer["available"] is True, buzzer
assert buzzer["pin_bcm"] == 18, buzzer
assert buzzer["frequency_hz"] == 880.0, buzzer
assert buzzer["sounding"] is False, buzzer
print("부저 초기 상태: OFF, GPIO18, 880 Hz")
' "${HEALTH_JSON}"

curl -fsS -X POST "${STATE_URL}" \
  -H 'Content-Type: application/json' \
  -d '{"state":"emergency"}' >/dev/null
ALARM_ACTIVE=1
sleep 2

HEALTH_JSON="$(curl -fsS "${HEALTH_URL}")"
python3 -c '
import json, sys
buzzer = json.loads(sys.argv[1])["buzzer"]
assert buzzer["sounding"] is True, buzzer
print("긴급 상태: 부저 ON 확인")
' "${HEALTH_JSON}"

safe_alarm_off
trap - EXIT INT TERM

HEALTH_JSON="$(curl -fsS "${HEALTH_URL}")"
python3 -c '
import json, sys
buzzer = json.loads(sys.argv[1])["buzzer"]
assert buzzer["sounding"] is False, buzzer
print("긴급 해제: 부저 OFF 확인")
' "${HEALTH_JSON}"

echo "SafeNest LCD 부저 배포 및 자동 검증 완료"
