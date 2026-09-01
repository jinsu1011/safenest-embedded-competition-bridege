# SafeNest CO₂ C-C1 SCD40 Measurement Protocol

- Document Version: `02`
- Author: `Codex` (CO₂ Measurement Protocol Agent)
- Execution Date: `2026-08-15`
- Phase: `C-C1 — Historical Four-Feature Measurement Protocol and Operator Handoff`
- Status: `HISTORICAL_PROTOCOL_WITH_CURRENT_HOLD`

**Protocol ID:** CO2_C_C1_MEASUREMENT_PROTOCOL_001
**Protocol version:** 1.0.0
**Protocol status:** FROZEN_FOR_EXTERNAL_ACQUISITION_WITH_PRECOLLECTION_COMPLIANCE_GATE
**C-C1 frozen:** YES
**Protocol creation base:** standalone origin/main 0625603f319b18cd6ad86b33dcca5ce2147ac2af
**Team acquisition reference:** team origin/main 5947334d3d0f6c6f7d6100c7ea6af219e5b4c5d5
**Physical collection in this phase:** NO

The machine-readable contract is the authority for field-level types and validation rules:

[datasets/co2/manifests/c_c1_measurement_protocol/protocol.json](../../datasets/co2/manifests/c_c1_measurement_protocol/protocol.json)

The independent operator handoff is:

[docs/prompts/20260814_SafeNest_CO2_C_C1_SCD40_Measurement_Operator_Prompt_01.md](../prompts/20260814_SafeNest_CO2_C_C1_SCD40_Measurement_Operator_Prompt_01.md)

## 0.1 Final pre-acquisition input decision (2026-08-15)

The subsequent pre-acquisition model-input decision audit is recorded at:

- [decision result](../../datasets/co2/manifests/c_c1_model_input_decision/model_input_decision_result.json)
- [decision audit report](20260815_SafeNest_CO2_Pre_Acquisition_Model_Input_Decision_Audit_01.md)

Its final decision is:

~~~text
FINAL_INPUT_DECISION: ADOPT_REDUCED_FEATURE_DIRECTION
FUTURE_MODEL_INPUT_DIRECTION: CO2 + CO2_slope
PHYSICAL_ACQUISITION_STATUS: HOLD_PENDING_REDUCED_FEATURE_CANDIDATE_LOCK
OPERATOR_GUIDE_HANDOFF: HOLD
CURRENT_B5: HISTORICAL_FROZEN_FOUR_FEATURE_CONTRACT
B5_MODIFIED: NO
C-C2_STARTED: NO
~~~

The four-feature protocol, protocol ID, version, required fields, and frozen B5 identity remain unchanged as historical C-C1 evidence. This status does not remove Temperature or Humidity from B5 and does not authorize collection with this guide. A revised protocol and operator prompt may be created only after the separately authorized `C-B6` CO₂ + `CO2_slope` candidate has been trained, validated, and locked.

## 1. Purpose and stop boundary

C-C1 converts verified C-C0 evidence gaps into a frozen physical-measurement contract. It defines what a future measurement owner must preserve so that a later, explicitly authorized C-C2 intake can audit protocol compliance before evaluating the frozen B5 candidate.

C-C1 is not:

- a new measurement session;
- a B5 inference run;
- an occupancy metric calculation;
- a model, scaler, feature, or threshold update;
- a C-C2 intake;
- a C-D authorization.

The C-C1 stop condition is:

~~~text
protocol frozen
+ machine-readable contract frozen
+ operator prompt independently executable
+ focused validator passes
= historical C-C1 artifact complete
~~~

The original C-C1 contract described a future external handoff, but the later final input decision places that handoff on `HOLD`. No measurement owner may collect data from this four-feature guide until a reduced-feature candidate is separately trained, validated, locked, and given a revised protocol. Once a revised protocol is authorized, the AI development loop must not inspect model performance and adapt the collection while sessions accumulate.

## 2. Entry evidence and predecessor gate

The C-C0 predecessor was verified live before this protocol was designed:

| Evidence | Current reference |
|---|---|
| C-C0 English report | [docs/reports/20260814_SafeNest_CO2_C_C0_Legacy_SCD40_Evidence_Audit_01.md](20260814_SafeNest_CO2_C_C0_Legacy_SCD40_Evidence_Audit_01.md) |
| C-C0 Korean report | [docs/reports/20260814_SafeNest_CO2_C_C0_팀원_SCD40_실측데이터_평가_01.md](20260814_SafeNest_CO2_C_C0_팀원_SCD40_실측데이터_평가_01.md) |
| Standalone entry revision | 0625603f319b18cd6ad86b33dcca5ce2147ac2af |
| C-C0 status | MERGED_ON_CURRENT_ORIGIN_MAIN |
| C-C0 result | B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE |

The reports are the primary predecessor evidence. Their key findings were rechecked against the live team acquisition code and current B5 lock before this protocol was frozen.

## 3. C-C0 finding to C-C1 control

Every required protocol field has a reason. The contract does not add metadata merely because it might be interesting.

| C-C0 finding | C-C1 control |
|---|---|
| Temperature and Humidity were read locally but dropped before telemetry and CSV capture. | Preserve CO2, Temperature, and Relative Humidity from one identified SCD40 read event, with per-field validity and the raw source payload. |
| Pi fresh and ESP CO2-valid flags describe transport or last-successful-read age, not a new SCD40 conversion. | Record data-ready, read status, fresh-read sequence, ESP event monotonic time, packet sequence, Pi receipt time, and logger clocks as separate layers. |
| Legacy host polling was approximately 1 second while SCD4x periodic measurement was described as approximately 5 seconds. | Never equate logger polls or telemetry packets with fresh SCD40 events. The adapter must expose a successful-read event marker. |
| The downstream SafeNest input/export schedule was not frozen by C-C0. | Freeze a nominal 60-second effective model-input and normal CO2 export cadence as a downstream contract, separately from native SCD40 measurement timing. |
| ENDPOINT_H150 could not be reconstructed from verified fresh SCD40 chronology. | Preserve same-session fresh-event chronology, actual elapsed time, session boundaries, stale/disconnect gaps, and restart behavior for later H150 reconstruction. |
| Independent synchronized VACANT/OCCUPIED truth was absent. | Record a separate controlled ground-truth log with source, label, event time, status, and operator code. CO2, PIR, slope, and B5 outputs are prohibited as GT. |
| Historical summary/report SHA-256 values did not match current raw bytes. | Close raw files first, hash frozen bytes, write a manifest with path/size/row count/session/protocol/checksum, and detect later mutation. |
| Sensor identity and configuration provenance were weak. | Separate SCD40 identity, ESP identity, Pi identity, firmware/library revisions, measurement mode, compensation/configuration state, and power-cycle history. |
| Invalid/stale/disconnected rows existed and were correctly preserved. | Preserve every raw event and failure/deviation record. Never drop, interpolate, forward-fill, zero-fill, or silently relabel. |

## 4. Live acquisition path and implementation boundary

The current team path was inspected at team origin/main 5947334d3d0f6c6f7d6100c7ea6af219e5b4c5d5:

~~~text
SCD40 on ESP32
  → ESP32 readMeasurement
  → ESP32 telemetry packet
  → TCP to Raspberry Pi
  → Pi latest-value SensorStore
  → Pi /health
  → capture_scd40.py
  → legacy CSV
~~~

Observed implementation facts:

- SCD40 periodic mode is used and the first measurement is described as taking approximately 5 seconds.
- The ESP32 checks data readiness on a 250 ms polling schedule.
- ESP32 telemetry is published approximately every 1000 ms.
- The ESP32 keeps a CO₂ last-successful-read freshness state with a 15-second stale limit.
- The Pi SensorStore uses a 5-second transport stale threshold.
- The ESP32 read call receives CO₂, Temperature, and Humidity, but the current TelemetrySnapshot and telemetry JSON publish CO₂ only.
- The current capture script polls Pi /health and stores transport/cache fields, not a direct SCD40 conversion event.

The current legacy path is therefore not C-C1 compliant without a protocol adapter or an explicitly equivalent implementation. C-C1 does not modify or deploy that adapter. The future measurement owner must declare its firmware, library, and adapter revisions and pass the precollection compliance gate before any session starts.

The observed native/read and transport timings above are not the downstream SafeNest cadence contract. The 60-second cadence below is a system-level model-input and normal-export decision; it must not be rewritten as a 60-second native SCD40 measurement interval.

## 5. Frozen B5 contract

The live machine-readable B5 lock was read from:

- [datasets/co2/manifests/c_b5_robustness_final_lock/final_candidate_lock.json](../../datasets/co2/manifests/c_b5_robustness_final_lock/final_candidate_lock.json)
- [models/co2/candidates/c_b5/final_candidate_metadata.json](../../models/co2/candidates/c_b5/final_candidate_metadata.json)
- [datasets/co2/manifests/c_b5_robustness_final_lock/robustness_protocol.json](../../datasets/co2/manifests/c_b5_robustness_final_lock/robustness_protocol.json)

The contract is unchanged by C-C1:

| Item | Frozen value |
|---|---|
| Candidate | CO2_B5_FINAL_OFFLINE_UCI_CANDIDATE_001 |
| Candidate status | FINAL_OFFLINE_UCI_CANDIDATE_LOCKED |
| Device-domain validation | NOT_YET_COMPLETE |
| Feature order | CO2, Temperature, Humidity, CO2_slope |
| Slope | ENDPOINT_H150 |
| Slope method | ENDPOINT_DIFFERENCE |
| History | 150.0 seconds, actual elapsed time, PAST_ONLY |
| Maximum internal gap | 90.0 seconds |
| Threshold | 0.58 |
| Architecture | LINEAR_LOGISTIC |
| Input | full-integer INT8; scale 0.03529411926865578; zero point 0 |
| Output | INT8; scale 0.00390625; zero point -128 |
| Model | models/co2/candidates/c_b4/full_integer_int8.tflite |
| Model SHA-256 | bb2ed28533bca75d4fa3d06348e017c506df47d7c34b29574b77f70b6b386816 |
| Scaler | datasets/co2/manifests/c_b2_imbalance_calibration/preprocessing_scaler_evidence.json |
| Scaler fingerprint | d0cf83558fb0de9dcdc97f0d94781a5a475a6f68e8d818121aee929030e5dc89 |
| Final lock SHA-256 | a020d462e0d359e0c9faa9bb680387119f095cb102243d7e6c223d76a801b627 |
| Safety semantic | ROOM_OCCUPANCY_ONLY_NO_SAFETY_SEMANTIC |

C-C1 may preserve the evidence needed to evaluate this contract later. It may not change the feature order, slope, scaler, model bytes, quantization, threshold, or class semantics.

## 6. Required feature contract

The physical measurement must preserve three raw source features from the same fresh SCD40 event:

| Frozen feature | Required raw evidence | Unit | Missing policy |
|---|---|---|---|
| CO2 | SCD40 read output | ppm | Null with read/failure status; never substitute |
| Temperature | Same SCD40 readMeasurement event | degC | Null with read/failure status; never substitute |
| Humidity | Same SCD40 readMeasurement event | %RH | Null with read/failure status; never substitute |
| CO2_slope | C-C2 derived feature from verified chronology | ppm/min | Null during warm-up/gap/invalid history; no interpolation |

The three raw values must share one measurement_event_id. A cached CO₂ value cannot be paired with Temperature or Humidity from another event. The machine-readable manifest contains the complete field registry, including source, timing, allowed missing state, reason, and validation rule.

## 7. Measurement-event contract

A raw event qualifies as a verified fresh SCD40 measurement only when all of the following are true:

1. The SCD40 data-ready status is true.
2. The SCD40 readMeasurement call returns success.
3. CO₂, Temperature, and Relative Humidity are finite values returned by that same call.
4. The adapter increments fresh_read_sequence exactly once.
5. The adapter captures sensor_event_monotonic_ms at the successful read boundary.
6. The event receives one measurement_event_id shared by the three source features.
7. The raw source payload and per-feature validity are preserved.

The permitted evidence mechanisms are implementation-level mechanisms already supported by the observed acquisition path or its declared adapter:

- SCD40 data-ready status;
- successful readMeasurement result;
- an ESP fresh-read sequence increment;
- an ESP monotonic timestamp captured at read completion.

The protocol does not claim that the SCD40 itself exposes a native timestamp. sensor_event_monotonic_ms is an ESP/controller event marker, not a fabricated sensor-native timestamp.

The following are not fresh-event evidence by themselves:

- a logger poll;
- a new ESP telemetry sequence;
- a Pi revision number;
- Pi transport_fresh;
- a last-successful-read validity flag;
- a numeric cached CO₂ field.

If the deployed adapter cannot demonstrate the event marker and same-event T/RH coherence in a precollection fixture or replay check, the operator must stop before physical collection.

## 8. Freshness and timestamp contract

The protocol keeps three event layers separate:

~~~text
LOGGER_POLL_EVENT
TRANSPORT_PACKET_EVENT
FRESH_SCD40_MEASUREMENT_EVENT
~~~

Required clocks:

| Clock/field | Meaning | Use |
|---|---|---|
| sensor_event_monotonic_ms | ESP monotonic time at successful fresh read | Sensor chronology and H150 elapsed time within session |
| logger_monotonic_ns | Logger host monotonic time | Host-local ordering and event gaps |
| logger_timestamp_utc | Logger wall clock in UTC | Provenance and same-logger GT alignment |
| pi_receive_timestamp_utc | Pi packet receipt time | Transport chronology, not sensor time |
| pi_receive_monotonic_ns | Pi monotonic receipt time | Host-local transport age/order |
| ground_truth_event_timestamp_utc | Same logger clock as GT marker | Entry/exit and label segment timing |

Rules:

- Use monotonic clocks for elapsed chronology.
- Use UTC timestamps for provenance and same-logger GT alignment.
- Do not claim subsecond cross-host synchronization without evidence.
- A sensor or logger restart starts a new session.
- A clock discontinuity is preserved as a deviation.
- A packet timestamp does not replace the fresh sensor-event marker.

### Effective SafeNest model-input cadence

The downstream SafeNest contract is nominally 60 seconds for both the effective model-input record and, where the same event is transmitted as the normal CO₂ telemetry record, the normal CO₂ export record:

~~~text
SCD40_NATIVE_MEASUREMENT_CADENCE: configured/observed separately
SAFENEST_EFFECTIVE_MODEL_INPUT_CADENCE: 60 seconds nominal
SAFENEST_NORMAL_CO2_EXPORT_CADENCE: 60 seconds nominal
~~~

This is downstream SafeNest sampling/export semantics. It does not claim that the SCD40 native measurement cycle is 60 seconds, and it does not replace the required `configured_measurement_interval_ms` or verified fresh-event chronology. Native SCD40 timing, ESP read behavior, transport packet timing, and SafeNest effective model-input/export timing are separate layers.

Every normal 60-second model-input/export record must contain CO₂, Temperature, and Relative Humidity from one verified fresh SCD40 event. The three values must share one `measurement_event_id`; cached values from different events cannot be assembled merely to satisfy the schedule. A valid record is not created when only a logger poll, transport packet, or cached value is available.

The 60-second cadence is nominal. If no verified fresh SCD40 event is available at a scheduled point, preserve the missing/failure state and the actual timestamps. Do not silently reuse a prior value, forward-fill, edit timestamps, or rewrite chronology to create perfect 60-second spacing. Failure, disconnect, and deviation evidence must be preserved when observed and must not be hidden until the next normal valid export.

The cadence is compatible with the frozen H150 contract only under normal uninterrupted sampling. For example:

~~~text
0 s      valid
60 s     valid
120 s    missing/invalid
180 s    next valid
~~~

The valid-event gap is then approximately 120 seconds. Because `120 > 90`, the frozen H150 history must reset. `CO2_slope` remains unavailable with a gap-restart status until sufficient causal, past-only history is rebuilt. The `>90`-second reset rule is not relaxed to accommodate the 60-second cadence.

The responsibility boundary remains unchanged:

- ESP32: SCD40 acquisition, data-ready/read status, fresh-read/event metadata, and transport.
- Raspberry Pi/downstream SafeNest processing: effective 60-second model-input/export handling, history management, ENDPOINT_H150 calculation, scaling, and later B5 inference when separately authorized.

H150 buffers, `StandardScaler`, B5 inference, threshold logic, and occupancy-model logic do not move to the ESP32 as part of this cadence correction.

## 9. ENDPOINT_H150 reconstructability

C-C1 retains the frozen H150 definition; it does not redefine it.

The later C-C2 reconstruction must use:

~~~text
method: ENDPOINT_DIFFERENCE
formula: (CO2_now - CO2_history_start) / (actual_elapsed_seconds / 60.0)
history: at least 150.0 seconds
causality: PAST_ONLY
maximum internal gap: 90.0 seconds
interpolation: forbidden
future samples: forbidden
centered window: forbidden
~~~

History is eligible only within one session and one continuous verified fresh-event chronology. Reset the history on:

- a new session;
- device restart or power cycle;
- a fresh-event gap greater than 90 seconds;
- stale/disconnect intervals that prevent verified fresh events;
- a non-monotonic sensor-event clock;
- invalid or nonfinite source values.

During warm-up or after a gap, preserve a null slope and an explicit status such as FEATURE_UNAVAILABLE_WARMUP or FEATURE_UNAVAILABLE_GAP_RESTART. Do not create a synthetic slope.

The 150-second requirement is justified by the frozen B5 H150 contract. It is not a claim that the current legacy CSVs already satisfy the physical freshness semantics.

## 10. Session and scenario contract

Every session has an immutable ID in this form:

~~~text
CO2C1-YYYYMMDD-OPCODE-SNNN
~~~

The scenario ID is one of:

- VACANT_STABLE
- OCCUPIED_STABLE
- VACANT_TO_OCCUPIED
- OCCUPIED_TO_VACANT

Start a new session after:

- device reboot or power cycle;
- location change;
- measurement configuration change;
- occupancy scenario reset;
- operator or logger restart;
- an interruption greater than 90 seconds without verified fresh chronology.

Do not carry temporal history across sessions.

Per-session completion rules:

| Scenario | Completion condition |
|---|---|
| VACANT_STABLE | Controlled VACANT truth, warm-up complete, then at least 150 seconds of verified fresh chronology before ending |
| OCCUPIED_STABLE | Controlled OCCUPIED truth, warm-up complete, then at least 150 seconds of verified fresh chronology before ending |
| VACANT_TO_OCCUPIED | At least 150 seconds of verified VACANT chronology, a logger-time entry marker, then at least 150 seconds of verified OCCUPIED chronology |
| OCCUPIED_TO_VACANT | At least 150 seconds of verified OCCUPIED chronology, a logger-time exit marker, then at least 150 seconds of verified VACANT chronology |

These are per-session history requirements derived from H150. C-C1 does not freeze an aggregate session count or adaptive stopping rule. The measurement owner must receive a separately authorized safe acquisition schedule and may not select its count or stopping point from B5 output.

Incomplete sessions remain in the handoff bundle and receive a compliance classification.

## 11. Device identity and configuration

Record separately:

- SCD40 model;
- unique SCD40 serial if accessible;
- explicit UNIQUE_SENSOR_IDENTITY_NOT_AVAILABLE if the serial cannot be queried;
- ESP device ID;
- Pi/logger ID;
- firmware revision or immutable build ID;
- SCD40 library revision;
- measurement mode;
- configured measurement interval;
- SafeNest effective model-input cadence: 60 seconds nominal, recorded separately from native SCD40 configuration;
- SafeNest normal CO₂ export cadence: 60 seconds nominal when the same event is exported;
- ASC enabled/disabled/unknown;
- temperature offset;
- altitude compensation;
- ambient pressure compensation;
- FRC history if known;
- power-cycle state;
- warm-up state.

Unknown or inaccessible configuration is recorded explicitly with a reason. It is never replaced by a default. A configuration change closes the current session and starts a new session.

The SCD40 serial, ESP identity, and Pi identity must never be collapsed into one device_id field.

## 12. Independent occupancy ground truth

Ground truth is an independent operator-controlled event log. It is not a sensor-derived label.

Allowed labels:

~~~text
VACANT
OCCUPIED
~~~

Allowed independent sources:

- CONTROLLED_EMPTY_ROOM;
- CONTROLLED_PERSON_PRESENT;
- RECORDED_ENTRY;
- RECORDED_EXIT.

For every ground-truth segment or transition, record:

- ground_truth_event_id;
- label;
- source;
- start timestamp;
- end or transition timestamp;
- status;
- operator code;
- linked session_id.

Only CONFIRMED_OPERATOR_CONTROLLED segments with explicit timing can enter later formal C-C2 occupancy metrics. UNCERTAIN, CONFLICTED, and MISSING segments remain preserved but block the corresponding metric claim.

Never infer ground truth from CO₂, CO₂ slope, PIR, B5 prediction, or B5 probability.

## 13. Environment and ventilation context

Always record location_id and scenario_id. Record the following when they materially change interpretation:

- door state;
- window state;
- ventilation state;
- HVAC state;
- another CO₂-relevant environmental change.

If a relevant value cannot be known, record UNKNOWN_WITH_REASON. The protocol deliberately does not require a maximal environmental checklist unrelated to CO₂ interpretation.

## 14. Failure and missing-data contract

The raw bundle must preserve statuses including:

- SENSOR_READ_FAILED;
- SENSOR_DATA_NOT_READY;
- SENSOR_INVALID;
- TRANSPORT_DISCONNECTED;
- TRANSPORT_STALE;
- LOGGER_ERROR;
- DEVICE_RESTART;
- SESSION_INTERRUPTED;
- GROUND_TRUTH_MISSING;
- CONFIGURATION_UNKNOWN;
- PROTOCOL_DEVIATION.

The operator and adapter must not:

- drop rows;
- forward-fill values;
- interpolate raw evidence;
- replace failure with zero;
- edit timestamps;
- relabel after looking at B5;
- discard failed sessions.

An invalid or stale event can remain in the raw bundle. It simply cannot be used as a verified fresh feature event.

At a nominal 60-second normal model-input/export point, absence of a verified fresh event produces a preserved missing/failure condition, not a valid stale record. Failure and disconnect evidence is recorded when observed; it does not wait for a later normal 60-second event.

## 15. Raw bundle and checksum finalization

The canonical future handoff uses an immutable JSONL raw event file and companion manifests:

~~~text
<session-or-acquisition-bundle>/
  raw_measurements.jsonl
  session_manifest.json
  ground_truth_events.jsonl
  failure_events.jsonl
  deviation_events.jsonl
  checksums.sha256
  operator_notes.md
~~~

Finalization order:

1. Stop the session capture.
2. Close every raw and registry file.
3. Record byte size and event/line count.
4. Compute SHA-256 for each handoff file except the checksum file itself.
5. Write checksums.sha256 with path, byte size, row/event count where applicable, session ID, protocol ID/version, and checksum.
6. Mark the bundle frozen.
7. Generate summaries only from the frozen raw bundle.

If a later hash differs, classify RAW_EVIDENCE_MUTATION_DETECTED. Derived summaries never replace raw evidence.

The historical C-C0 checksum mismatch is the reason this finalization sequence is mandatory.

## 16. Protocol compliance and C-C2 intake

Future C-C2 must classify each session or bundle as:

- PROTOCOL_COMPLIANT;
- PROTOCOL_COMPLIANT_WITH_LIMITATIONS;
- PROTOCOL_NONCOMPLIANT;
- PROTOCOL_STATUS_UNKNOWN.

Blocking violations include:

- missing any required raw B5 source feature;
- CO₂, Temperature, and Humidity not linked to one measurement_event_id;
- missing fresh-measurement chronology;
- missing session identity or unknown session boundary;
- missing or mismatched raw checksum;
- silent timestamp, label, or raw-value edit;
- unrecorded configuration change;
- missing independent ground truth for a claimed formal metric segment;
- B5 identity drift;
- adaptive collection based on B5 output.

Noncompliant data is preserved and classified; it is not silently discarded.

C-C2 may start only when:

1. the final reduced-feature candidate and revised C-C1 protocol are locked;
2. protocol-controlled measurements have actually accumulated under that revised protocol;
3. the intake passes the pre-metric compliance gate;
4. the user explicitly authorizes C-C2.

C-C2 must audit compliance before evaluating the finally locked candidate. C-C1 does not authorize formal metrics.

## 17. External accumulation boundary (currently HOLD)

The following boundary is retained as the historical C-C1 contract. Under the final input decision above, no measurement owner may begin external accumulation with this four-feature guide:

~~~text
collect according to frozen protocol
→ preserve every session and deviation
→ seal raw bundle and checksums
→ wait for explicit C-C2 authorization
~~~

The owner must not adapt session selection, duration, conditions, class balance, threshold, feature definition, or stopping rules based on B5 output. Any unavoidable deviation is logged with a reason, timestamp, affected session, and compliance consequence.

## 18. Operator handoff (currently HOLD)

The standalone operational prompt is:

[docs/prompts/20260814_SafeNest_CO2_C_C1_SCD40_Measurement_Operator_Prompt_01.md](../prompts/20260814_SafeNest_CO2_C_C1_SCD40_Measurement_Operator_Prompt_01.md)

It is retained for provenance and must not currently be handed to a physical measurement owner for collection. It includes:

- precollection adapter compliance gate;
- hardware and revision fields;
- session ID and scenario procedure;
- same-event CO₂/T/RH requirements;
- fresh-event and clock requirements;
- independent GT actions;
- environment and failure logging;
- raw finalization and checksum steps;
- prohibited cleanup and prohibited B5-driven adaptation;
- stop conditions and returned artifacts.

If the precollection adapter cannot expose the required fields, the prompt instructs the operator to stop and return a blocked preflight record. C-C1 does not implement or deploy acquisition code.

## 19. C-C1 exit gate

C-C1 is classified complete only when all of the following agree:

~~~text
C_C1_PROTOCOL_FROZEN: YES
human-readable technical protocol: PRESENT
machine-readable protocol manifest: PRESENT
independent operator prompt: PRESENT
effective model-input cadence: 60 seconds nominal
normal CO2 export cadence: 60 seconds nominal
native SCD40 cadence treated separately: YES
focused validator: PASS
B5 contract unchanged: YES
new device data consumed: NO
B5 inference executed: NO
formal metrics calculated: NO
C-C2 started: NO
C-D started: NO
~~~

The validator result is recorded at:

[datasets/co2/manifests/c_c1_measurement_protocol/validation_result.json](../../datasets/co2/manifests/c_c1_measurement_protocol/validation_result.json)

## 20. Unresolved items that block physical collection until resolved

The following are deliberately explicit precollection gates, not hidden assumptions:

1. The deployed protocol adapter revision must be identified and must demonstrate same-event CO₂/T/RH plus fresh_read_sequence in a fixture or replay check.
2. SCD40 serial accessibility must be queried; if unavailable, record UNIQUE_SENSOR_IDENTITY_NOT_AVAILABLE.
3. The deployed adapter/receiver must record and honor the downstream 60-second nominal model-input/export cadence separately from native SCD40 timing, without stale reuse, and must preserve the one-missed-sample H150 reset consequence.
4. A separately authorized aggregate session schedule must exist; C-C1 does not choose counts adaptively.

These items do not authorize collection before resolution. They make the handoff safe: unresolved implementation facts produce a stop, not a fabricated value.

## 21. Scientific boundary

C-C1 freezes the measurement process, not the model. The locked B5 candidate remains untouched. No physical measurement, new raw payload, B5 inference, formal occupancy metric, model retraining, scaler refit, threshold change, C-C2 intake, or C-D work is authorized by this document.

The later decision audit adds a stricter current boundary: physical acquisition and operator distribution remain `HOLD_PENDING_REDUCED_FEATURE_CANDIDATE_LOCK` until a new reduced-feature candidate and a revised protocol are separately authorized and locked.
