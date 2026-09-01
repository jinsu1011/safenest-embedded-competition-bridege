# SafeNest CO₂ C-C1T — Acquisition Tooling Readiness and Pre-Collection Compliance Gate

- Document version: `01`
- Date: `2026-08-15`
- Phase: `C-C1T — Acquisition Tooling Readiness & Pre-Collection Compliance Gate`
- Agent: `Codex (CO2 C-C1T Acquisition Tooling Readiness Agent)`
- Standalone execution base: `0dc7325266a2e87b588398ba2182defd69a18fbf`
- Result: `C_C1T_BLOCKED`
- Validation disposition: `PASS_WITH_DEPLOYMENT_BLOCKER`

## 1. Scope and non-scope

This phase makes the reduced-feature C-C1R acquisition path executable in a
dry-run and inspectable before any physical collection. It does not collect
new physical data, run model inference, alter the C-B6 candidate, recompute a
scaler, change a threshold, change TFLite artifacts, start C-C2, or authorize
C-D.

The `C_C1T_BLOCKED` result in this report is the **formal
protocol-controlled acquisition gate**. It does not prohibit a separate
pre-deployment exploratory real-device collection. Exploratory sessions may
record real CO₂ range, qualitative VACANT/OCCUPIED behavior, transport and
failure modes, and capture workflow evidence under the explicit class
`PRE_DEPLOYMENT_EXPLORATORY_REAL_DEVICE_EVIDENCE`. Such evidence is retained
but is not automatically eligible for C-C2 formal performance evaluation when
fresh sensor-event identity is unverified.

The effective model-input/export contract remains 60 seconds. The capture
logger may poll the Pi more frequently to observe producer events; that logger
interval is not a claim about the native SCD40 cadence and does not authorize
stale reuse or synthetic fill.

## 2. Producer audit and decision

The current team implementation was inspected before tooling was written.

```text
ESP32 producer:
  getDataReadyStatus() → successful readMeasurement() → cached CO₂ state
  packet telemetry seq increments for telemetry packets
  co2Valid describes last-successful-read availability within the stale limit

Raspberry Pi:
  SensorStore derives fresh/age from packet receipt time
  record_telemetry previously dropped unknown producer event fields

Decision:
  TEAM_PRODUCER_CHANGE_REQUIRED
```

Packet `seq`, Pi receipt time, `fresh`, `age_seconds`, and `co2Valid` cannot
independently establish a new SCD40 measurement. They describe packet or
transport state and may accompany a cached CO₂ value.

The minimum correction is isolated to producer/transport observability:

```text
co2_measurement_event_id
co2_measurement_monotonic_ms
co2_measurement_event_valid
```

The ESP32 feature branch increments the event ID only after an accepted
SCD40 `readMeasurement()` result and preserves the producer-side monotonic
time. The Pi passes the fields through without manufacturing event identity
from packet sequence.

Team handoff state:

```text
team repository: https://github.com/jinsu1011/safenest-embedded-competition
team main base: 3d86bf2a7a4e527d7aba2dfabcb087201ffeb46e
team feature: feature/C-C1T-co2-fresh-event-observability
team feature commit: a7db03e6d7c65e91c52839e7b337c0886fa3431a
team PR: #19 OPEN
team main deployment: NO
```

PR #19 has not been merged or deployed by this task. Therefore the
canonical team path cannot yet be treated as acquisition-ready.

## 3. Standalone tooling and contract

The machine-readable contract is:

```text
datasets/co2/manifests/c_c1t_acquisition_tooling/capture_contract.json
```

The capture utility is:

```text
scripts/capture_co2_c_c1t_session.py
```

It accepts the Pi `/health` JSON path or a deterministic JSONL fixture. Each
raw row preserves the received payload before preprocessing and records:

- C-C1R protocol/version and the C-B6 candidate lock identity;
- generated session ID, operator/location/scenario identity;
- host UTC and monotonic capture chronology;
- CO₂ ppm and unit without filling missing values;
- producer event ID, producer monotonic event time, and event validity;
- transport freshness separately from sensor-measurement freshness;
- packet sequence, uptime, Pi receipt time, transport age/status;
- independent ground-truth reference and label when available;
- failure/missing/deviation classification.

The session bundle is finalized as:

```text
raw_measurements.jsonl
session_manifest.json
ground_truth_events.jsonl
failure_events.jsonl
deviation_events.jsonl
checksums.sha256
operator_notes.md
```

`CO2_slope` is not computed in the raw layer. Model inference and adaptive
collection decisions are not part of the utility.

## 4. Dry-run evidence

The deterministic fixture input is:

```text
datasets/co2/manifests/c_c1t_acquisition_tooling/fixtures/valid_session_input.jsonl
```

The committed example bundle is:

```text
datasets/co2/manifests/c_c1t_acquisition_tooling/fixtures/CO2C1R-20260815-CODEX-S001/
```

It contains three raw observations:

```text
raw observations: 3
verified fresh events: 2
cached retransmissions: 1
ground-truth events: 1 (VACANT)
failure events: 0
deviation events: 0
```

The same event ID across packet sequence changes is classified as
`CACHED_RETRANSMISSION`; it is not counted as another sensor event. The
missing-marker and transport-failure fixtures are retained separately and
are expected to block a bundle that contains no verified fresh event:

```text
datasets/co2/manifests/c_c1t_acquisition_tooling/fixtures/missing_event_marker.jsonl
datasets/co2/manifests/c_c1t_acquisition_tooling/fixtures/transport_failure.jsonl
```

Dry-run status is `PASS`, but this is software/contract validation only and
is not real-sensor validation.

## 5. Precollection result

The focused validator is:

```text
scripts/validate_co2_c_c1t_precollection.py
```

Its machine-readable result is:

```text
datasets/co2/manifests/c_c1t_acquisition_tooling/precollection_result.json
```

Observed result:

```text
tooling contract: PASS
dry-run bundle: PASS
team producer change: present on feature branch
team producer change deployed to team main: NO
operator handoff: HOLD_PENDING_TEAM_PRODUCER_PR_MERGE_AND_DEPLOYMENT
physical acquisition: HOLD
C-C2: NOT_STARTED
C-D: NOT_AUTHORIZED
```

The final phase status is therefore:

```text
C_C1T_BLOCKED
blocker: TEAM_PRODUCER_OBSERVABILITY_PR_NOT_MERGED_OR_DEPLOYED
```

Once the team PR is explicitly reviewed, merged, deployed, and the deployed
`/health` payload is rechecked, the standalone validator must be rerun. Only
that later pass may change the operator guide to `READY`; it still would not
by itself authorize C-C2.

## 6. Verification performed

The following checks passed on the standalone branch:

```text
python3 -m py_compile scripts/capture_co2_c_c1t_session.py \
  scripts/validate_co2_c_c1t_precollection.py \
  tests/test_co2_c_c1t_acquisition_tooling.py

python3 -m unittest tests/test_co2_c_c1t_acquisition_tooling.py -v
  4 tests passed

python3 scripts/validate_co2_c_c1t_precollection.py \
  --bundle-dir datasets/co2/manifests/c_c1t_acquisition_tooling/fixtures/CO2C1R-20260815-CODEX-S001
  tooling contract PASS; dry-run PASS; deployment blocker recorded

git diff --check
  passed
```

The previous C-C1R predecessor remains on standalone `main` with its frozen
protocol and `C_C1R_BLOCKED` handoff state. No C-B6 model/scaler/threshold or
C-C2 artifact was changed.

## 7. Required next action

Do not start physical acquisition and do not merge PR #19 automatically.
After explicit review and merge/deployment of PR #19, rerun the precollection
validator against the deployed producer/Pi path, record the resulting team
SHA and deployed payload evidence, and only then reassess the C-C1T status.
