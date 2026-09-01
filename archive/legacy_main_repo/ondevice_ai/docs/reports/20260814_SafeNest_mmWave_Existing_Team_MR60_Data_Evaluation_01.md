# Existing Team MR60 Measurement Evaluation

Assessment date: 2026-08-14

This report is a human-readable evidence assessment of physical MR60BHA2
measurements that already exist in the team repository. It is written for team
members who need to know what was measured, what is actually usable, and what
must not be claimed yet.

This document does not run the frozen Phase-B model, does not collect new
recordings, and does not retrain anything. Numerical claims were recomputed from
the live team `main` tree unless a stored analysis file is cited.

Evidence identity used for this assessment:

- Team repository: `jinsu1011/safenest-embedded-competition`
- Team `main` SHA: `fdf34b804f35e5868356f0ed6f804a248aa69131`
- Standalone `main` SHA at original report branch creation: `4b31808b31444fa502250e24a42ba9e843964b2f`
- Standalone `main` SHA at the ML-dataset / Korean-guide enhancement: `07f1cdefa0775c6525101bb83546b89acc5e3c13`

A Korean team-facing companion, not a literal translation, is
`docs/reports/20260814_SafeNest_mmWave_Team_MR60_Data_Evaluation_KR_01.md`.

Paths below are repository-relative POSIX paths in the team tree unless a
standalone Phase-B path is explicitly marked.

---

## 1. Executive Summary

The team already has **valuable real MR60BHA2 measurements**. They are much more
useful than screenshots or manually copied sensor values. Multiple sessions keep
real timestamps, expose both a phase-like waveform and a vendor respiration-rate
field, and preserve failed trials instead of deleting them.

They are **not** yet a formal device-domain validation set for the frozen
standalone mmWave model, and they are **not** yet a supervised
`NORMAL` / `RAPID_OR_ABNORMAL` / `APNEA-proxy` retraining dataset. Section 15
explains that distinction. The data are still valuable for M-C0.

Current classification, based on live evidence:

| Question | Assessment |
| --- | --- |
| Existing team MR60 data | VALUABLE |
| Usable for device-domain exploration | YES |
| Telemetry / log-row cadence | VERIFIED ≈ 9.99 Hz for multiple sessions |
| Fresh MR60 phase-frame cadence | NOT YET ESTABLISHED / PARTIAL |
| 30 s / 300 telemetry-row construction | YES |
| 30 s / 300 fresh `breath_phase` sample correspondence | NOT YET ESTABLISHED |
| Phase-B temporal correspondence | NOT YET ESTABLISHED |
| Signal-field lineage | GOOD |
| Vendor respiration-rate characterization | USEFUL |
| Failure-case evidence | USEFUL |
| Multi-subject validation | INSUFFICIENT |
| Independent physiological respiration reference | ABSENT |
| Phase-B signal-semantic correspondence | NOT YET ESTABLISHED |
| Supervised Phase-B target `y` | NOT YET ESTABLISHED |
| Immediate supervised retraining | NOT AUTHORIZED |
| Formal device-domain model validation | NOT YET AUTHORIZED |

The most important technical distinctions in this dataset are:

```text
breath_phase     ≠  breath_rate_raw
waveform-like    ≠  vendor respiration-rate number

JSONL/CSV row cadence ≈ 10 Hz
≠
fresh 0x0A13 breath_phase update cadence ≈ 10 Hz
```

The historical “about 20 rpm” observation is currently associated with the
**vendor respiration-rate field**, not with a demonstrated AI classifier output
and not with a proven 20 rpm frequency of the phase-like waveform itself.

Recommended next use of this data:

```text
existing team measurements
        ↓
M-C0 forensic / correspondence audit
        ↓
separate telemetry cadence vs fresh 0x0A13 cadence vs stale/repeated breath_phase
        ↓
decide whether breath_phase can defensibly build the frozen Phase-B input
        ↓
optional exploratory legacy inference only if correspondence is established
        ↓
independent review
        ↓
future protocol-controlled M-C1 measurements
        ↓
formal frozen-candidate M-C2 device-domain evaluation
```

Do not retrain, replace preprocessing, or start M-D from this report.

---

## 2. What Data the Team Already Has

The physical evidence is not a single file. It is a stack of timestamped logs,
CSV exports, manifests, and later analysis.

### 2.1 Structured delivery batch used for AI handoff

Primary bundle:

```text
devices/mmwave/firmware/csv/2026-07-26_han_junwoo_delivery_v2/
```

That folder contains:

- session CSV exports with SHA-256 in `manifest.json`
- copied original JSONL logs under `original_jsonl/`
- interpretation flags (`preferred_validation`, `failure_case`, `lock_loss_case`)
- delivery notes in `DELIVERY_NOTES.md`

Export contract, from `devices/mmwave/firmware/export_mmwave_csv.py`:

- `resp_phase` stores ESP `breath_phase` as-is
- no ×100 scaling, no Z-score, no smoothing, no resampling
- no synthetic `resp_phase` invented when presence is 0
- `subject_id` is hardcoded as `S001`

Delivery sessions:

| Session ID | Role in the bundle | Source log |
| --- | --- | --- |
| `S001_NORMAL_D06` | occupied distance, preferred | `logs/matrix/2026-07-25_occupied_d06_v1_360s.jsonl` |
| `S001_NORMAL_D09` | occupied distance, preferred | `logs/baseline/2026-07-25_occupied_d09_v1_360s.jsonl` |
| `S001_NORMAL_D12` | occupied distance, range-limit / presence drop | `logs/matrix/2026-07-25_occupied_d12_v1_360s.jsonl` |
| `S001_NORMAL_D15` | occupied distance, lock-loss / vitals freeze | `logs/matrix/2026-07-25_occupied_d15_v1_360s.jsonl` |
| `S001_BREATH_PACED_12_01` | invalid 12 rpm attempt | `logs/breath/2026-07-25_breath_paced_12rpm.jsonl` |
| `S001_BREATH_PACED_12_02` | valid 12 rpm | `logs/breath/2026-07-28_breath_paced_12rpm_explicit_v2_attempt03.jsonl` |
| `S001_BREATH_PACED_15_03` | 15 rpm delivery session | `logs/breath/2026-07-26_breath_paced_15rpm.jsonl` |
| `S001_BREATH_PACED_20_04` | 20 rpm shallow / weak | `logs/breath/2026-07-26_breath_paced_20rpm.jsonl` |
| `S001_BREATH_PACED_20_05` | 20 rpm deep / stronger | `logs/breath/2026-07-26_breath_paced_20rpm_deep.jsonl` |

### 2.2 Additional physical logs beyond the CSV bundle

The firmware log tree contains more than the delivery CSV set, including empty
room, entry/exit, diagnostics, Apple Watch heart-rate comparison, and a
schema-1.2 occupied ~31-minute recording:

```text
devices/mmwave/firmware/logs/final/2026-08-01_occupied_d09_v120_31min_attempt02.jsonl
```

A later firmware/Python reproducibility check was recorded in commit
`3b44e505490811b640ed9200b2fd6ed27846edc3` and
`docs/operations/PROJECT_PROGRESS.md`.

### 2.3 What Git history does and does not prove

Team PRs `#2` and `#7` reorganized architecture/docs paths. They are not the
original act of creating the physical measurements. The logs themselves are
timestamped device captures that later moved with the tree, including commit
`38274c084544af6f26b1377e593b012628a7eb05`.

---

## 3. What Was Done Well in the Existing Measurements

These strengths are supported by files, not by courtesy.

**Real timestamps were preserved.** JSONL records store `ts_monotonic_ms`. CSV
exports rebase that clock to session start as `timestamp_s` without inventing a
uniform grid. Telemetry/log-row cadence can therefore be measured instead of
assumed. That row cadence is not, by itself, a fresh `0x0A13` phase-frame
cadence.

**Both signal families were retained.** The logs keep `breath_phase` and
`breath_rate_raw` side by side. That is what makes the later vendor-vs-phase
comparison possible.

**Several controlled breathing rates were attempted.** 12, 15, and 20 rpm cues
exist, and the team re-measured 12 rpm after the first attempt failed.

**Distance conditions were attempted.** Occupied recordings exist at intended
0.6 / 0.9 / 1.2 / 1.5 m (`D06`–`D15`).

**Failed sessions were kept.** The invalid 12 rpm attempt, the shallow 20 rpm
attempt, and the D15 lock-loss session were not deleted. The delivery manifest
labels them instead of silently treating them as success.

**Checksums and copies exist.** `manifest.json` records origin SHA-256, copied
JSONL SHA-256, and CSV SHA-256.

**Export rules were conservative.** The exporter does not normalize, smooth,
resample, or synthesize no-presence phase. That is the right default for later
forensic work.

**Long-duration behavior was investigated.** The schema-1.2 occupied log and the
2026-08-03 C++/Python replay are useful engineering evidence, even though they
are not model-accuracy evidence.

**Vendor rate was not blindly trusted.** Team notes already warn that
`breath_rate_raw` bias is not constant. That warning is consistent with the
recomputed numbers below.

---

## 4. What the MR60 Fields Actually Mean

Parser authority is `devices/mmwave/firmware/src/main.cpp`.

### 4.1 `breath_phase` — lowest currently exposed respiration phase-like signal

Firmware frame type:

```text
0x0A13  →  totalPhase, breathPhase, heartPhase
```

The ESP JSON field `breath_phase` is the `breathPhase` float from that frame.
CSV column `resp_phase` is that same value, unmodified.

This is currently the best candidate for comparison with the standalone
respiration-waveform AI input. It is **not** confirmed true radar ADC, IQ, or
raw range-FFT data. No ADC/IQ/range-bin arrays appear in the inspected JSONL
keys. The honest description is:

```text
MR60-exposed phase-like intermediate signal
```

### 4.2 `breath_rate_raw` — vendor-derived respiration rate

Firmware frame type:

```text
0x0A14  →  breathRaw
```

This is a vendor respiration-rate output, typically in rpm-like units. It is
**not** the waveform used by the standalone Phase-B model. Schema 1.2 logs also
carry firmware-side derived fields such as `breath_rate_filtered` and
`breath_filtered_valid`; those are ESP post-processing of `breath_phase`, still
not the frozen standalone AI input.

Firmware itself marks `breath_rate_raw_trusted: false` in schema 1.2 telemetry.

### 4.3 Distance, presence, and other fields

| Field | Meaning for this assessment |
| --- | --- |
| `distance_cm_raw` | vendor distance sample; useful for geometry/lock diagnostics |
| `human_detected_raw` | vendor presence flag; not a respiration waveform |
| `heart_rate_raw` / `heart_phase` | not a validated heart-rate or respiration reference |
| `total_phase` | companion phase channel from `0x0A13`; not the AI input contract |
| `ts_monotonic_ms` | ESP monotonic timestamp of the telemetry row, not proof that `breath_phase` was freshly updated in that row |
| `phase_age_ms` | age of the last `0x0A13` phase-frame update relative to the telemetry emit time |

Apple Watch logs exist for exploratory heart-rate comparison. They are not an
independent respiration belt, spirometer, or chest-belt reference.
`devices/mmwave/firmware/analysis/breath/2026-07-28_vitals_measured_vs_reference.json`
states `heart_reference: null` and `breath_reference: "paced cue target"`.

---

## 5. Actual Timing / Sampling Quality

Two clocks must be kept apart.

Firmware emits JSON telemetry on a timer, not on every radar phase frame.
`devices/mmwave/firmware/include/mmwave_config.h` sets
`kTelemetryIntervalMs = 100`. `devices/mmwave/firmware/src/main.cpp` `loop()`
calls `emitTelemetry()` when that interval elapses. `emitTelemetry()` writes
the **last stored** `breathPhase`. A fresh `0x0A13` frame is the only path that
updates `breathPhase` and `phasesUpdatedMs`. `phase_age_ms` exists specifically
to record how old that last phase-frame update is.

```text
TELEMETRY / LOG ROW CADENCE:
VERIFIED ≈ 9.99 Hz for multiple sessions

FRESH MR60 PHASE-FRAME CADENCE:
NOT YET ESTABLISHED / PARTIAL

30 s / 300 TELEMETRY ROW CONSTRUCTION:
YES

30 s / 300 FRESH breath_phase SAMPLE CORRESPONDENCE:
NOT YET ESTABLISHED

Phase-B temporal correspondence:
NOT YET ESTABLISHED
```

```text
JSONL/CSV row cadence ≈ 10 Hz
≠
fresh 0x0A13 breath_phase update cadence ≈ 10 Hz
```

### 5.1 Telemetry / log-row cadence (verified)

Row cadence was recomputed from exported CSV `timestamp_s` as
`1 / mean(diff(timestamp_s))`. The values match
`devices/mmwave/firmware/csv/2026-07-26_han_junwoo_delivery_v2/manifest.json`
diagnostics.

| Session | Records | Duration (s) | Telemetry row cadence (Hz) | Max row gap (ms) |
| --- | ---: | ---: | ---: | ---: |
| `S001_NORMAL_D06` | 2998 | 299.851 | 9.994964 | 102 |
| `S001_NORMAL_D09` | 2998 | 299.816 | 9.996131 | 101 |
| `S001_NORMAL_D12` | 2998 | 299.826 | 9.995798 | 102 |
| `S001_NORMAL_D15` | 2999 | 299.849 | 9.998366 | 102 |
| `S001_BREATH_PACED_12_02` | 1774 | 177.381 | 9.995434 | 101 |
| `S001_BREATH_PACED_15_03` | 1779 | 177.905 | 9.994098 | 103 |
| `S001_BREATH_PACED_20_04` | 1784 | 178.403 | 9.994227 | 103 |
| `S001_BREATH_PACED_20_05` | 1784 | 178.425 | 9.992994 | 103 |

No timestamp duplicates or backwards steps were found in those exported
windows. Original JSONL copies of the same sessions also sit near 9.99 Hz, with
selected maximum **row** gaps of 101–103 ms.

The logging/telemetry stream is close to 10 Hz for multiple sessions. This
establishes row-level timing quality, but does not yet prove that each row
contains a fresh MR60 phase measurement or that the fresh `breath_phase`
cadence matches the Phase-B 10 Hz signal contract.

### 5.2 Fresh `0x0A13` phase-frame cadence (not yet established)

A 30-second window containing approximately 300 telemetry rows can be cut from
these logs; whether those rows represent 300 fresh phase observations remains
an M-C0 correspondence question.

The same report already contains a direct counter-example. The schema-1.2
occupied log in §9 has telemetry cadence 9.986 Hz and max row gap 103 ms, while
`phase_age_ms` reaches 288,530 ms and 2,585 packets have `phase_age_ms > 30 s`.
The log can keep printing at ~10 Hz while `breath_phase` is a repeated stale
value.

M-C0 must therefore measure, separately:

```text
telemetry cadence
vs
fresh 0x0A13 phase-frame cadence
vs
stale/repeated breath_phase behavior
```

Row-cadence match is also not signal-semantic match:

```text
matching telemetry cadence  ≠  matching Phase-B signal semantics
matching telemetry cadence  ≠  fresh breath_phase sampling
```

---

## 6. Paced Breathing Results

Paced cues are controlled exploratory references. They are not a respiration
belt. The numbers below were recomputed with the same cue-window + FFT method
used by `devices/mmwave/firmware/analyze_paced_breathing.py`, and they match the
stored summaries where those summaries exist.

### 6.1 Valid 12 rpm

Source: `logs/breath/2026-07-28_breath_paced_12rpm_explicit_v2_attempt03.jsonl`

Stored summary:
`analysis/breath/2026-07-28_breath_paced_12rpm_explicit_v2_attempt03_summary.json`

| Quantity | Value |
| --- | ---: |
| Cue target | 12 rpm |
| Inhale-cue interval | 5.000 s → 12.00 rpm cue |
| `breath_phase` dominant rate | 12.34 rpm |
| Vendor `breath_rate_raw` mean | 14.52 rpm |
| Vendor median | 14.0 rpm |
| Presence true ratio | 1.00 |
| Phase std | 0.377 |

The phase-like waveform follows the 12 rpm cue more closely than the vendor
rate field. This is still one subject, one geometry, and a paced cue rather
than independent physiological ground truth.

### 6.2 15 rpm

Two 15 rpm recordings matter, and they are not identical.

**Delivery preferred session**
`logs/breath/2026-07-26_breath_paced_15rpm.jsonl`
(`S001_BREATH_PACED_15_03`):

| Quantity | Value |
| --- | ---: |
| Cue target | 15 rpm |
| `breath_phase` dominant rate | 15.00 rpm |
| Vendor mean | 18.04 rpm |
| Vendor median | 19.0 rpm |

**Later explicit 15 rpm session used in the calibration comparison**
`logs/breath/2026-07-28_breath_paced_15rpm_explicit_full_v3.jsonl`

Stored in
`analysis/breath/2026-07-28_breath_paced_15rpm_explicit_full_v3_summary.json`
and
`analysis/breath/2026-07-28_breath_calibration_12_15_20_comparison.json`:

| Quantity | Value |
| --- | ---: |
| Cue target | 15 rpm |
| `breath_phase` dominant rate | 15.01 rpm |
| Vendor mean | 18.80 rpm |
| Vendor median | 19.0 rpm |
| Vendor ±2 rpm hit rate vs 15 rpm cue | 0.112 |

In both 15 rpm sessions the phase-like waveform stays near 15 rpm, while the
vendor field clusters near 19 rpm.

### 6.3 20 rpm

**Deep / stronger delivery session**
`logs/breath/2026-07-26_breath_paced_20rpm_deep.jsonl`
(`S001_BREATH_PACED_20_05`):

| Quantity | Value |
| --- | ---: |
| Cue target | 20 rpm |
| `breath_phase` dominant rate | 20.00 rpm |
| Vendor mean | 23.31 rpm |
| Vendor median | 23.0 rpm |
| Phase std | 0.501 |
| Presence | 1.00 |

**Later explicit 20 rpm session in the calibration JSON**
`logs/breath/2026-07-28_breath_paced_20rpm_explicit_full_v2.jsonl`:

| Quantity | Value |
| --- | ---: |
| `breath_phase` dominant rate | 20.01 rpm |
| Vendor mean | 19.40 rpm |
| Vendor median | 22.0 rpm |
| Vendor std | 6.39 rpm |

The vendor offset is **not the same** at 12, 15, and 20 rpm, and it is not the
same across the 2026-07-26 and 2026-07-28 20 rpm recordings. No universal
`+N rpm` correction is justified.

Interpretation that is supported:

> In these paced sessions, the MR60-exposed phase-like waveform tracked the
> cue periodicity better than the vendor respiration-rate field.

Interpretation that is **not** supported:

```text
MR60 always has a +N rpm error
```

---

## 7. What the “~20 rpm” Observation Actually Means

The short answer: the currently documented ~19–20 rpm behavior is primarily
**vendor respiration-estimator behavior**, not an AI prediction and not a proof
that `breath_phase` itself has a 20 rpm frequency.

The cleanest documented contrast is the 2026-07-28 explicit 15 rpm trial:

```text
paced cue                  ≈ 15 rpm
breath_phase estimate      ≈ 15.01 rpm
vendor breath_rate_raw     mean 18.80 / median 19.0 rpm
```

The 2026-07-26 delivery 15 rpm session shows the same direction:
phase ≈ 15.00 rpm, vendor median 19.0 rpm.

Therefore the current interpretation is:

```text
vendor respiration estimator behavior / bias evidence
```

not:

```text
the AI predicts 20 rpm
```

and not:

```text
the radar waveform itself necessarily has a 20 rpm frequency
```

Cause remains exploratory. No universal bias correction has been established.
Condition dependence is already visible: 12 rpm vendor median was 14, 15 rpm
vendor median was 19, and 20 rpm vendor medians were 22 or 23 depending on the
session.

Do not convert this into a scaler, offset, or retraining ticket.

---

## 8. Useful Failure Cases

Failed recordings are QA evidence. They should be kept and labeled, not used as
clean reference.

### 8.1 Incorrect 12 rpm attempt

Source: `logs/breath/2026-07-25_breath_paced_12rpm.jsonl`
(`S001_BREATH_PACED_12_01`)

The filename and cue target say 12 rpm. The chest motion did not.

Independent reproduction with
`devices/mmwave/firmware/analysis_tools/phase_any_session.py`:

```text
autocorrelation of breath_phase  →  6.06 rpm
30 s sliding median              →  6.00 rpm
vendor breath_rate_raw mean      →  6.05 rpm
vendor median                    →  4.00 rpm
```

Cue inhale intervals in that file average 5.09 s, so the **metronome/cue** was
still near 12 rpm. The subject appears to have used about 10 seconds per breath,
producing ~6 rpm chest motion. Delivery notes describe this as a half-breath
instruction accident.

This is **not** a valid 12 rpm reference. It is useful as
`measurement-protocol failure evidence`: future reference conditions must record
the actual performed rate, not only the intended label.

### 8.2 D15 lock-loss / vitals freeze

Source: `logs/matrix/2026-07-25_occupied_d15_v1_360s.jsonl`
CSV window `S001_NORMAL_D15` (60 s warmup skipped, 2999 records).

Do **not** repeat the older claim `distance std ≈ 0`.

Recomputed from `distance_cm_raw` in the exported after-warmup window:

| Quantity | Value |
| --- | ---: |
| Distance unique values | 172.20, 177.94, 183.68 cm |
| Distance sample std | 2.94 cm |
| Distance population std | 2.94 cm |
| Unique `breath_phase` | 1 (`-0.01`) |
| Unique `breath_rate_raw` | 1 (`15.0`) |
| Unique `heart_rate_raw` | 1 (`87.0`) |
| `breath_phase` std | 0.0 |
| Presence true | 88.0% |

Lock-loss / vitals freeze **is** supported: phase and vendor vitals are stuck.
Low numeric variance of distance is **not** the right description. Distance
still hops among three quantized values. The difference:

```text
signal / target lock failure   ≠   low numeric variance of distance
```

Team docs that still say “D15 distance std=0” are describing the freeze
signature loosely. The measured distance sample standard deviation is ~2.94 cm.

### 8.3 Shallow vs deep 20 rpm

| Session | Phase std | Phase-dominant rpm | Vendor median | Presence |
| --- | ---: | ---: | ---: | ---: |
| Shallow `S001_BREATH_PACED_20_04` | 0.113 | 20.00 | 19.0 | 97.3% CSV / 96.4% cue window |
| Deep `S001_BREATH_PACED_20_05` | 0.501 | 20.00 | 23.0 | 100% |

The weak session still has a ~20 rpm phase periodicity, but much smaller
amplitude. Team notes used this contrast as evidence for an amplitude gate
(`breath_phase` std < 0.2 → do not emit a trusted rate). For SafeNest AI work,
the lesson is:

- detectability depends on breathing effort / chest displacement
- shallow breathing must not be treated as a clean reference/success condition
  unless it is explicitly pre-registered as a robustness condition with
  separate QA criteria
- low-amplitude sessions remain useful failure/QA evidence when labeled as such

---

## 9. Long-Duration / Reproducibility Evidence

Occupied schema-1.2 log:

```text
devices/mmwave/firmware/logs/final/2026-08-01_occupied_d09_v120_31min_attempt02.jsonl
SHA-256 7f9e9ac65377c6dc217af92f9dee2401b6162540e2245fce97acf2ed49368a34
```

Independent counts from the live file:

| Quantity | Value |
| --- | --- |
| Schema | 1.2 for all 18,574 sensor records |
| Duration | 1,859.84 s ≈ 31.00 min |
| Telemetry / log-row cadence | 9.986 Hz |
| Max timestamp row gap | 103 ms |
| Firmware string | `safenest-mr60-esp/1.2.0` |
| `phase_age_ms` maximum | 288,530 ms |
| Packets with `phase_age_ms` > 30 s | 2,585 |

This is the same telemetry-versus-fresh-phase distinction as §5. The log keeps
emitting rows near 10 Hz, but `breath_phase` can remain a repeated last value
for minutes. `phase_age_ms` is the field that records that staleness. Row
cadence here must not be read as a 10 Hz stream of fresh `0x0A13` samples.

Final-validation manifest assessment:
`PRESENCE_PASS_BREATH_CONTINUITY_FAIL`
(`analysis/final/2026-08-01_mr60_final_validation_manifest.json`).

C++/Python replay, commit `3b44e505490811b640ed9200b2fd6ed27846edc3`,
tool `devices/mmwave/firmware/analysis_tools/r1_fw_python_equivalence.py`,
written up in `docs/operations/PROJECT_PROGRESS.md`:

| Comparison | Recorded result |
| --- | --- |
| `breath_filtered_valid` gate mismatch | 51 / 18,276 = 0.279% |
| Residual mismatches | attributed to replay warmup, late phase dropout, and 2-decimal `breath_phase` quantization |

This is useful as:

- long-duration logging/stability evidence
- firmware/Python reproducibility evidence
- phase-dropout / stale-window evidence
- quantization-behavior evidence

This is **not** frozen-model accuracy evidence. Presence staying high while
breath continuity fails is a device-domain warning, not an AI F1 score.

---

## 10. Current Limitations

These limitations do not make the data useless. They cap the claim level.

**Single identifiable participant.** Delivery CSVs contain only `subject_id=S001`.
The exporter hardcodes `DEFAULT_SUBJECT = "S001"`. Multiple files are not
multiple people.

**No independent respiration reference.** No respiration belt, spirometer, or
validated chest-belt waveform is present in the inspected MR60 evidence.
Paced cues are the breathing reference. That is weaker than a physiological
sensor.

**Some trials were incorrectly executed or weak.** The 6.06 rpm “12 rpm” file,
shallow 20 rpm, D12 presence drop, and D15 vitals freeze are examples.

**Geometry/posture metadata is incomplete for formal reuse.** Intended distances
are recorded, and median `distance_cm_raw` can be computed, but a frozen M-C
protocol with posture, orientation, clothing, and operator notes was not the
collection contract for these legacy captures.

**True radar ADC/IQ/range-bin raw is not present or established in the
inspected team evidence.** Inspected JSONL keys contain no ADC, IQ, or
range-bin arrays. The lowest currently exposed respiration-related channel in
those logs is still an MR60-exported phase-like intermediate signal. That is a
statement about this evidence set, not a claim that the MR60 hardware can never
expose a lower-level radar representation.

**Vendor RPM cannot substitute for the AI waveform.** Using `breath_rate_raw` as
if it were Phase-B input would be a category error.

**Phase-B temporal and signal-semantic correspondence are not yet proven.**
Verified ~9.99 Hz telemetry/log-row cadence is not fresh `0x0A13` sampling and
is not correspondence with the Phase-B 10 Hz respiration-series contract.

**Legacy measurements were not collected under a pre-frozen M-C protocol.**
They are forensic inputs, not a pre-registered `FORMAL_DEVICE_VALIDATION_SET`.

**Amplitude / domain scale is unresolved.** Team notes already flag that ESP
`breath_phase` std is often ~0.02–0.5, while standalone training `resp_phase`
std is much larger. That is a correspondence question for M-C0, not a reason to
quietly rescale and retrain.

---

## 11. What We Can Use the Existing Data For Right Now

Appropriate uses:

- M-C0 forensic inventory of fields, timestamps, telemetry cadence, `phase_age_ms`, and quality
- distinguishing `breath_phase` from `breath_rate_raw`
- distinguishing telemetry-row cadence from fresh `0x0A13` phase-frame cadence
- characterizing vendor rate behavior under paced cues
- documenting lock-loss, stale phase, low-amplitude, and protocol-failure modes
- checking whether 30-second windows of ~300 telemetry rows are constructable
- planning M-C1 protocol so the next capture does not repeat known failure modes

The data are valuable **because** they are real, timestamped, and annotated with
known defects.

---

## 12. What We Must NOT Claim From It

Do not claim any of the following from the current evidence:

- `MR60 AI accuracy = X%` or `model F1 = X` on real MR60
- the frozen Phase-B model is validated on the team sensor
- deployment-ready or Raspberry Pi performance from these logs
- clinical apnea detection
- `breath_phase` is proven true radar ADC/IQ/rFFT
- 300 telemetry rows are automatically 300 fresh phase observations or a valid Phase-B input
- a ~9.99 Hz log-row cadence is already Phase-B temporal correspondence
- a universal vendor rpm offset exists
- D15 proves “distance std ≈ 0”
- the invalid 12 rpm file is a 12 rpm reference
- multiple JSONL files imply multiple subjects
- Apple Watch heart-rate comparison is a respiration ground truth

Standalone Phase-B offline numbers (accuracy ~0.56, macro F1 ~0.495, and the
locked class-wise recalls) remain **offline public-dataset results**. They must
not be rewritten as MR60 device-domain performance.

---

## 13. What the Next Controlled Measurement Must Improve

If M-C0 finds that `breath_phase` can defensibly construct the frozen input,
future M-C1 capture should improve the following. This report does not start
that capture.

- more than one independently identifiable participant
- independent respiration reference, or an explicit statement that paced cue
  remains the only reference and therefore limits the claim
- pre-registered distance, posture, orientation, clothing, and operator notes
- explicit recording of intended vs actually performed breathing rate
- keep failed sessions, but separate them from success references before any
  evaluation
- shallow breathing must not be treated as a clean reference/success condition
  unless it is explicitly pre-registered as a robustness condition with
  separate QA criteria
- continue storing raw `breath_phase` without smoothing or synthetic fill
- continue storing vendor `breath_rate_raw` for comparison, without using it as
  the AI waveform
- hardware availability is a prerequisite for M-C1, not a reason to skip M-C0
  on the logs that already exist

---

## 14. Recommended Next Step

Use the existing measurements as **M-C0 forensic evidence**, then stop until
correspondence is reviewed.

```text
Existing team measurements
        ↓
M-C0 forensic / device-domain correspondence audit
        ↓
separate telemetry cadence vs fresh 0x0A13 cadence vs stale/repeated breath_phase
        ↓
determine whether breath_phase can defensibly construct the frozen Phase-B input
        ↓
optional exploratory legacy inference if correspondence is established
        ↓
independent review
        ↓
future protocol-controlled M-C1 measurements
        ↓
formal frozen-candidate M-C2 device-domain evaluation
```

If correspondence cannot be established, a scientifically valid M-C0 result is
still:

```text
telemetry cadence              = YES for multiple sessions
fresh 0x0A13 phase cadence     = UNKNOWN / PARTIAL
signal semantics               = UNKNOWN
inference                      BLOCKED
```

That outcome would document a measured device-domain gap. It would not by itself
authorize M-D retraining, scaler replacement, architecture change, or merging
these logs into TRAIN.

---

## 15. Why the Existing Team Data Is Not Yet a Model-Training / Formal Validation Dataset

This section answers a communication gap that the earlier sections leave
implicit: the legacy MR60 logs are valuable sensor evidence, but they are not
the same kind of object as the Phase-A/B public development dataset.

```text
original Phase-A/B data
= input X + sufficiently defined target y
→ supervised model training/evaluation possible

current team MR60 legacy data
= useful input-side evidence X
+ incomplete / not-established Phase-B target y
→ M-C0 device-domain analysis first
→ not immediate supervised retraining
→ not formal Accuracy / F1 / Recall as MR60 model-performance evidence
```

### 15.1 What the original Phase-A/B dataset had

The standalone public mmWave archive used in Phase A/B was not an unlabeled
waveform dump. A0 inventoried 110 subjects and 440 recordings. A4 mapped source
experimental conditions, voluntary non-breathing annotations, and Movesense
chest-accelerometer reference respiration rates onto SafeNest classes. A5 then
froze a subject-level split so that every recording and window from one subject
stays in exactly one of TRAIN / VALIDATION / LOCKED_TEST.

Authoritative standalone paths:

- A4 report: `docs/reports/20260808_Antigravity_A4_Annotation_Label_Mapping_Pilot_01.md`
- A4 profile: `datasets/mmwave/manifests/a4_label_pilot/label_mapping_profile.json`
  (`MMWAVE_LABEL_MAPPING_PROFILE_001`)
- A5 report: `docs/reports/20260808_Antigravity_A5_Subject_Split_Provenance_01.md`
- A5 split: `datasets/mmwave/splits/mmwave_real_subject_split_v1.json`
- M-B12 frozen candidate:
  `docs/reports/20260813_Cursor_M-B12_mmWave_Phase_B_Offline_Final_Report_01.md`

Conceptually each canonical window could be treated as:

```text
radar-related signal
+
subject identity / grouping evidence
+
experimental condition
+
supervised class semantics
```

which allowed labels:

```text
NORMAL
RAPID_OR_ABNORMAL
APNEA   (SafeNest proxy only)
```

A4 semantics that matter for later protocol design, from
`MMWAVE_LABEL_MAPPING_PROFILE_001`:

- `NORMAL`: rest-condition proxy and/or Movesense chest-ACC reference rate in
  `[10.0, 25.0)` bpm, with zero non-breathing overlap
- `RAPID_OR_ABNORMAL`: Movesense reference rate `>= 25.0` bpm, or bradypnea
  `< 10.0` bpm; the profile requires an independent respiration-rate reference
- `APNEA`: `DERIVED` from `>= 6.0` s overlap with a voluntary non-breathing
  annotation inside a 30 s window

Provenance of `25.0` bpm: this number is frozen Phase-A public-dataset label
semantics, not a newly invented MR60 rule. It is
`rapid_or_abnormal_policy.rapid_min_rr_bpm` in
`datasets/mmwave/manifests/a4_label_pilot/label_mapping_profile.json`
(`MMWAVE_LABEL_MAPPING_PROFILE_001`), the default in
`scripts/mmwave_label_mapper.py`, and the profile loaded by
`scripts/validate_mmwave_label_pilot.py`. The same policy requires an
independent respiration-rate reference (`reference_sensor: MOVESENSE_CHEST_ACC`).
It is a threshold on Movesense chest-accelerometer reference RR in the public
archive, not on paced metronome cues and not on MR60 `breath_rate_raw`.

```text
25 bpm is frozen evidence of current Phase-A public-dataset label semantics.
It is NOT an automatic labeling threshold for future MR60 M-C1 data.

Phase-A RAPID was defined as Movesense reference RR >= 25.0 bpm
≠
future MR60: 25 bpm or 20 rpm cue automatically means RAPID
```

M-C1 must define its own class mapping before formal evaluation or training.
Copying `25.0` onto team MR60 sessions without that protocol would be a
category error.

`APNEA` remains an experimental apnea-like / voluntary breath-hold **proxy**.
It is not clinical sleep-apnea diagnosis. `AGENTS.md` and the A4 profile both
forbid that claim (`clinical_apnea_claimed: false`).

A5 split counts: 77 TRAIN / 17 VALIDATION / 16 LOCKED_TEST subjects. Cross-split
subject, recording, and window overlap is 0. That isolation is why later
offline scoring could be interpreted as subject-held-out evaluation rather than
same-person leakage.

So:

```text
Phase-A/B public development data
= input X + sufficiently defined target y
→ supervised training/evaluation was possible
```

That still does not make the offline model MR60-validated.

### 15.2 What the current team MR60 legacy data has

The team logs contain real device evidence:

```text
physical MR60 measurements
timestamps / telemetry timing
breath_phase
breath_rate_raw
paced-breathing cues
distance sessions
failed/weak sessions
long-duration / reproducibility evidence
```

They do **not** currently establish all of the information needed for a formal
supervised 3-class evaluation dataset.

```text
current team data:
input signal X exists

but trustworthy Phase-B target y is incomplete / not established
```

Missing or not established for supervised Phase-B use:

- Phase-B class ground truth (`NORMAL` / `RAPID_OR_ABNORMAL` / `APNEA-proxy`)
- independently identifiable participant diversity beyond delivery `S001`
- independent physiological respiration reference
- Phase-B `breath_phase` signal-semantic correspondence
- fresh `0x0A13` phase-frame cadence correspondence

Therefore formal Accuracy / Macro F1 / Recall **cannot yet be scientifically
computed as MR60 model-performance evidence**. Offline Phase-B numbers remain
public-dataset results. They must not be rewritten onto these logs.

### 15.3 Is training impossible with the current raw data?

No. The current MR60 data is not technically unusable for all forms of machine
learning.

It is currently **inappropriate** to use it directly as a supervised
`NORMAL` / `RAPID_OR_ABNORMAL` / `APNEA-proxy` retraining dataset.

Reasons:

```text
Phase-B class ground truth is incomplete
participant diversity is very limited
delivery evidence is primarily S001
independent respiration reference is absent
Phase-B breath_phase signal correspondence is not yet established
fresh phase cadence correspondence is not yet established
```

Correct current use:

```text
M-C0 device-domain analysis first
```

not:

```text
immediate retraining
```

Unsupervised, self-supervised, or domain-adaptation methods are technically
possible in general. They are **not authorized and not justified during M-C**,
because they would mix:

```text
measuring the device-domain gap
```

with:

```text
changing the model to fit that domain
```

Adaptation, retraining, scaler replacement, and architecture change remain
**M-D only**, after a measured gap and separate authorization.

### 15.4 What the current raw data CAN still be used for

“Not suitable for formal performance scoring” does **not** mean “useless data.”

Present-tense authorized uses:

1. MR60 field / producer-code lineage analysis (`0x0A13` vs `0x0A14`)
2. `breath_phase` value-range and waveform characterization
3. telemetry / log-row cadence analysis
4. reconstruction of fresh phase-frame cadence from `phase_age_ms` / update
   times
5. stale / repeated `breath_phase` detection
6. phase dropout analysis
7. distance / lock-loss behavior
8. paced-breathing periodicity analysis
9. vendor `breath_rate_raw` behavior / bias characterization
10. failed-condition QA analysis
11. comparison against Phase-B input semantics
12. determination of whether a valid 30 s / 300-sample **model input** can be
    constructed from fresh phase, not merely from 300 telemetry rows
13. optional exploratory frozen-model inference, **only after** correspondence
    is established
14. identifying which old sessions might later be recoverable as labeled
    evidence and which should remain forensic-only
15. designing the future M-C1 measurement protocol

### 15.5 Paced RPM is not automatically a Phase-B label

The team data includes paced 12 / 15 / 20 rpm sessions. Do **not** infer:

```text
12 rpm → NORMAL
15 rpm → NORMAL
20 rpm → RAPID_OR_ABNORMAL
```

unless a pre-registered Phase-A/B label contract independently establishes that
mapping.

Paced respiration rate and Phase-B supervised class label are different
concepts. Phase-B labels came from the source dataset’s experimental semantics
and Movesense reference rules, not from a newly invented rpm threshold.

Under the frozen A4 profile, Movesense-derived `RAPID_OR_ABNORMAL` begins at
`>= 25.0` bpm. That statement explains why a 20 rpm paced cue would **not**
automatically become `RAPID_OR_ABNORMAL` even if the cue were perfectly
followed **under the public-dataset A4 contract**. It does **not** authorize
applying `>= 25.0` bpm as a new automatic RAPID rule to future MR60
measurements. Future protocol must define the class mapping **before** formal
evaluation or training.

### 15.6 A paced cue is not perfect ground truth

The failed 12 rpm session is the clearest warning.

The file and cue target said 12 rpm. Independent autocorrelation of
`breath_phase` in
`devices/mmwave/firmware/analysis_tools/phase_any_session.py` gave **6.06 rpm**.
The metronome/cue stayed near 12 rpm; the performed chest motion did not.

```text
instruction / intended condition
!=
actual performed physiology
```

Future measurements must distinguish:

```text
INTENDED_CONDITION
ACTUALLY_OBSERVED_REFERENCE
```

A paced cue is useful experimental metadata. It is not automatically equivalent
to independently observed physiological ground truth.

### 15.7 What future model-validation data actually needs

This is a principle list, not a frozen M-C1 protocol. Formal protocol design
remains M-C1 work.

At minimum, a later dataset that could support defensible window labels needs:

```text
MR60 breath_phase or selected lowest exposed signal
+
fresh phase timestamp / freshness evidence
+
subject pseudonym
+
session ID
+
trial ID
+
distance
+
posture
+
sensor orientation / placement
+
presence / motion context where relevant
+
predefined experimental condition
+
independent respiration reference where appropriate
+
actual performed respiration state/rate
+
signal-lock / dropout / failure status
+
firmware/acquisition-code identity
+
trial start/end timestamps
```

Collection principle:

```text
signal only
→ good for sensor analysis

signal + trustworthy answer/ground truth
→ can support model training/evaluation
```

Example of the principle, not a final protocol:

```text
subject S003
session ...
distance ...
posture ...

00:00–02:00  known controlled NORMAL condition
02:00–04:00  known controlled RAPID_OR_ABNORMAL condition
04:00–...    predefined breath-hold / APNEA-proxy condition

MR60 signal and independent reference recorded together
```

Do not invent the exact timings, cues, or safety rules here. APNEA-proxy
collection, if any, remains a voluntary breath-hold proxy under existing safety
rules and is still not clinical apnea.

### 15.8 Subject-wise split requirement

If future MR60 data are later used for model development, participant identity
must be preserved so that subjects can be isolated:

```text
TRAIN subjects
VALIDATION subjects
TEST subjects
```

Avoid placing windows from the same person into both train and test. That
leakage can exaggerate generalization. This is the same principle already
frozen in A5: all recordings and windows from one subject remain in exactly
one split.

### 15.9 Compact comparison

| Evidence property | Phase-A/B public development data | Current team MR60 legacy data | Future controlled MR60 data |
| --- | --- | --- | --- |
| Real radar/device signal | Yes (public radar archive, not team MR60) | Yes (physical MR60) | Yes |
| Subject identity | Yes (110 subjects) | Limited / delivery `S001` | Required |
| Controlled condition | Defined by source dataset | Partial (paced cues, distances, failures) | Required |
| Independent respiration reference | Dataset-defined (Movesense chest ACC; non-breathing annotations) | No independent physiology reference | Required where appropriate |
| Phase-B class label | Available under `MMWAVE_LABEL_MAPPING_PROFILE_001` | Not reliably established | Must be defined before scoring/training |
| Formal model scoring | Yes, as offline public-dataset evidence | No | Intended after M-C2 authorization |
| Supervised training use | Yes, for the frozen offline candidate | Not currently justified | Possible after governance, labels, and subject split |
| Device-domain / MR60 analysis | Not team-MR60 device data | Yes | Yes |

---

## Appendix A. Phase-B input contract (standalone, for comparison only)

Frozen offline candidate, from standalone
`docs/reports/20260813_Cursor_M-B12_mmWave_Phase_B_Offline_Final_Report_01.md`:

- respiration-related time series
- nominal 10 Hz, 30 seconds, 300 samples
- preprocessing `BPF_ZSCORE` / `M-B1_D0_B1_Z1`
- runtime INT8 input shape `[1, 300, 1]`
- candidate remains `REAL_DATA_OFFLINE_CANDIDATE`
- not MR60-validated, not deployment-ready, APNEA remains a proxy

Existing team data looks promising for **starting** correspondence work because
timestamps, ~10 Hz telemetry-row cadence, and a `breath_phase` field exist. It
does not finish that work. In particular, ~10 Hz log rows are not yet shown to
be ~10 Hz fresh phase observations.

## Appendix B. Traceability index

| Claim | Source |
| --- | --- |
| `0x0A13` / `0x0A14` field mapping | `devices/mmwave/firmware/src/main.cpp` |
| Telemetry emit interval 100 ms vs phase-frame update | `include/mmwave_config.h` `kTelemetryIntervalMs`; `src/main.cpp` `loop()` / `handleValidFrame()` / `phase_age_ms` |
| Export does not normalize/resample | `devices/mmwave/firmware/export_mmwave_csv.py` |
| Delivery session list and SHA-256 | `devices/mmwave/firmware/csv/2026-07-26_han_junwoo_delivery_v2/manifest.json` |
| Failed 12 rpm label | same manifest; `DELIVERY_NOTES.md`; `analysis_tools/phase_any_session.py` → 6.06 rpm |
| 12/15/20 calibration table | `devices/mmwave/firmware/analysis/breath/2026-07-28_breath_calibration_12_15_20_comparison.json` |
| No independent heart/respiration sensor | `analysis/breath/2026-07-28_vitals_measured_vs_reference.json` |
| ~31 min schema 1.2 log | `logs/final/2026-08-01_occupied_d09_v120_31min_attempt02.jsonl` |
| 51 / 18,276 = 0.279% gate mismatch | commit `3b44e505…`; `docs/operations/PROJECT_PROGRESS.md` |
| Telemetry row-cadence table | recomputed from delivery CSVs; matches manifest `diagnostics`; this is log-row cadence, not proven fresh `0x0A13` cadence |
| D15 distance sample std ~2.94 cm | recomputed from D15 JSONL `distance_cm_raw` after 60 s warmup |
| Participant `S001` only in delivery CSVs | CSV `subject_id` column; exporter `DEFAULT_SUBJECT` |
| Phase-B frozen contract | standalone `docs/reports/20260813_Cursor_M-B12_mmWave_Phase_B_Offline_Final_Report_01.md` |
| A4 class semantics / APNEA proxy | `docs/reports/20260808_Antigravity_A4_Annotation_Label_Mapping_Pilot_01.md`; `datasets/mmwave/manifests/a4_label_pilot/label_mapping_profile.json` (`rapid_min_rr_bpm: 25.0`, Movesense chest ACC; frozen public-dataset semantics, not an automatic future MR60 threshold) |
| A5 subject-isolated split | `docs/reports/20260808_Antigravity_A5_Subject_Split_Provenance_01.md` |
| Korean team-facing companion | `docs/reports/20260814_SafeNest_mmWave_Team_MR60_Data_Evaluation_KR_01.md` |
