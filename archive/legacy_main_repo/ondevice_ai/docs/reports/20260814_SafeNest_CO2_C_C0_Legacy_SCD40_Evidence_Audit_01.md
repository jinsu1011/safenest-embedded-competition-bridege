# SafeNest CO₂ C-C0 Legacy SCD40 Evidence Audit

**Document status:** evidence record and maintainer handoff
**Audit date:** 2026-08-14
**Current classification:** B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE
**Scope:** legacy team SCD40 measurements already present in the team repository
**Change type:** documentation only; no model, dataset, runtime, firmware, or team-repository modification

## 1. Executive finding

The legacy evidence is real-device CO₂ evidence collected through the team’s SCD40-to-ESP32-to-Raspberry-Pi telemetry path. It is useful for establishing that the hardware path produced plausible CO₂ values and that the transport layer records explicit NORMAL, STALE, and NOT_CONNECTED states.

It is **not** sufficient for formal device-domain validation of the locked CO₂ B5 candidate. The frozen B5 input vector is:

$$
[\mathrm{CO2},\ \mathrm{Temperature},\ \mathrm{Humidity},\ \mathrm{CO2\_slope}]
$$

The legacy capture preserves CO₂ but does not preserve Temperature or Humidity. It also does not provide a verified fresh-SCD40 measurement-event chronology for CO2_slope. Therefore:

- CO₂ is available, but not every row is transport-valid.
- Temperature availability is NO.
- Humidity availability is NO.
- Temperature/Humidity semantic correspondence is UNKNOWN / NOT_ASSESSABLE, not NO, because the fields were not captured for comparison.
- CO2_slope temporal correspondence is UNKNOWN.
- ENDPOINT_H150 is diagnostic-only for this legacy evidence.
- No B5 inference result is authorized from this evidence.
- No occupancy ground truth or occupancy metric is established.

The correct C-C0 outcome is therefore:

> **B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE**

This document records what the legacy evidence can prove and what it cannot prove. It does not freeze the future C-C1 measurement protocol.

## 2. Audit boundary and non-goals

### 2.1 Included

This audit covers:

1. The four legacy raw CSV files currently present on team origin/main.
2. The capture script, ESP32 telemetry path, Raspberry Pi cache/API path, and associated verification report.
3. Current raw-byte hashes recomputed from the team repository.
4. Historical hashes recorded in the team analysis summaries and verification report.
5. The standalone repository’s locked B5 feature contract and current C-C roadmap interpretation.

### 2.2 Explicitly not performed

This evidence audit did not perform model inference, new physical measurement, runtime/firmware modification, model modification, or team-repository modification.

It also did not:

- calculate occupancy F1, AUROC, confusion matrices, or threshold performance;
- start C-C1;
- freeze a final C-C1 protocol;
- modify the active roadmap.

## 3. Reproducibility anchors

The following references were checked before writing this document:

| Reference | Revision or path | Role |
|---|---|---|
| Standalone SafeNest repository | origin/main at c65d2e32e6f14089790a8c576312eb9873e367f7 | Active roadmap, B5 lock, model and dataset manifests |
| Team repository | origin/main at 5947334d3d0f6c6f7d6100c7ea6af219e5b4c5d5 | Current legacy firmware, telemetry, raw logs, and verification evidence |
| Active master roadmap | [docs/20260810_ChatGPT_SafeNest_Multisensor_Parallel_Execution_Roadmap_01.md](../20260810_ChatGPT_SafeNest_Multisensor_Parallel_Execution_Roadmap_01.md) | C-C0/C-C1/C-C2 ordering and decision gate |
| B5 final lock | [datasets/co2/manifests/c_b5_robustness_final_lock/final_candidate_lock.json](../../datasets/co2/manifests/c_b5_robustness_final_lock/final_candidate_lock.json) | Locked candidate and closure state |
| B5 candidate metadata | [models/co2/candidates/c_b5/final_candidate_metadata.json](../../models/co2/candidates/c_b5/final_candidate_metadata.json) | Frozen feature order and device-domain status |
| Team raw capture implementation | devices/co2/firmware/capture_scd40.py | CSV schema and fail-closed capture semantics |
| Team SCD40/ESP32 implementation | display-test2/esp32_sensor_node/esp32_sensor_node.ino | SCD40 read path and telemetry payload |
| Team Pi receiver/API | display-test2/raspberry_pi_lcd/server.py | Latest-value cache and transport freshness |
| Team protocol | display-test2/docs/COMMUNICATION_PROTOCOL.md | TCP and /health contract |
| Team verification report | devices/co2/docs/VERIFICATION_REPORT_2026-08-12.md | Historical test conclusions and recorded hashes |
| Team evidence contract tests | devices/co2/tests/test_co2_evidence_contract.py | Software/replay contract checks |

The team paths above are paths in the private team repository, not files added to this standalone repository by this audit.

## 4. Evidence source and signal lineage

The legacy files were not direct SCD40 I²C logs. The observed lineage is:

~~~text
SCD40 on ESP32 → ESP32 TelemetrySnapshot → TCP to Raspberry Pi
→ Pi latest-value SensorStore → Pi /health → capture_scd40.py → raw CSV
~~~

Important lineage facts:

- The SCD40 is addressed as 0x62 on the ESP32 I²C bus.
- The ESP32 code uses SCD4x periodic mode and checks data readiness before readMeasurement.
- The ESP32 polling loop runs every 250 ms.
- The ESP32 publishes a telemetry snapshot approximately every 1000 ms.
- The ESP32 telemetry payload carries co2_ppm and a CO₂ validity flag, but it does not carry Temperature or Humidity.
- The Raspberry Pi stores the latest received telemetry packet and exposes transport status through /health.
- The capture script polls /health at a nominal 1-second interval.
- The captured CO₂ value is therefore a device-derived value transported through a latest-value cache, not a direct per-row native SCD40 measurement record.

The model-level hardware identity is supported by the SCD40 implementation and the team verification report. A unique SCD40 serial number or other unique physical sensor identity is not present in the legacy CSV contract. The observed device_id is the ESP32 telemetry identity, esp32-01, not a unique SCD40 identity.

## 5. Legacy raw-file inventory

The following statistics were recomputed from the current raw bytes at team origin/main 5947334d3d0f6c6f7d6100c7ea6af219e5b4c5d5.

| Raw file | Scenario | Total rows | Valid rows | Invalid rows | Invalid state breakdown | Valid CO₂ range (ppm) | Host interval min/max/mean (s) |
|---|---|---:|---:|---:|---|---:|---|
| devices/co2/firmware/logs/2026-08-12_preflight_30s.csv | preflight | 30 | 30 | 0 | — | 504–634 | 0.999363 / 1.000655 / 0.999998 |
| devices/co2/firmware/logs/2026-08-12_baseline_5min.csv | baseline | 300 | 277 | 23 | NOT_CONNECTED=14, STALE=9 | 495–506 | 0.998974 / 1.000640 / 0.999998 |
| devices/co2/firmware/logs/2026-08-12_baseline_attempt02_5min.csv | baseline | 300 | 300 | 0 | — | 505–516 | 0.997832 / 1.002460 / 0.999996 |
| devices/co2/firmware/logs/2026-08-12_breath-rise-recovery_6min.csv | breath-rise-recovery | 360 | 329 | 31 | NOT_CONNECTED=16, STALE=15 | 507–1493 | 0.999451 / 1.000536 / 1.000000 |
| **Aggregate** | — | **990** | **936** | **54** | **NOT_CONNECTED=30, STALE=24** | **495–1493** | — |

The valid-row means were approximately 560.37 ppm, 500.11 ppm, 511.07 ppm, and 896.24 ppm respectively for the four files. These are descriptive values for the captured rows; they are not occupancy labels and are not a B5 evaluation result.

The explicit invalid states are evidence, not rows to silently convert to zero or to a synthetic normal value. The team capture and contract tests preserve fail-closed behavior at the transport-validity boundary.

## 6. Raw CSV schema and units

The capture implementation declares these columns:

~~~text
host_timestamp
host_unix_s
host_monotonic_ns
scenario
source_url
device_id
seq
uptime_ms
co2_ppm
valid
sensor_state
error
connected
fresh
transport_status
peer
age_seconds
last_received_at
raw_response_json
~~~

Interpretation:

| Field group | Evidence meaning | Limitation |
|---|---|---|
| host_timestamp, host_unix_s, host_monotonic_ns | Time recorded by the Pi capture process | Not a native SCD40 measurement timestamp |
| scenario | Operator-supplied capture context | Not synchronized occupancy ground truth |
| device_id, seq, uptime_ms | ESP32 telemetry identity and packet counters | Packet chronology is not the same as SCD40 fresh-measurement chronology |
| co2_ppm | Numeric CO₂ value in ppm from the telemetry path | A cached value can remain present while transport validity is false |
| valid | Capture-level validity: CO₂ valid, numeric, connected, and fresh | Does not prove that a new SCD40 conversion occurred for that row |
| sensor_state, error | Fail-closed state and reason | Correctly separates NORMAL, STALE, and NOT_CONNECTED |
| connected, fresh, transport_status, age_seconds, last_received_at | Pi transport/cache freshness evidence | fresh is transport freshness, not SCD40 measurement freshness |
| raw_response_json | Raw /health response retained in each row | It is still a snapshot of the latest-value API, not a direct I²C event log |

All 990 raw_response_json values parsed successfully in this audit. Each contained a numeric cached sensors.co2_ppm and sensors.valid.co2=true. No nested temperature-like or humidity-like keys were present in the 990 captured JSON objects.

This combination is important: some rows are capture-invalid because the Pi reports a stale or disconnected transport state even though the latest cached JSON still contains a numeric CO₂ value and a CO₂ validity flag. A numeric field alone must not be treated as a valid fresh sample.

## 7. Freshness and timestamp assessment

There are at least three different clocks or freshness concepts in the path:

1. **SCD40 conversion/read cadence.** The ESP32 comments identify SCD4x periodic mode as producing a new sample about every 5 seconds. The code polls readiness every 250 ms.
2. **ESP32 telemetry cadence.** The ESP32 publishes a snapshot approximately every 1 second, carrying the latest CO₂ value.
3. **Pi transport freshness.** The Pi receiver updates the latest-value store when a packet arrives. The /health status uses a 5-second stale threshold; the ESP32 CO₂ validity cache uses a 15-second stale threshold for its last successful CO₂ read.

The raw CSV contains host timestamps, host monotonic timestamps, packet sequence and uptime fields, and Pi transport fields. It does not contain a verified SCD40 measurement-event marker or a native sensor timestamp associated with each co2_ppm.

Consequently:

- Logger polling cadence: **verified at approximately 1 second**.
- Transport freshness: **represented and replay-testable**.
- SCD40 fresh-measurement cadence per captured row: **unknown**.
- One-to-one mapping from each CSV row to a new SCD40 conversion: **not established**.
- CO2_slope on the frozen H150 profile: **not formally assessable** from this legacy evidence.

The host intervals are regular enough to support chronology diagnostics. They do not upgrade the chronology into a verified fresh-sensor event sequence.

## 8. Temperature and Humidity assessment

The ESP32 SCD40 read call receives temperature and humidity local values, but the implementation only stores and publishes co2Ppm. The TelemetrySnapshot and the transmitted safenest.telemetry.v1 payload contain no Temperature or Humidity fields.

The resulting distinction is:

| Question | Result | Reason |
|---|---|---|
| Is a numeric Temperature field available in the legacy raw capture? | NO | No temperature field exists in the CSV or nested telemetry JSON |
| Is a numeric Humidity field available in the legacy raw capture? | NO | No humidity field exists in the CSV or nested telemetry JSON |
| Has Temperature semantic correspondence been disproven? | UNKNOWN / NOT_ASSESSABLE | No captured field exists to compare |
| Has Humidity semantic correspondence been disproven? | UNKNOWN / NOT_ASSESSABLE | No captured field exists to compare |
| Can either feature be substituted with zero, a default, or an inferred value for B5? | NO | That would violate the frozen feature contract |

NO is correct for feature availability. UNKNOWN / NOT_ASSESSABLE is the correct semantic-correspondence status.

## 9. CO₂ and slope assessment

CO₂ is the only frozen B5 feature preserved in the legacy payload. The values are in ppm and include both normal-range baselines and a breath-rise-recovery range up to 1493 ppm. The capture includes explicit validity and transport-state fields, so the CO₂ evidence is classified as PARTIAL, not as a clean frozen feature stream.

The frozen B5 candidate uses ENDPOINT_H150 for CO2_slope. A host-time slope can be calculated mechanically from adjacent CSV values, but that would not establish that the adjacent values represent fresh SCD40 conversions. It could instead reflect repeated reads of a latest-value cache or transitions in transport validity.

Therefore:

- CO₂ semantic correspondence: PARTIAL.
- CO2_slope temporal correspondence: UNKNOWN.
- ENDPOINT_H150: DIAGNOSTIC_ONLY for this legacy evidence.
- No slope-derived B5 input may be promoted to formal validation status.

## 10. Raw integrity and checksum provenance

The capture script opens output with create-exclusive mode and refuses to overwrite an existing raw file. That is a useful acquisition-time safeguard. It does not by itself prove that the bytes remained unchanged after capture or that the current bytes are identical to the bytes used by the original team analysis.

The current raw hashes were recomputed from team origin/main. They do not match the hashes recorded in the historical analysis summaries and verification report:

| Raw file | Current raw SHA-256 | Historical recorded SHA-256 | Match |
|---|---|---|---|
| 2026-08-12_preflight_30s.csv | e414be88d5b246411143b7353493565f8fea95bd6fd7f8120804c478f89c41fb | dea523b77258b8cf6f08987e575102c2aa29877fb96b8cbcf05985acd5918f2f | NO |
| 2026-08-12_baseline_5min.csv | f9fee44ef154bc03ff2c3e0704b3b2c9732841b8510656585b4e7ed9226b6357 | 11f58c3d624cff907f033fdcaa1e1041614a6aad282c3b6005efb052c7af7c42 | NO |
| 2026-08-12_baseline_attempt02_5min.csv | 741e9a48b77bd8c8a4bbff31f795b1b66f748e8e3dcb36efa2b3470ef60e4d4f | 409b788437e4685f8136f6d6b19c2f47d3ecd081ee56f46d958bf6ab486f9ad1 | NO |
| 2026-08-12_breath-rise-recovery_6min.csv | b9d01bb96aedd0df68e4f13a8ae2d4512f67e64d359a44a1c4c8c2642d110b32 | 2f5a2b7b6e4baf4d2544baefc3c0e3a65dc082bac7a95565002d784454a096c9 | NO |

The appropriate classification is:

~~~text
RAW_BYTES_AVAILABLE: YES
RAW_IMMUTABILITY: PARTIAL
HISTORICAL_SHA256_MATCH: NO
POST_CAPTURE_BYTE_STABILITY: UNVERIFIED
~~~

The current files remain inspectable evidence. They must not be described as cryptographically proven unchanged copies of the original capture bytes.

## 11. Failure-state evidence

The four files contain 54 capture-invalid rows:

- NOT_CONNECTED: 30 rows.
- STALE: 24 rows.

The invalid rows are retained in the raw files and are not zero-filled. The contract tests cover the software behavior that disconnect, nonnumeric data, and invalid data remain invalid. Those tests prove software/replay contract behavior; they do not prove a new physical disconnect experiment.

The team verification report also classifies the overall hardware verification as partial. Normal measurement and an exhalation response were reported, while the disconnect contract was not formally completed with a qualifying 60-second raw capture. This audit preserves that boundary.

## 12. Ground-truth assessment

No independent, synchronized occupancy ground truth is present in these raw files.

The following are **not** occupancy ground truth:

- scenario=baseline;
- scenario=breath-rise-recovery;
- the CO₂ level or CO₂ rise itself;
- PIR motion in the telemetry payload;
- filenames;
- operator context inferred after capture;
- a future B5 model output.

The files can support descriptive sensor/transport analysis and measurement-design planning. They cannot support an occupancy confusion matrix or an authorized B5 performance claim.

## 13. Locked B5 contract and why inference remains blocked

The standalone B5 lock remains unchanged:

- Candidate status: FINAL_OFFLINE_UCI_CANDIDATE_LOCKED.
- Device-domain validation status: NOT_YET_COMPLETE.
- Feature order: CO2, Temperature, Humidity, CO2_slope.
- Slope profile: ENDPOINT_H150.
- Threshold: 0.58.
- Candidate model: LINEAR_LOGISTIC.
- Final lock profile: CO2_B5_FINAL_OFFLINE_CANDIDATE_LOCK_001.
- Final lock SHA-256: a020d462e0d359e0c9faa9bb680387119f095cb102243d7e6c223d76a801b627.
- Model SHA-256: bb2ed28533bca75d4fa3d06348e017c506df47d7c34b29574b77f70b6b386816.
- Preprocessing scaler fingerprint: d0cf83558fb0de9dcdc97f0d94781a5a475a6f68e8d818121aee929030e5dc89.

The legacy evidence cannot satisfy the four-feature contract because two features are absent and the slope chronology is not verified. No feature imputation, default substitution, or adaptive tuning is authorized to make the vector appear complete.

Thus:

~~~text
FROZEN_FEATURE_VECTOR: INCOMPLETE
FORMAL_DEVICE_DOMAIN_VALIDATION: NO
FROZEN_B5_INFERENCE: BLOCKED
~~~

C-C0 success means that the legacy evidence has been audited and classified. It does not mean B5 inference succeeded.

## 14. What this evidence does support

The evidence supports the following bounded statements:

1. The team’s SCD40 hardware path produced numeric CO₂ telemetry.
2. The ESP32-to-Pi transport and /health cache exposed explicit connection/freshness states.
3. The capture code preserved raw /health snapshots and fail-closed validity fields.
4. The current raw files contain 990 rows, 936 capture-valid rows, and 54 explicit invalid rows.
5. The current files include a descriptive baseline and breath-rise-recovery pattern in CO₂.
6. The transport layer can produce stale and disconnected states that must remain visible to later validation.
7. The legacy path does not preserve the complete frozen B5 feature vector.

## 15. What this evidence does not support

It does not support:

- a formal device-domain B5 score;
- occupancy F1, AUROC, accuracy, recall, or precision;
- a claim that the model generalizes to the device domain;
- a claim that CO2_slope is based on fresh SCD40 conversions;
- a claim that Temperature or Humidity semantics are mismatched;
- a claim that the current raw bytes are unchanged from the original capture;
- a clinical/medical safety or performance conclusion;
- a final C-C1 protocol decision;
- a C-D authorization.

## 16. Measurement gaps for a future C-C1 handoff

The next authorized measurement-design stage should address, at minimum:

- preservation of Temperature and Humidity from the same SCD40 read event;
- a verifiable fresh-measurement marker or equivalent event contract;
- a trustworthy timestamp associated with each verified fresh measurement event;
- unique sensor/device identity and session identity;
- explicit measurement mode and configuration;
- calibration, ambient-pressure, altitude, temperature-offset, and related metadata when applicable;
- power-cycle, reset, disconnect, timeout, and recovery events;
- synchronized ground-truth source, label ownership, and timing;
- a capture-time manifest and checksum procedure whose relation to raw bytes is explicit;
- a distinction between sensor freshness, transport freshness, and logger polling cadence.

This list is a gap inventory, not a frozen C-C1 protocol. No external acquisition or B5 evaluation is authorized by this document.

## 17. Machine-readable classification block

The following block is intentionally plain text so validators and future agents can locate the C-C0 decision without interpreting prose:

~~~text
AUDIT_ID: SAFE_NEST_CO2_C_C0_LEGACY_SCD40_20260814_01
AUDIT_DATE: 2026-08-14
STANDALONE_ORIGIN_MAIN_SHA: c65d2e32e6f14089790a8c576312eb9873e367f7
TEAM_ORIGIN_MAIN_SHA: 5947334d3d0f6c6f7d6100c7ea6af219e5b4c5d5
REAL_DEVICE_SOURCE: VERIFIED
SCD40_MODEL_IDENTITY: VERIFIED
UNIQUE_SCD40_DEVICE_IDENTITY: UNKNOWN
RAW_BYTES_AVAILABLE: YES
RAW_IMMUTABILITY: PARTIAL
HISTORICAL_SHA256_MATCH: NO
POST_CAPTURE_BYTE_STABILITY: UNVERIFIED
RAW_ROW_COUNT: 990
RAW_VALID_ROW_COUNT: 936
RAW_INVALID_ROW_COUNT: 54
INVALID_NOT_CONNECTED_ROWS: 30
INVALID_STALE_ROWS: 24
LOGGER_POLL_CADENCE: VERIFIED_APPROX_1S
TRANSPORT_FRESHNESS: VERIFIED_AS_REPRESENTED
SCD40_FRESH_MEASUREMENT_CADENCE: UNKNOWN
CO2_AVAILABILITY: YES
CO2_SEMANTIC_CORRESPONDENCE: PARTIAL
TEMPERATURE_AVAILABILITY: NO
TEMPERATURE_SEMANTIC_CORRESPONDENCE: UNKNOWN_NOT_ASSESSABLE
HUMIDITY_AVAILABILITY: NO
HUMIDITY_SEMANTIC_CORRESPONDENCE: UNKNOWN_NOT_ASSESSABLE
CO2_SLOPE_TEMPORAL_CORRESPONDENCE: UNKNOWN
ENDPOINT_H150: DIAGNOSTIC_ONLY
FROZEN_FEATURE_VECTOR: INCOMPLETE
OCCUPANCY_GROUND_TRUTH: ABSENT
OCCUPANCY_METRICS_AUTHORIZED: NO
FORMAL_DEVICE_DOMAIN_VALIDATION: NO
FROZEN_B5_INFERENCE: BLOCKED
C_C0_OUTCOME: B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE
NEXT_STAGE: C_C1_PROTOCOL_FREEZE_AND_OPERATOR_HANDOFF
~~~

## 18. Maintainer handoff

Future agents should treat this document as a C-C0 evidence boundary:

- preserve the raw files and their current hashes as an observed snapshot;
- do not overwrite the historical hash mismatch with a new “verified immutable” claim;
- do not infer Temperature, Humidity, or fresh-measurement slope data;
- do not run B5 against an incomplete vector;
- keep legacy evidence accumulation separate from model development;
- use the active roadmap for the C-C1/C-C2 order and explicit C-D gate.

No model inference, new physical measurement, runtime/firmware modification, model modification, or team-repository modification was performed as part of this report.
