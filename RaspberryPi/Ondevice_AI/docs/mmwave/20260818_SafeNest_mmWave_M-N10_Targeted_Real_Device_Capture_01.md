# SafeNest M-N10 — Targeted multi-subject real-MR60 capture

- Date: 2026-08-18
- Phase: **M-N10 protocol lock**. Human capture has **not** started.
- Protocol: `config/mmwave/m_n10_capture_protocol_lock.json`
- Status: `LOCKED_BEFORE_HUMAN_CAPTURE` / capture `CAPTURE_NOT_PERFORMED`
- Gate: **INCOMPLETE**
- `M_N11_AUTHORIZED = NO`

This document freezes the capture contract before any new participant is
measured. It is not a captured dataset, not a model-accuracy report, and not
device validation.

---

## 1. Remaining evidence gap after M-N9

M-N9 locked `MMWAVE_M_N9_FULL_INT8_V1` and showed public VAL INT8 parity.
It did **not** validate the model on real people.

After M-N9 the remaining gap is still:

```text
real MR60
+ multiple physical subjects
+ independent respiratory reference
+ development-unseen formal validation evidence
```

Existing Team MR60 evidence is one physical subject with no independent
respiratory ground truth. That cannot authorize M-N11.

---

## 2. Hardware / reference setup

Required capture chain:

1. MR60BHA2 raw telemetry, especially `0x0A13 breath_phase`, with
   `ts_monotonic_ms` and `phase_age_ms`.
2. An independent respiratory reference on a synchronizable clock.
3. Session identity: `subject_id`, `session_id`, `trial_id`, `boot_id`.

M-N9 Pi isolated smoke remains unverified. If the Raspberry Pi is the logger,
close that smoke with the exact INT8 SHA
`3b008af4be0facc4037c2afd3fe39292fb794208eb4370dbe6916b2d15aa38a4`
**before** human capture. If another verified raw logger is used, capture may
proceed, but the report must say `PI_SMOKE_REMAINS_UNVERIFIED`. This lock does
not invent a Pi PASS.

---

## 3. Independent-reference identity

Preferred: **Movesense chest accelerometer**, already the M-N4 / A4 source
(`MMWAVE_LABEL_MAPPING_PROFILE_001`, `scripts/mmwave_label_mapper.py`).

Forbidden as ground truth:

- MR60 `breath_rate_raw` or vendor respiration;
- paced-breathing cue alone;
- `human_detected_raw`;
- model prediction.

A paced cue may guide Condition B. It is not the label. M-N10 does not invent
new RR thresholds.

If this reference is not on the bench, stop with
`INDEPENDENT_RESPIRATORY_REFERENCE_NOT_AVAILABLE`. That is the current state.

---

## 4. New physical subject count

```text
target >= 8
hard minimum for M-N11 = 6
captured so far = 0
previous Team subject reused = NO
```

De-identified IDs only: `MN10-S001`, `MN10-S002`, … Names, phones, and student
IDs stay out of Git.

---

## 5. Subject partition

Frozen **before** any model prediction:

```text
rule:     MMWAVE_M_N10_SUBJECT_PARTITION_V1
seed:     20260818
unit:     SUBJECT
overlap:  0
DEV:      approximately 1/3  M_N10_DEVELOPMENT_REFERENCE
RESERVED: approximately 2/3  M_N11_FORMAL_VALIDATION_RESERVED
          and >= 4 when N >= 6
```

Examples: 6→2/4, 8→3/5, 9→3/6. Assignments are empty until subjects exist.
A reserved subject is never moved to DEV because the data is inconvenient.

---

## 6. Capture conditions

Per new subject, at least:

| Condition | Intent | Minimum usable |
|---|---|---:|
| A | quiet/rest, stationary | 120 s |
| B | elevated/faster breathing (cue or brief movement + recovery) | 120 s |
| C | repeat after leave/reposition or geometry reset | 120 s |

Intent is not the label. Optional short seated breath-pauses may be collected
safely; they are APNEA-proxy only if the frozen A4 mapper later agrees with
the independent reference. Do not force prolonged breath-holds. Do not
manufacture APNEA-proxy.

---

## 7. Synchronization

Preferred: same host / common clock. Otherwise an explicit sync marker on both
timelines, with wall time, monotonic time, and estimated alignment
uncertainty. Visual guess alignment is forbidden. Unverified sessions are
`REFERENCE_ALIGNMENT_UNVERIFIED` and excluded from M-N11 scoring.

---

## 8. Raw evidence lineage

Local raw root (not forced into Git): `datasets/mmwave/raw/m_n10/`.

Git keeps protocol, manifests, SHA-256, and provenance. Every raw file must
record filename, subject/session, size, SHA-256, clocks, device IDs, and
firmware/config identity. No in-place raw edits. Derived files cite the raw
SHA.

No raw files exist yet.

---

## 9. Canonical eligibility

M-N10 may count eligible vs invalid 30 s windows under the frozen M-N4
contract (timing, gaps, boots, MAD). It may not inspect neural correctness.
Window later must not cross subject, session, boot, or large-gap boundaries.
Nothing to count until capture exists.

---

## 10. Class / reference coverage

Classes remain:

```text
0 NORMAL
1 RAPID_OR_ABNORMAL
2 APNEA-proxy
```

Coverage will be structural counts from the independent reference after
capture. Current counts are all unknown / zero. Presence telemetry is
retained; absence is never APNEA ground truth. `PRESENCE_GATE_REQUIRED = YES`
is inherited, not redesigned.

---

## 11. Reserved-access discipline

For `M_N11_FORMAL_VALIDATION_RESERVED`:

```text
M-N10 FLOAT inference = 0
M-N10 INT8 inference = 0
predictions inspected = NO
```

The protocol lock and helper script refuse reserved inference. Development
reference subjects are also not used here for M-N8-style adaptation.

---

## 12. Is M-N11 authorized?

**No.**

```text
M-N10 gate:                 INCOMPLETE
M_N11_AUTHORIZED:           NO
NEXT_RECOMMENDED_PHASE:     M-N10_CAPTURE_COMPLETION
```

Missing: independent reference on the bench, >=6 new physical subjects,
>=4 reserved subjects, verified alignment, SHA-locked raw MR60 and reference
payloads, and structurally eligible canonical windows.

M-N11 must not start until those exist. This protocol lock is the analogue of
the M-N6 pre-heldout lock: the exam paper is defined before anyone sits it.

## Files

- `config/mmwave/m_n10_capture_protocol_lock.json`
- `datasets/mmwave/manifests/m_n10_subject_partition.json`
- `datasets/mmwave/manifests/m_n10_capture_manifest.json`
- `scripts/mmwave_m_n10_capture_protocol.py`
- `tests/test_mmwave_m_n10_capture_protocol.py`
