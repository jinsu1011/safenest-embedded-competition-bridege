#!/usr/bin/env bash
# Controlled Thermal model comparison launcher.
#
# Does not replace ./run_safenest.sh. Ordinary startup remains the Team baseline.
#
#   ./run_safenest_thermal_test.sh baseline
#   ./run_safenest_thermal_test.sh a
#   ./run_safenest_thermal_test.sh b
#   ./run_safenest_thermal_test.sh a --api-port 8080
#   ./run_safenest_thermal_test.sh a --dry-run
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CHOICE="${1:-}"

case "${CHOICE}" in
  baseline)
    SELECTOR="thermal_public_sdt_fp32_active"
    ;;
  a)
    SELECTOR="thermal_tv2_candidate_a_a0_fp32_v1"
    ;;
  b)
    SELECTOR="thermal_tv2_candidate_b_seed42_fp32_test_v1"
    ;;
  *)
    echo "Usage: $0 {baseline|a|b} [SafeNest args...]" >&2
    echo "  baseline  current Team Thermal model (thermal_public_sdt_fp32_active)" >&2
    echo "  a         Thermal V2 Candidate A A0 (controlled test)" >&2
    echo "  b         Thermal V2 Candidate B seed-42 (controlled comparison only)" >&2
    exit 2
    ;;
esac

shift

DRY_RUN=0
FORWARD_ARGS=()
for arg in "$@"; do
  if [[ "${arg}" == "--dry-run" ]]; then
    DRY_RUN=1
  else
    FORWARD_ARGS+=("${arg}")
  fi
done

export SAFENEST_THERMAL_TEST_MODE=1
export SAFENEST_THERMAL_MODEL_SELECTOR="${SELECTOR}"

echo "[SafeNest Thermal Test]"
echo "mode: controlled-test"
echo "choice: ${CHOICE}"
echo "selector: ${SELECTOR}"
echo "SAFENEST_THERMAL_TEST_MODE=1"
echo "SAFENEST_THERMAL_MODEL_SELECTOR=${SELECTOR}"
echo "ordinary ./run_safenest.sh is unchanged; this launcher is opt-in only"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "dry-run: not starting SafeNest"
  exit 0
fi

exec "${REPOSITORY_ROOT}/run_safenest.sh" "${FORWARD_ARGS[@]}"
