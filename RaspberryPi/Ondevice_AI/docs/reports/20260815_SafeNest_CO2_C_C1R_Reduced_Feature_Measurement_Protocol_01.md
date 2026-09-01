# SafeNest CO₂ C-C1R Reduced-Feature Measurement Protocol

- Document Version: `01`
- Author: `Codex` (CO₂ C-C1R Protocol and Operator Handoff Agent)
- Execution Date: `2026-08-15`
- Phase: `C-C1R — Reduced-Feature Measurement Protocol Revision and Operator Handoff`
- Status: `C_C1R_BLOCKED`

**Protocol ID:** `CO2_C_C1R_REDUCED_MEASUREMENT_PROTOCOL_001`
**Protocol version:** `1.0.0`
**Standalone execution base:** `81358008f44ff7b92e1c0997d862777c97497440`
**Protocol state:** `PROTOCOL_FROZEN`
**Operator guide state:** `HOLD_PENDING_ACQUISITION_TOOLING_CORRECTION`
**Physical acquisition:** `HOLD`
**C-C2:** `NOT_STARTED`

Authoritative manifest:

[datasets/co2/manifests/c_c1r_reduced_measurement_protocol/protocol.json](../../datasets/co2/manifests/c_c1r_reduced_measurement_protocol/protocol.json)

Korean operator-facing draft:

[docs/prompts/20260815_SafeNest_CO2_C_C1R_SCD40_Measurement_Operator_Guide_KO_01.md](../prompts/20260815_SafeNest_CO2_C_C1R_SCD40_Measurement_Operator_Guide_KO_01.md)

The draft is not authorized for distribution yet because the current team capture path cannot demonstrate the required fresh-measurement event contract.

## 1. Executive status

C-C1R froze the successor physical acquisition contract for the locked C-B6 reduced-feature candidate without collecting new physical data. The contract covers model inputs, freshness, chronology, nominal cadence, H150 eligibility, independent occupancy truth, raw preservation, and the later C-C2 compliance gate.

The current team tooling cannot authorize physical acquisition. `devices/co2/firmware/capture_scd40.py` records Pi `/health` observations, transport/cache status, host clocks, and raw API responses, but it does not expose a verified fresh SCD40 measurement event sequence or timestamp. It also lacks the frozen protocol/session/candidate manifest and independent time-stamped ground-truth bundle required by this contract.

```text
PROTOCOL_FROZEN: YES
OPERATOR_GUIDE_HANDOFF: HOLD
PHYSICAL_ACQUISITION: HOLD
OPERATOR_HANDOFF_BLOCKER: OPERATOR_HANDOFF_BLOCKED_BY_ACQUISITION_TOOLING
C-C2: NOT_STARTED
C-D: NOT_AUTHORIZED
```

This is a tooling-readiness block, not a C-B6 model failure. No team firmware, telemetry, runtime, model, scaler, threshold, or TFLite artifact was modified in C-C1R.

## 2. Predecessor lineage

The reduced protocol is a successor contract. The historical four-feature C-C1 artifact remains unchanged and is not silently converted.

| Evidence | Identity and role |
|---|---|
| C-C0 | `B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE`; legacy SCD40 evidence audit |
| Historical C-C1 | `CO2_C_C1_MEASUREMENT_PROTOCOL_001` version `1.0.0`; preserved four-feature B5 contract |
| PR #78 | merged; `266151d12a1e4b144d5a6f2bae28dda72f939cc5` |
| Final input decision | `ADOPT_REDUCED_FEATURE_DIRECTION`; `datasets/co2/manifests/c_c1_model_input_decision/model_input_decision_result.json` |
| PR #80 / C-B6 | merged `7c0b2d606b048e07cd2941a2df14d9981faeb735`; `C_B6_PASS_WITH_LIMITATIONS` |
| C-C1R | successor `CO2_C_C1R_REDUCED_MEASUREMENT_PROTOCOL_001`; no new physical data |

```text
Historical: CO2 + Temperature + Humidity + CO2_slope
Successor:  CO2 + Pi-derived CO2_slope
```

## 3. Locked C-B6 candidate binding

```text
CANDIDATE_ID: C_B6_REDUCED_CO2_SLOPE_CANDIDATE_001
FEATURE_ORDER: CO2, CO2_slope
C_B6_STATUS: C_B6_PASS_WITH_LIMITATIONS
THRESHOLD: 0.43
THRESHOLD_SOURCE: TRAIN_INTERNAL_ONLY
B5_THRESHOLD_0_58_INHERITED: NO
LOCKED_TEST_PREDICTIVE_ACCESS: NO
PHYSICAL_ACQUISITION_STARTED: NO
C-C2_STARTED: NO
```

| Artifact | Repository-relative path | SHA-256 or fingerprint |
|---|---|---|
| Candidate lock | `datasets/co2/manifests/c_b6_reduced_feature_candidate/candidate_lock.json` | `5f7772ff26ca10ca95aa5216b45f3eebd96c2429b98a7ee66963ec4ea73c6fd2` |
| Lock content | candidate lock field | `7dd6a4c78731465d258e60d2f5e301df2f7b30dbdcc28addb99a0e72a4ec1a90` |
| TRAIN-only scaler | `datasets/co2/manifests/c_b6_reduced_feature_candidate/scaler_metadata.json` | `a92123ad37e9b284929ba0fe53179126345d54d487ec4b3a73c910d00490a462` |
| Threshold contract | `models/co2/candidates/c_b6/threshold_contract.json` | `db7076b1b9870c67471f049d96c99db7de2d767790e50065010ed0c752d07db0` |
| Float TFLite | `models/co2/candidates/c_b6/float_reference.tflite` | `fc1d4150a818473758f1f2a7c3a5f3afe604cf7c59171524f21dac3a22c3a87c` |
| Full integer INT8 | `models/co2/candidates/c_b6/full_integer_int8.tflite` | `c5969b367f5b5e28c4d27f1bdd6220f7d02da92e99604e3f85c9f1291e98dd3b` |

C-C1R does not refit, retune, reconvert, or replace these artifacts.

## 4. Locked model-input contract

The physical operator supplies raw CO₂ evidence. `CO2_slope` is derived downstream on the Raspberry Pi or equivalent post-processing layer from verified chronology.

```text
SCD40 / ESP
  → fresh CO2 event and freshness/chronology evidence
  → transport preserving event identity and failure state
  → Pi / downstream post-processing
  → ENDPOINT_H150 CO2_slope
  → C-B6 scaler, threshold, and inference
```

| Field | Role | Requirement |
|---|---|---|
| `CO2` | raw sensor feature | Required model input; ppm; tied to a verified fresh event |
| `CO2_slope` | derived feature | Required model input; Pi/post-processing only; `ENDPOINT_H150` |
| `Temperature` | optional diagnostic telemetry | Not required for reduced-model eligibility |
| `Humidity` | optional diagnostic telemetry | Not required for reduced-model eligibility |

T/RH may be retained if a future adapter exposes them, but their availability is not a reduced-candidate model gate. This is a model/system-contract decision, not a claim that T/RH have no physical or diagnostic value and not a transport-size claim.

## 5. Freshness and chronology contract

```text
TRANSPORT_FRESHNESS != SENSOR_MEASUREMENT_FRESHNESS
```

A new Pi packet, logger row, recent `age_seconds`, or numeric cached CO₂ value does not prove a new SCD40 conversion.

A valid fresh CO₂ event requires data-ready or equivalent readiness evidence, successful fresh-read status, a `fresh_read_sequence` or equivalent marker that advances only for a successful read, chronology associated with that event, and the raw value/unit/status/failure state. An SCD40-native timestamp is not required if the hardware/API does not provide one. Host chronology may order events only when explicitly associated with a verified fresh event; packet receipt time alone is not sensor-event chronology.

## 6. Effective cadence and H150 behavior

The SafeNest normal model-input/export cadence is nominally 60 seconds. This is not a claim that the SCD40 native measurement interval is 60 seconds.

If a verified fresh CO₂ event exists at a normal opportunity, preserve its real chronology. If it does not, preserve a missing/failure state. Stale reuse, forward-fill, interpolation, and synthetic sensor events are forbidden.

The slope contract remains:

```text
profile: CO2_SLOPE_FEATURE_PROFILE_001
method: ENDPOINT_H150
history: 150 seconds
chronology: PAST_ONLY
minimum samples: 2
gap reset: >90 seconds
cross-session/block history: FORBIDDEN
```

At nominal events `60 → 180` seconds, one missed event produces an approximately 120-second gap. Because `120 > 90`, the H150 history resets and `CO2_slope` is temporarily unavailable. Do not invent an intermediate sample or relax the gap rule. Warm-up and gap-unavailable records remain in raw evidence.

## 7. Required raw evidence

The immutable acquisition layer should be line-oriented JSONL, or an explicitly lossless equivalent, with a separate session manifest. At minimum, future compliant capture must preserve:

```text
protocol_id
protocol_version
session_id
target_candidate_id
device identity or explicit unknown
logger UTC timestamp
logger monotonic chronology
raw CO2 value and ppm unit
sensor measurement freshness/status
transport freshness/status
missing/error state
raw received payload or lossless equivalent
software/configuration identity
```

When available, also preserve `measurement_event_id`, `fresh_read_sequence`, `sensor_event_monotonic_ms`, `data_ready`, telemetry sequence, Pi receipt timestamps, and device uptime. A missing field must remain null/unknown with a declared reason; it must not be replaced with a normal value.

Each session or authorized batch should contain:

```text
raw_measurements.jsonl
session_manifest.json
ground_truth_events.jsonl
failure_events.jsonl
deviation_events.jsonl
checksums.sha256
operator_notes.md
```

Close files, record row/event counts and byte sizes, hash the handoff files, write the checksum manifest, and only then create derived artifacts. Do not manually correct old rows, delete failures, replace raw CO₂, reorder chronology, or overwrite a finalized file.

## 8. Independent ground truth

C-C2 requires independent `VACANT` / `OCCUPIED` ground truth. The ground-truth source must not be a model input or model output.

The operator must record a separate time-stamped event log with:

```text
ground_truth_event_id
session_id
label: VACANT or OCCUPIED
source: controlled empty / controlled person-present / recorded entry / recorded exit
start and end or transition time
ground_truth_status
operator_id
```

Do not derive labels from CO₂, CO₂ slope, PIR, filenames such as `breath`, threshold crossings, expected model behavior, or any displayed prediction. Ambiguous transition intervals remain explicitly ambiguous or excluded according to the later C-C2 intake rule; they are not silently relabeled.

## 9. Scenario and session design

Allowed session types are `VACANT_STABLE`, `OCCUPIED_STABLE`, `VACANT_TO_OCCUPIED`, and `OCCUPIED_TO_VACANT`.

After warm-up, each stable segment should retain at least 150 seconds of same-session verified fresh chronology before it is considered H150-ready. A transition session should retain at least 150 seconds before and after the independently marked transition when the scenario requires both segments. Multiple sessions and independent transitions are preferred; the total number is supplied by a separately authorized acquisition schedule. No session count here claims statistical power.

Start a new session after a device/logger restart, location or configuration change, or a chronology interruption requiring a new H150 block. Keep incomplete and failed sessions in the returned bundle.

## 10. Operator responsibilities and prohibited adaptive use

The operator is responsible for safe ordinary room conditions, declared session identity, the independently controlled occupancy scenario, preserving raw and failure evidence, and returning the frozen bundle. The operator does not calculate `CO2_slope` and does not need to understand the model internals.

During accumulation, do not inspect predictions to change labels, scenarios, durations, stopping rules, sample balance, threshold, scaler, feature order, or H150. Do not retrain or refit the candidate. If the capture tool cannot produce a required field, stop and report a tooling deviation; do not improvise a replacement.

## 11. C-B6 INT8 saturation limitation disposition

C-B6 observed low-frequency `CO2_slope` INT8 input saturation while its Float/INT8 equivalence gate passed. C-C1R records this as:

```text
KNOWN_NONBLOCKING_LIMITATION_FOR_DEVICE_DOMAIN_OBSERVATION
```

This does not mean the limitation was fixed or explained away. It does not block protocol definition by itself, but C-C2 must report real-device slope quantizer saturation, input clipping/range exceedance, and any observable prediction effect before making device-domain claims. No C-B6 model, scaler, threshold, quantization range, or TFLite file was changed here.

## 12. Current team tooling readiness

The read-only team reference was checked at:

```text
repository: https://github.com/jinsu1011/safenest-embedded-competition.git
main: 3d86bf2a7a4e527d7aba2dfabcb087201ffeb46e
capture: devices/co2/firmware/capture_scd40.py
```

| Contract area | Current status | Evidence |
|---|---|---|
| Fresh CO₂ event | `PARTIAL` | CO₂ and `fresh`/valid status are captured, but `fresh` is not a verified new SCD40 event marker |
| Chronology | `PARTIAL` | host timestamps, monotonic clock, and packet sequence exist; sensor-event chronology is absent |
| Error/missing preservation | `PARTIAL` | CSV status/error and raw API response are retained, but the event-level fresh-read contract is absent |
| Independent ground truth | `PARTIAL` | scenario text exists; no independent time-stamped GT event bundle is produced |
| Raw preservation/checksum | `PARTIAL` | raw API response is embedded in CSV; no C-C1R session bundle and final SHA-256 manifest |
| Protocol/session/candidate identity | `NO` | current capture has no frozen protocol/version, session, or C-B6 candidate binding |

The current path is therefore not sufficient for this protocol without a declared acquisition adapter/tooling correction. This C-C1R change does not modify the team repository or pretend that an operator can manually supply event evidence the current path cannot capture.

Minimum correction before handoff:

1. Expose a verified fresh CO₂ event marker and associated chronology, separately from transport receipt freshness.
2. Preserve protocol ID/version, session ID, target candidate identity, device/software/configuration provenance, raw payload, and failure/missing states.
3. Produce an independent time-stamped ground-truth event log and a final session checksum bundle.
4. Run the C-C1R precollection compliance validator against the deployed capture path before any physical session.

## 13. C-C2 future intake boundary

C-C2 is not implemented or started here. When separately authorized, it must first audit protocol compliance, candidate-lock identity, session provenance, raw immutability, freshness semantics, chronology, nominal cadence, missing/stale handling, independent ground truth, H150 eligibility, and the saturation observations listed above. Only compliant evidence may proceed to frozen-candidate metrics.

External accumulation remains separate from model development. No acquisition result authorizes C-D. C-D requires a later explicit decision gate.

## 14. Final state

```text
C_C1R_PROTOCOL_FROZEN: YES
OPERATOR_GUIDE_HANDOFF: HOLD
PHYSICAL_ACQUISITION: HOLD
C-C2: NOT_STARTED
C-D: NOT_AUTHORIZED
FINAL_STATUS: C_C1R_BLOCKED
BLOCK_REASON: OPERATOR_HANDOFF_BLOCKED_BY_ACQUISITION_TOOLING
```
