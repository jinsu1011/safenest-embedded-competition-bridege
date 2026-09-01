# SafeNest CO₂ C-C1 SCD40 Measurement Operator Prompt

- Document Version: `02`
- Author: `Codex` (CO₂ Measurement Protocol Agent)
- Execution Date: `2026-08-15`
- Phase: `C-C1 — Historical Four-Feature Measurement Protocol and Operator Handoff`
- Status: `HISTORICAL_PROMPT_WITH_CURRENT_HOLD`

**Protocol ID:** CO2_C_C1_MEASUREMENT_PROTOCOL_001
**Protocol version:** 1.0.0
**Protocol status:** FROZEN_FOR_EXTERNAL_ACQUISITION_WITH_PRECOLLECTION_COMPLIANCE_GATE
**Audience:** physical SCD40 measurement owner
**Execution mode:** use this document without relying on the AI development chat

## Final pre-acquisition decision status (2026-08-15)

~~~text
FINAL_INPUT_DECISION: ADOPT_REDUCED_FEATURE_DIRECTION
FUTURE_MODEL_INPUT_DIRECTION: CO2 + CO2_slope
PHYSICAL_ACQUISITION_STATUS: HOLD_PENDING_REDUCED_FEATURE_CANDIDATE_LOCK
OPERATOR_GUIDE_HANDOFF: HOLD
CURRENT_B5: HISTORICAL_FROZEN_FOUR_FEATURE_CONTRACT
B5_MODIFIED: NO
C-C2_STARTED: NO
~~~

This four-feature guide is retained as historical C-C1 evidence only. Do not distribute or use it for physical collection under the current decision. Do not remove Temperature or Humidity from B5. A revised operator guide may be created only after the separately authorized `C-B6` CO₂ + `CO2_slope` candidate has been trained, validated, and locked.

## 0. Important boundary

This prompt was the historical handoff for a future physical measurement owner. The C-C1 protocol-design phase itself performed no measurement and created no new raw payload. The current handoff status is HOLD; no physical session may start from this guide.

Do not:

- run B5;
- inspect B5 performance to choose what to collect;
- change the model, scaler, threshold, feature order, or slope definition;
- start C-C2;
- create a dangerous CO₂ exposure or intentionally unsafe enclosure.

If any precollection requirement below cannot be demonstrated, stop and return a blocked preflight record. Do not improvise a replacement field.

## 1. Objective (historical four-feature contract; collection HOLD)

Collect protocol-controlled SCD40 sessions that preserve:

1. CO₂, Temperature, and Relative Humidity from the same verified SCD40 read event.
2. A defensible fresh-measurement chronology for later ENDPOINT_H150 reconstruction.
3. Separate ESP, Pi transport, logger, and sensor clocks.
4. Independent VACANT/OCCUPIED ground truth.
5. Session, device, configuration, failure, deviation, and environment provenance.
6. Immutable raw files and a final SHA-256 manifest.

The future C-C2 intake must be able to classify every session before any B5 metric is considered.

Under the current final decision, the requirements in this section are historical contract evidence only. Do not execute a physical session until a revised operator guide is issued after the reduced-feature candidate lock.

## 2. Historical frozen contract you must not change

The B5 candidate remains:

~~~text
feature order: CO2, Temperature, Humidity, CO2_slope
slope: ENDPOINT_H150
slope method: ENDPOINT_DIFFERENCE
history: at least 150 seconds of actual past-only elapsed time
maximum internal gap: 90 seconds
threshold: 0.58
model: full-integer INT8 TFLite
device-domain validation: NOT_YET_COMPLETE
effective SafeNest model-input cadence: 60 seconds nominal
normal SafeNest CO2 export cadence: 60 seconds nominal
native SCD40 measurement cadence: record separately; do not equate it with the two downstream cadences
~~~

The physical session does not produce a B5 result. It produces evidence for a later C-C2 compliance audit.

### 2.1 Normal SafeNest model-input / export cadence

The downstream SafeNest normal-data cadence is nominally 60 seconds. This is not a requirement that the SCD40 itself measure natively every 60 seconds.

- Produce one normal SafeNest-valid CO₂/Temperature/Relative Humidity record approximately every 60 seconds.
- The three values in that record must originate from the same verified fresh SCD40 measurement event and share one `measurement_event_id`.
- Do not reuse an old cached measurement merely to satisfy the 60-second schedule.
- If no verified fresh measurement is available at the scheduled point, record the appropriate missing/failure state and do not emit a valid normal model-input/export record.
- Preserve the actual sensor/event timestamp and chronology. Do not edit timestamps afterward to make spacing exactly 60 seconds.
- Preserve failure, disconnect, and deviation evidence when observed; do not hide it until the next nominal valid export.

The native SCD40 measurement interval, ESP read behavior, transport packet timing, and downstream SafeNest model-input/export cadence are separate fields/layers. Record the native configured interval separately. The 60-second contract does not move H150 history, scaling, B5 inference, threshold logic, or occupancy-model logic to the ESP32; those remain downstream on the Raspberry Pi/SafeNest processing side.

## 3. Required hardware and code precondition

Use the declared SCD40 + ESP32 + Raspberry Pi acquisition path, with a protocol-compliant adapter that exposes all required fields.

Record in the session manifest:

- SCD40 model;
- unique SCD40 serial if the device/library exposes it;
- ESP device ID;
- Pi/logger ID;
- firmware revision or immutable build identifier;
- SCD40 library revision;
- adapter/source revision;
- actual measurement mode;
- configured measurement interval;
- SafeNest effective model-input cadence: 60 seconds nominal;
- SafeNest normal CO₂ export cadence: 60 seconds nominal;
- network/transport endpoint if used.

The current legacy path is not sufficient by itself:

~~~text
devices/co2/firmware/capture_scd40.py
display-test2/esp32_sensor_node/esp32_sensor_node.ino
~~~

Do not use the legacy capture script unchanged. It polls Pi /health, drops Temperature and Humidity from the ESP telemetry contract, and does not expose a verified fresh-read sequence. The measurement owner may deploy an explicitly compliant adapter revision, but this protocol agent does not implement or deploy that change.

## 4. Precollection stop checklist

Before starting any scenario, mark every item PASS or record a blocking reason.

### 4.1 Adapter/event contract

- [ ] The deployed adapter revision is recorded.
- [ ] A fixture or replay check shows data-ready status.
- [ ] A successful readMeasurement event returns CO₂, Temperature, and Relative Humidity together.
- [ ] One measurement_event_id links those three values.
- [ ] fresh_read_sequence increments only after a successful fresh read.
- [ ] sensor_event_monotonic_ms is captured at the successful read boundary.
- [ ] Failed/not-ready reads create failure events and do not create valid feature events.
- [ ] Logger poll and Pi transport events remain separate from fresh sensor events.
- [ ] The downstream SafeNest effective model-input cadence is recorded as 60 seconds nominal, separately from the configured SCD40 measurement interval.
- [ ] The normal CO₂ export cadence is recorded as 60 seconds nominal when the same event is exported.
- [ ] A fixture or replay check confirms that stale/cached reuse is forbidden when a fresh event is unavailable at the scheduled point.

If any item fails, stop before collecting physical sessions.

### 4.2 Storage and clocks

- [ ] The raw JSONL destination is writable and empty for the new session.
- [ ] The logger can write UTC wall-clock timestamps.
- [ ] The logger can write a monotonic timestamp.
- [ ] The Pi receive timestamp and monotonic timestamp are preserved when transport is used.
- [ ] The output is not a path that can overwrite an earlier session.
- [ ] The finalization process can compute SHA-256 before any derived summary is made.

### 4.3 Device/configuration

- [ ] SCD40 model and I²C address are recorded.
- [ ] SCD40 serial is recorded, or UNIQUE_SENSOR_IDENTITY_NOT_AVAILABLE is recorded.
- [ ] Measurement mode is recorded.
- [ ] Configured measurement interval is recorded.
- [ ] ASC state is recorded or marked UNKNOWN_NOT_ACCESSIBLE with a reason.
- [ ] Temperature offset, altitude compensation, ambient pressure, and FRC history are recorded when accessible, otherwise marked explicitly unavailable/unknown.
- [ ] Power-cycle state is recorded.
- [ ] Firmware and library revisions are recorded.

### 4.4 Ground truth and safety

- [ ] The operator can record a same-logger ground-truth event marker.
- [ ] VACANT/OCCUPIED labels will be established independently of CO₂, PIR, slope, and B5.
- [ ] Door/window/ventilation/HVAC context can be recorded when it changes.
- [ ] The room remains an ordinary safe environment.
- [ ] No intentional hazardous CO₂ accumulation is planned.

## 5. Session ID and scenario

Create one immutable ID before the first raw event:

~~~text
CO2C1-YYYYMMDD-OPCODE-SNNN
~~~

Use one scenario per session:

- VACANT_STABLE
- OCCUPIED_STABLE
- VACANT_TO_OCCUPIED
- OCCUPIED_TO_VACANT

Start a new session after:

- ESP/device reboot;
- power cycle;
- logger or receiver restart;
- location change;
- measurement configuration change;
- occupancy scenario reset;
- operator restart;
- more than 90 seconds without verified fresh chronology.

Never carry a slope history across sessions.

## 6. Raw event that must be preserved

Write one immutable JSON object per raw event to raw_measurements.jsonl. At minimum, preserve:

~~~text
protocol_id
protocol_version
session_id
scenario_id
measurement_event_id
fresh_read_sequence
sensor_event_monotonic_ms
data_ready
sensor_read_status
co2_ppm
temperature_c
relative_humidity_pct
per_feature_valid
raw_sensor_payload
scd40_model
scd40_serial_or_UNIQUE_SENSOR_IDENTITY_NOT_AVAILABLE
esp_device_id
esp_uptime_ms
telemetry_sequence
firmware_revision
sensor_library_revision
pi_receive_timestamp_utc
pi_receive_monotonic_ns
transport_connected
transport_fresh
transport_age_seconds
transport_status
logger_timestamp_utc
logger_monotonic_ns
logger_row_index
ground_truth_ref
environment_context
failure_event_ref
deviation_event_ref
~~~

Do not write a synthetic normal value for a missing or invalid field. Use null plus a declared status.

## 7. Fresh SCD40 event rule

Treat an event as a verified fresh SCD40 event only when:

1. data-ready is true.
2. readMeasurement succeeds.
3. CO₂, Temperature, and Relative Humidity are finite values from that same read call.
4. fresh_read_sequence increments exactly once.
5. sensor_event_monotonic_ms is captured at read completion.
6. The same measurement_event_id is attached to all three values.

The following are not sufficient:

- a new logger row;
- a new telemetry sequence;
- Pi transport_fresh;
- a recent age_seconds value;
- a numeric cached CO₂ value;
- a successful HTTP request alone.

When data-ready is false, write SENSOR_DATA_NOT_READY to the failure registry. When the read fails, write SENSOR_READ_FAILED or SENSOR_INVALID as appropriate. Preserve the attempted event and do not increment the fresh-read sequence.

At the nominal 60-second normal-data point, a missing fresh event remains a missing/failure condition. Do not fabricate a valid record, reuse a cached value, or rewrite timestamps. Failure and disconnect evidence is preserved when observed and does not wait for the next normal valid export.

## 8. Timestamp rules

Record all of the following where the layer exists:

| Field | Rule |
|---|---|
| sensor_event_monotonic_ms | ESP monotonic time at successful read; used for sensor chronology; resets require a new session |
| logger_monotonic_ns | Logger monotonic time; used for host-local order and gaps |
| logger_timestamp_utc | UTC wall time; never edit after capture |
| pi_receive_timestamp_utc | Packet receipt time; not sensor event time |
| pi_receive_monotonic_ns | Pi host-local packet chronology |
| ground_truth_event_timestamp_utc | Same logger clock as the entry/exit marker |

Use monotonic clocks to calculate elapsed time. Use UTC for provenance and same-logger ground-truth alignment. Do not claim that ESP, Pi, and logger wall clocks are synchronized more precisely than demonstrated.

## 9. Ground-truth actions

Write ground_truth_events.jsonl independently of sensor values.

Allowed labels:

~~~text
VACANT
OCCUPIED
~~~

Allowed sources:

~~~text
CONTROLLED_EMPTY_ROOM
CONTROLLED_PERSON_PRESENT
RECORDED_ENTRY
RECORDED_EXIT
~~~

For every label segment or transition, record:

- ground_truth_event_id;
- session_id;
- label;
- source;
- start timestamp;
- end or transition timestamp;
- ground_truth_status;
- operator_id.

Use CONFIRMED_OPERATOR_CONTROLLED only when the state is directly controlled and timed. Use UNCERTAIN or CONFLICTED when appropriate. Use MISSING when no independent truth exists.

Never derive the label from CO₂, CO₂_slope, PIR, a filename, or B5 output. Do not edit a label after viewing any model output.

## 10. Scenario procedure and H150 completion

The per-session timing rule is based on the frozen 150-second H150 history, not on an arbitrary row count.

### VACANT_STABLE

1. Establish and log CONFIRMED_OPERATOR_CONTROLLED VACANT truth.
2. Start the declared measurement mode.
3. Record warm-up and all not-ready events.
4. Mark WARMUP_COMPLETE at the first verified fresh event.
5. Continue until at least 150 seconds of same-session verified fresh chronology is available.
6. Record the session end marker and final environment state.

### OCCUPIED_STABLE

Follow the VACANT_STABLE steps with CONFIRMED_OPERATOR_CONTROLLED OCCUPIED truth.

### VACANT_TO_OCCUPIED

1. Establish and log VACANT truth.
2. Complete warm-up.
3. Obtain at least 150 seconds of verified fresh VACANT chronology.
4. Record the person entry marker on the logger clock.
5. Change to the controlled OCCUPIED state and record the new GT segment.
6. Obtain at least 150 seconds of verified fresh OCCUPIED chronology.
7. Close the session and record the final state.

### OCCUPIED_TO_VACANT

Follow the transition procedure in the reverse direction: obtain at least 150 seconds of verified OCCUPIED chronology, record the exit marker, then obtain at least 150 seconds of verified VACANT chronology.

If an interruption exceeds 90 seconds or a device restarts, close the session and start a new one. Do not repair the chronology by interpolation or forward-fill.

With nominal 60-second sampling, one missed valid point can create an approximately 120-second gap between valid events. Since `120 > 90`, reset the frozen H150 history and mark `CO2_slope` unavailable until sufficient causal, past-only history is rebuilt. Do not relax the 90-second reset rule.

The total number of sessions is supplied by a separately authorized measurement schedule. Do not choose the count or stop based on B5.

## 11. Environment context

Record location_id and scenario_id for every session. Record when relevant:

- door state;
- window state;
- ventilation state;
- HVAC state;
- another event that materially changes CO₂ interpretation.

If a relevant state is unavailable, write UNKNOWN_WITH_REASON. Do not invent a value.

## 12. Failure and deviation handling

Write failure_events.jsonl immediately when an abnormal event occurs. Use declared statuses:

~~~text
SENSOR_READ_FAILED
SENSOR_DATA_NOT_READY
SENSOR_INVALID
TRANSPORT_DISCONNECTED
TRANSPORT_STALE
LOGGER_ERROR
DEVICE_RESTART
SESSION_INTERRUPTED
GROUND_TRUTH_MISSING
CONFIGURATION_UNKNOWN
PROTOCOL_DEVIATION
~~~

Write deviation_events.jsonl for any departure from this protocol. Include:

- deviation ID;
- timestamp;
- session ID;
- reason;
- affected fields/events;
- operator action;
- expected C-C2 compliance consequence.

Keep failed and incomplete sessions. Do not delete them from the returned bundle.

## 13. Raw finalization and checksum

Use a new bundle directory for each session or authorized acquisition batch:

~~~text
<bundle-root>/<session_id>/
  raw_measurements.jsonl
  session_manifest.json
  ground_truth_events.jsonl
  failure_events.jsonl
  deviation_events.jsonl
  checksums.sha256
  operator_notes.md
~~~

Finalize in this order:

1. Stop capture.
2. Close all files.
3. Record byte sizes and line/event counts.
4. Compute SHA-256 for every handoff file except checksums.sha256 itself.
5. Write checksums.sha256 with path, size, count where applicable, session ID, protocol ID/version, and digest.
6. Mark the bundle frozen.
7. Only then produce derived summaries.

After finalization:

- do not edit raw values;
- do not edit timestamps;
- do not edit labels;
- do not reorder or renumber rows;
- do not overwrite a file;
- do not regenerate checksums after an unrecorded mutation.

If a later digest differs, report RAW_EVIDENCE_MUTATION_DETECTED.

## 14. Required returned artifacts

Return all of the following, including failed/incomplete sessions:

- raw_measurements.jsonl;
- session_manifest.json;
- ground_truth_events.jsonl;
- failure_events.jsonl;
- deviation_events.jsonl;
- checksums.sha256;
- operator_notes.md;
- a precollection checklist result;
- the adapter/firmware/library revision identifiers;
- a session-level protocol compliance declaration.

Do not return only selected “good” sessions.

## 15. Prohibited actions

Do not:

- run B5 or any other model during accumulation;
- delete outliers;
- fill missing samples;
- interpolate raw evidence;
- replace failures with zero;
- edit timestamps;
- edit labels after looking at model output;
- discard failed sessions;
- change session duration or conditions because of a B5 result;
- change the B5 threshold, feature order, scaler, model, or H150 definition;
- create intentional unsafe CO₂ exposure;
- begin C-C2 without explicit authorization.

## 16. Stop conditions

Stop before physical collection if:

- the adapter cannot preserve same-event CO₂/Temperature/Humidity;
- data-ready or successful-read evidence is unavailable;
- fresh_read_sequence or sensor_event_monotonic_ms is unavailable;
- logger timestamps or monotonic clocks cannot be preserved;
- raw files cannot be sealed and hashed;
- independent ground truth cannot be recorded;
- device/configuration identity cannot be recorded or explicitly classified;
- the downstream 60-second model-input/export cadence cannot be recorded separately from native SCD40 timing or cannot preserve missing/failure status without stale reuse;
- safe ordinary environmental operation cannot be maintained.

If a session fails after collection begins, preserve it, record the failure, close it, and classify it. Do not silently restart inside the same session.

## 17. Completion report to return

Return a short report with:

~~~text
protocol_id:
protocol_version:
effective_model_input_cadence_sec: 60 nominal
normal_co2_export_cadence_sec: 60 nominal
native_scd40_cadence_recorded_separately: YES
operator_id:
adapter_revision:
session_ids:
sessions_completed:
sessions_incomplete:
fresh_event_contract_precheck:
ground_truth_contract_precheck:
raw_checksum_status:
protocol_compliance_status:
failures:
deviations:
returned_bundle_path:
B5_inference_performed: NO
~~~

This report is a handoff record only. It does not authorize C-C2 or any model evaluation.
