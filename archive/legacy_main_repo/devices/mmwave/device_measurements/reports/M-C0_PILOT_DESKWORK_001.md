# M-C0 Physical Pilot: Desk Work with Small Arm Movements

## Decision

`M-C0-PILOT-DESKWORK-001` proves that the standalone MR60BHA2 → ESP32 → USB JSON acquisition path can preserve an approximately 10Hz telemetry-row stream with no observed transport-integrity failures during a 180-second desk-work session. It does not by itself prove a 10Hz fresh `0x0A13 breath_phase` update stream.

The session is `PASS_WITH_LIMITATIONS`, not formal evidence and not training data. Small arm/paperwork movement coincided with large distance variation and a high proportion of `BREATH_PHASE_LOW_AMPLITUDE`/`DEGRADED` records. No independent respiration reference was collected, so respiration and heart accuracy remain unverified.

## Session

| Item | Value |
|---|---|
| Label | `PILOT_NOT_FORMAL_EVALUATION` |
| Session ID | `M-C0-PILOT-DESKWORK-001` |
| UTC start | `2026-08-14T06:20:00.299921Z` |
| UTC end | `2026-08-14T06:23:00.309841Z` |
| Condition | seated, front-facing, ordinary paperwork with small arm movements |
| Reported distance | approximately 50-60cm; manifest representative value 55cm |
| Sensor height | aligned with chest; absolute floor height not measured |
| Other person | approximately 2m behind target, no movement reported |
| Reference | none/not collected |
| Firmware | `safenest-mr60-esp/1.2.0` |
| Config hash | `b817e8bfd5e52b18275626f7b6a9bd60098ea4b108428a5aaf63600dbc987834` |

## Immutable raw identity

This curated Pilot raw is intentionally Git-tracked under the narrow `TRACKED_EXCEPTION` policy. The general JSONL ignore rule remains in force for unrelated or unreviewed data.

```text
path: devices/mmwave/device_measurements/pilot/M-C0-PILOT-DESKWORK-001.raw.jsonl
records: 1,799
bytes: 1,819,539
SHA-256: 368e6a16e897b9231ff5fcdecd3edcc5b725a0a4dc6b20dee1e3162405bc2876
```

## Timing and transport QA

| Metric | Result |
|---|---:|
| Telemetry rows / intervals | 1,799 / 1,798 |
| Telemetry-row cadence | 9.993997Hz |
| Minimum interval | 100ms |
| Mean interval | 100.060067ms |
| Median interval | 100ms |
| p95 interval | 100ms |
| Interval jitter, population stddev | 0.299715ms |
| Maximum gap | 103ms |
| Gaps over 500ms | 0 |
| Nominal 30-second windows | 5 |
| Malformed JSON | 0 |
| UART bad | 0 |
| Checksum bad | 0 |
| Sequence gap/duplicate/backward | 0/0/0 |
| Timestamp duplicate/backward | 0/0 |

Strict contract validation passed with `raw_records=1799`.

`phase_age_ms` was present and valid in all 1,799 rows: min `0ms`, median `12ms`, p95 `15ms`, max `111ms`; missing/null `0`, invalid `0`. The producer validity threshold is `kPhaseMaxAgeMs = 500ms` in `devices/mmwave/firmware/include/mmwave_config.h`; no row reached it. This threshold supports producer stale/valid classification but does not reconstruct exact arrivals. `phase_age_ms` is freshness evidence, not an exact frame-arrival log, and repeated numeric values alone are not stale proof. Final status: `FRESH_PHASE_CADENCE_NOT_YET_FULLY_VERIFIED`.

## Physical fields

Presence, distance, raw respiration, raw heart, total phase, breath phase and heart phase were populated for all 1,799 records. `sensor_firmware_version` was not reported.

| Field | Minimum | Median | Maximum |
|---|---:|---:|---:|
| Distance | 40.18cm | 51.66cm | 120.54cm |
| Raw respiration | 0.0 RPM | 21.0 RPM | 32.0 RPM |
| Filtered respiration | 13.58 RPM | 18.59 RPM | 22.49 RPM |
| Raw heart | 0.0 BPM | 82.0 BPM | 118.0 BPM |
| Breath phase | -0.70 | 0.00 | 0.75 |
| Heart phase | -1.65 | 0.00 | 1.67 |
| Total phase | -3.01 | -0.02 | 3.13 |

## Movement finding

```text
VALID: 838 records (46.58%)
DEGRADED: 961 records (53.42%)
BREATH_PHASE_LOW_AMPLITUDE: 961 records
filtered respiration populated: 838/1,799 (46.58%)
```

This is evidence that the desk-work condition materially affects the current filtered-validity gate. It does not prove that arm movement alone caused every degraded record because the session also had an unmeasured absolute sensor height, one other person behind the target, and no synchronized reference.

## Claim boundary

```text
physical JSON signal captured = true
telemetry row cadence measured = true for this Pilot
exact fresh phase cadence verified = false
transport integrity passed = true for this Pilot
phase fields physically populated = true
phase units/scale/reset semantics verified = false
respiration accuracy verified = false
heart accuracy verified = false
training suitability established = false
formal device evidence complete = false
Raspberry Pi E2E validated = false
deployment ready = false
clinical apnea validated = false
```

## Required next work

1. Do not repeat the completed stationary raw capture.
2. After user approval, create its manifest and run strict contract/physical QA without modifying the raw file.
3. Compare stationary and desk-work sessions only in a derived report.
4. Run the physical phase stream through the locked 30-second/300-sample preprocessing path.
5. Add a synchronized independent respiration reference only if an accuracy claim is required.
