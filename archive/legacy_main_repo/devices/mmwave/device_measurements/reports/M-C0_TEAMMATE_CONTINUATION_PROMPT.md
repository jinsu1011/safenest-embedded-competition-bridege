# SafeNest M-C0 Physical Measurement Continuation Prompt

## Role

Continue the MR60BHA2 physical-device evidence task from the verified state below. Do not repeat completed offline audits or either completed capture. Do not treat Pilot data as formal evidence or training data.

## Repository state

```text
repository: https://github.com/jinsu1011/safenest-embedded-competition
branch: feature/mmwave-mc0-device-evidence
base PR: https://github.com/jinsu1011/safenest-embedded-competition/pull/18
original PR head: e3f9dc0150cb36b3bbbac06492a83285371c459e
```

The standalone ESP32 firmware was built and physically flashed from:

```text
devices/mmwave/firmware/src/main.cpp
devices/mmwave/firmware/include/mmwave_config.h
firmware: safenest-mr60-esp/1.2.0
config hash: b817e8bfd5e52b18275626f7b6a9bd60098ea4b108428a5aaf63600dbc987834
port: /dev/cu.usbserial-10
baud: 115200
```

Do not update the MR60 sensor firmware. A private 4MB pre-flash ESP32 backup exists locally and must never be committed or shared.

## Completed and QA-verified physical Pilot

```text
session: M-C0-PILOT-DESKWORK-001
label: PILOT_NOT_FORMAL_EVALUATION
condition: seated/front-facing desk work with small arm movements
duration: 180 seconds
records: 1,799
raw bytes: 1,819,539
raw SHA-256: 368e6a16e897b9231ff5fcdecd3edcc5b725a0a4dc6b20dee1e3162405bc2876
telemetry-row cadence: 9.993997Hz
fresh phase cadence: FRESH_PHASE_CADENCE_NOT_YET_FULLY_VERIFIED
median/p95 interval: 100/100ms
jitter: 0.299715ms
maximum gap: 103ms
JSON/UART/checksum failures: 0/0/0
sequence gaps/duplicates/backwards: 0/0/0
timestamp duplicates/backwards: 0/0
strict contract validator: PASS
```

Physical presence, distance, respiration, heart and total/breath/heart phase fields were populated. `sensor_firmware_version` remained unavailable.

Desk-work result:

```text
VALID: 838/1,799 (46.58%)
DEGRADED: 961/1,799 (53.42%)
BREATH_PHASE_LOW_AMPLITUDE: 961
distance range: 40.18-120.54cm
filtered respiration populated: 838/1,799 (46.58%)
```

## Captured but not yet analyzed

```text
session: M-C0-PILOT-STATIONARY-001
label: PILOT_NOT_FORMAL_EVALUATION
condition: seated/front-facing, user reported remaining nearly stationary
duration: 180 seconds
records: 1,799
raw bytes: 1,837,444
raw SHA-256: e2b832fd3a72f18b4c3a370738c10e58c0269283dac218ae2d7d4dad48036f6f
capture-console telemetry-row cadence: approximately 9.99Hz
capture-console maximum gap: 102ms
capture-console JSON/UART/checksum failures: 0/0/0
QA/manifest/derived interpretation: intentionally pending user approval
```

Both curated Pilot raw files are intentionally Git-tracked as narrow `TRACKED_EXCEPTION` evidence despite the general `*.jsonl` ignore rule. This does not authorize arbitrary raw dumps. Their immutable identities are recorded by path, size, record count and SHA-256; do not fabricate, edit or silently promote them into formal evidence.

## Interpretation boundary

- The stream and timing integrity passed for this Pilot.
- The measured rate is telemetry-row cadence, not exact fresh `0x0A13` cadence. Producer validity uses `kPhaseMaxAgeMs = 500ms`, but that threshold does not reconstruct exact arrivals; repeated values alone are not stale proof.
- The session demonstrates movement sensitivity; it does not establish accuracy.
- Do not add this Pilot to model training data without a later, explicit dataset-design and labeling decision.
- Do not retrain, change thresholds, modify `BPF_ZSCORE`, alter window semantics, or modify the locked TFLite artifact.
- No independent reference was collected; respiration/heart accuracy remains unverified.
- Phase fields are populated, but units, scale and reset semantics remain unverified.
- Raspberry Pi E2E, deployment readiness and clinical apnea remain unverified.

## Next task — no new sensor measurement

Do not repeat the stationary capture. After explicit approval:

1. Run strict contract and physical QA on the immutable stationary raw.
2. Create its actual session manifest and environment metadata without inventing unknown values.
3. Compare desk-work and stationary captures only in a derived report.
4. Test whether the actual physical phase stream can form locked 30-second/300-sample inputs.
5. Apply the already-locked M-B11 BPF/Z-score/int8 path without changing thresholds, scaling, window semantics or the TFLite artifact.
6. Update the verification matrix and handoff report with PASS, PASS_WITH_LIMITATIONS or exclusion evidence.

A synchronized independent respiration reference is required only for an accuracy claim. Raspberry Pi validation remains a later integration stage. Do not begin formal evaluation, model retraining or M-D from these Pilot captures.
