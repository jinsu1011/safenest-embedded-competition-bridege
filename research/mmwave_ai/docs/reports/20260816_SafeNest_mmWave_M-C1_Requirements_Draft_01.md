# SafeNest mmWave M-C1 Requirements Draft

Status: **documentation only — hardware available; M-C1 is `PENDING_EXPLICIT_PROTOCOL_APPROVAL`**

This draft records capture requirements derived from the measured M-C0
correspondence audit. It does not authorize M-C1 capture, inference, model
scoring, retraining, preprocessing changes, or LOCKED_TEST access.

## Why these requirements exist

The M-C0 audit of the long MR60 log
`devices/mmwave/firmware/logs/final/2026-08-01_occupied_d09_v120_31min_attempt02.jsonl`
measured telemetry row cadence separately from reconstructed fresh updates:
`9.986342911 Hz` versus corrected `8.419003785 Hz`. The earlier
`4.30467137 Hz` value is retained only as `RETRACTED_FAULTY_ESTIMATOR`; its
replacement is `8.419003785 Hz` from the reconstructed-update-instant method.
The faulty `phase_age_ms`-decrease estimator undercounted fresh updates. The
corrected computation reconstructs each
update instant as `round(timestamp_s*1000)-phase_age_ms`, counts advancing
instants, and divides by the timestamp span.

The nine legacy CSVs used by the historical window path do not contain
`phase_age_ms` or a 0x0A13 freshness identity. Reconstructing
`ondevice_ai/adapters/mmwave_csv_adapter.py` produced 620 historical input
windows, but freshness for every one of those windows is unobservable from the
CSV evidence. A nominal telemetry cadence therefore cannot be treated as a
proven fresh-phase cadence.

## PR18 pilot consequence for capture tooling

The two PR18 pilot captures resolve the M-C0 alternatives in favour of (b):
the PR18-lineage capture tooling approaches the telemetry row cadence and does
not exhibit the extreme phase-age tail in the legacy long log.
`M-C0-PILOT-DESKWORK-001` measures corrected fresh cadence `9.988438535 Hz`
with `phase_age_ms` p95 `15 ms`; `M-C0-PILOT-STATIONARY-001` measures
`9.993330369 Hz` with p95 `15 ms`. The legacy p95 is `195627 ms`. The earlier
pilot values `3.679658492 Hz` and `3.518230325 Hz` are
`RETRACTED_FAULTY_ESTIMATOR`; their replacements are `9.988438535 Hz` and
`9.993330369 Hz`. The resulting (a) verdict is retracted because the
age-decrease estimator undercounted always-low age values.

Direct corrected window reconstruction found `4/6` valid 300-fresh windows in
DESKWORK and `5/6` in STATIONARY. These pilot results are recorded only under
`PR18_PILOT_CAPTURE` in
`datasets/mmwave/manifests/M-C0_correspondence_audit/m_c0_summary.json`; they are
not merged with legacy results.

Consequently, M-C1 may proceed with PR18-lineage capture tooling only after an
explicit protocol approval. Each session must pass a fresh-cadence and
300-fresh-window acceptance gate. The tooling must:

- record each source 0x0A13/phase update when received, with an update identity,
  source timestamp, sequence, and freshness provenance, rather than treating a
  periodic re-emission of the last stored phase as a new sample;
- count genuinely fresh source updates, not emitted telemetry rows, and fail
  closed unless a candidate window contains 300 independently identifiable
  fresh updates;
- prevent stale repeats, interpolation, or synthesis from increasing the fresh
  sample count; and
- reconstruct or directly identify source update instants per session and
  reject the session if no contract-eligible 300-fresh window is demonstrated.

This consequence does not choose a numeric `phase_age_ms` threshold, a
resampling method, an official distance, reference hardware, or sample size.
Those remain **UNDEFINED**. Existing hardware availability removes the previous
hardware blocker, but this draft does not approve or begin M-C1 capture.

## M-C1 readiness blockers, in priority order

1. **Select an independent respiratory reference device.** The selection is
   **UNDEFINED**. Without an independently measured, time-aligned respiratory
   reference, `semantic_correspondence` remains `UNDETERMINED` regardless of
   how completely or cleanly M-C1 is captured.
2. **Obtain explicit approval for the complete M-C1 protocol.** The approval
   has not been granted; status remains `PENDING_EXPLICIT_PROTOCOL_APPROVAL`.
3. **Define the reference-to-MR60 synchronization and provenance procedure.**
   It must support an auditable correspondence comparison without treating a
   paced-rpm cue as a label; the procedure remains **UNDEFINED**.
4. **Define the temporal acceptance details.** The official `phase_age_ms`
   threshold and resampling/interpolation method remain **UNDEFINED**.
5. **Define the capture design.** Official measurement distances and sample
   sizes remain **UNDEFINED**.

This prioritized list is a readiness note only. It neither selects a device
nor authorizes M-C1 to begin.

## M-C1 capture must guarantee

### 1. Fresh-phase update rate is measured per session

Every session must retain the raw freshness evidence needed to identify a
genuinely fresh phase update. The session report must include:

- telemetry row cadence;
- fresh-phase/0x0A13 update cadence measured independently;
- the exact fields and computation used to identify a fresh update; and
- an explicit status if the fresh cadence cannot be measured.

The row cadence must never be used as a substitute for fresh-phase cadence.
No assumed 10 Hz fresh-phase rate is acceptable.

### 2. `phase_age_ms` is logged and reported per session

Each session must preserve `phase_age_ms` (or an explicitly identified direct
freshness field) with timestamps and sequence information sufficient to audit
it. The session report must include the phase-age distribution:

- minimum;
- median;
- p95;
- maximum; and
- fraction over the selected reporting partition.

The M-C0 value of 30 seconds is only a reporting partition. A formal
`phase_age_ms` failure threshold remains **UNDEFINED** and is not set by this
draft.

### 3. Formal-evaluation eligibility requires one genuine window

A session is eligible for formal M-C1 evaluation only when it yields at least
one window containing `300` genuinely fresh samples. The freshness evidence
must support that claim; a row count, timestamp cadence, reset proxy, repeated
value, or interpolated sample does not by itself qualify.

The exact window overlap policy and any resampling policy remain unresolved and
must be decided and recorded before an approved M-C1 protocol is issued.

## Required per-session audit record

The capture record should preserve, at minimum, raw timestamp, sequence, phase,
phase-age/freshness field, distance/vitals fields, firmware/model identity,
session metadata, and file SHA-256. The derived report must cite the source
file and computation for every numeric claim. Missing freshness fields must be
reported as missing, not reconstructed silently from row cadence.

The following findings remain constraints for interpretation:

- the M-C0 decision is `BLOCKED_PENDING_SIGNAL_CORRESPONDENCE`;
- semantic correspondence is `UNDETERMINED`;
- temporal correspondence is `MEASURED_SUFFICIENT_FOR_PR18_PILOT_CAPTURE_ONLY`;
- valid windows are reported separately as `PR18_PILOT_CAPTURE=9` and
  `PRE_PR18_LEGACY_LOGS=27`, with no cross-group aggregate;
- the 620-window legacy path diverges at freshness provenance before
  `BPF_ZSCORE`; and
- the all-APNEA historical collapse is not assigned to BPF, z-score, INT8, or
  the model by this document.

## Still undefined and not authorized here

This draft intentionally does not define or authorize:

- a numeric `phase_age_ms` failure threshold;
- a resampling or interpolation method;
- official measurement distances;
- independent M-C1 reference hardware;
- M-C1 sample size; or
- any paced-rpm-to-label mapping.

The PR18-lineage capture hardware/tooling is available, so M-C1 is no longer
`BLOCKED_HARDWARE`. M-C1 remains `PENDING_EXPLICIT_PROTOCOL_APPROVAL`; this
document does not grant that approval. No new capture was performed for this
draft, and independent reference hardware remains **UNDEFINED**.
