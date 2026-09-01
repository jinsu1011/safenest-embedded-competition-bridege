# PR18 REQUIRED REFINEMENT RESULT

## Repository identity

Team main SHA: `6c3faea3126cff0d17565e534d019d344edc6d1a`

PR #18 base ref SHA: `6c3faea3126cff0d17565e534d019d344edc6d1a` (pre-correction merge-base: `5947334d3d0f6c6f7d6100c7ea6af219e5b4c5d5`)

PR #18 head before correction / current local HEAD: `62eb0d867cfa02295c9a1d023b813134c434b8eb`

Branch: `feature/mmwave-mc0-device-evidence`

Standalone authoritative evidence SHA: `efc7e2eb61a49e221ce0ebf6057b0c1617525ad1`

## Git isolation

Working tree before: clean, tracking `origin/feature/mmwave-mc0-device-evidence`.

Branch ancestry: three PR commits only (`e3f9dc0`, `39a2370`, `62eb0d8`); no CO2, Thermal, Integration, or unrelated sensor-track changes.

Existing PR changed files: 39. MR60 producer files `devices/mmwave/firmware/src/main.cpp` and `devices/mmwave/firmware/include/mmwave_config.h` do not differ from base; producer semantics are unchanged.

Corrective files are confined to `devices/mmwave/device_measurements/`. Exact inventory:

- policy/index: `.gitignore`, `README.md`, `progress.md`;
- QA/schema/tests: `tools/physical_capture_qa.py`, `tests/test_physical_capture_qa.py`, `schemas/raw_record.schema.json`, and both Pilot QA JSON files;
- inference reproducibility: `tools/tflite_offline_benchmark.py`;
- reports: `M-C0_PILOT_DESKWORK_001.md`, `M-C0_TEAMMATE_CONTINUATION_PROMPT.md`, `existing_evidence_audit.md`, `offline_pipeline_audit.md`, `offline_pipeline_results.json`, `tflite_offline_benchmark.md`, `tflite_offline_benchmark_results.json`, `verification_matrix.md`, and this completion report.

Unrelated files: none.

## Immutable evidence check

Pilot desk-work:

- path: `devices/mmwave/device_measurements/pilot/M-C0-PILOT-DESKWORK-001.raw.jsonl`
- SHA-256 before/after: `368e6a16e897b9231ff5fcdecd3edcc5b725a0a4dc6b20dee1e3162405bc2876` / identical
- bytes before/after: `1819539` / identical
- records before/after: `1799` / identical

Pilot stationary:

- path: `devices/mmwave/device_measurements/pilot/M-C0-PILOT-STATIONARY-001.raw.jsonl`
- SHA-256 before/after: `e2b832fd3a72f18b4c3a370738c10e58c0269283dac218ae2d7d4dad48036f6f` / identical
- bytes before/after: `1837444` / identical
- records before/after: `1799` / identical

Firmware identity: `safenest-mr60-esp/1.2.0`; producer source SHA-256 `a812888a25da85eea7bc35fece9d11013f116fb50639e003b3455544ae25d98b`; capture program SHA-256 `ef084d921d6e51fbc66c8845c4f0d6e5de9dc561ba95cd13aa07589d7638b859`.

Config hash: `b817e8bfd5e52b18275626f7b6a9bd60098ea4b108428a5aaf63600dbc987834`.

Frozen Phase-B model identity: authoritative path `models/mmwave/experiments/M-B6_stage_equivalence/M-B3_CONV1D_GAP_BASELINE_seed42_M-B5_CAL_CLASS_BALANCED_120_int8.tflite`, SHA-256 `6dff6aaa72c79d76715d40cf7e32bb1e6cd9b2c2e3ac78eaf2fda737561430c5`; resolved from standalone M-B11/M-B12 lock evidence at the commit above. PR #18's artifact has the same SHA. Input `[1,300,1]` INT8 (scale `0.041720833629369736`, zero-point `-3`); output `[1,3]` INT8 (scale `0.00390625`, zero-point `-128`), classes `NORMAL`, `RAPID_OR_ABNORMAL`, `APNEA` proxy. Locked preprocessing remains `BPF_ZSCORE`, 0.1–0.5Hz order-4 zero-phase Butterworth at 10Hz, mean `0.0031162832173884064`, std `2.955399434649939`.

## Refinement 1 — freshness

Telemetry cadence separated from fresh phase cadence: **YES**.

| Pilot | rows / intervals | telemetry row Hz | interval min / median / p95 / max (ms) | `phase_age_ms` count / missing / invalid | min / median / p95 / max (ms) |
|---|---:|---:|---:|---:|---:|
| desk-work | 1799 / 1798 | 9.993997 | 100 / 100 / 100 / 103 | 1799 / 0 / 0 | 0 / 12 / 15 / 111 |
| stationary | 1799 / 1798 | 9.993330 | 100 / 100 / 101 / 102 | 1799 / 0 / 0 | 0 / 12 / 15 / 17 |

Authoritative producer validity threshold exists: **YES**. Source/value: `devices/mmwave/firmware/include/mmwave_config.h`, `kPhaseMaxAgeMs = 500ms`. It classifies producer staleness/validity; it does not reconstruct every `0x0A13` arrival.

Exact fresh-phase cadence verified: **NO**.

Fresh-phase final claim: `FRESH_PHASE_CADENCE_NOT_YET_FULLY_VERIFIED`.

Repeated identical `breath_phase` treated as sufficient stale proof: **NO**.

Schema outcome: `phase_age_ms` is `EXPLICITLY_OPTIONAL_WITH_LIMITATION` for historical compatibility; current Pilot QA reports its presence and validity explicitly.

## Refinement 2 — D15

Source artifact: `devices/mmwave/firmware/csv/2026-07-26_han_junwoo_delivery_v2/2026-07-25_occupied_d15_v1_360s__S001_NORMAL_D15.csv`.

Selection: all 2,639 finite `range_m` values; missing/non-finite excluded; converted from metres to centimetres. Python `statistics.pstdev`/`statistics.stdev` reproduces the result.

Population std (`ddof=0`): `2.937040294cm`.

Sample std (`ddof=1`): `2.937596920cm` (used in corrected narrative).

Incorrect distance std=0 claim corrected: **YES**.

Lock/freeze interpretation: distance varies (`1.7220–1.8368m`), while all 2,999 finite `resp_phase` values equal `-0.01` (std 0). D15 remains exploratory vitals/phase freeze or lock-loss evidence, but zero distance variance is not supporting evidence.

## Refinement 3 — 620/620 APNEA

Observed result preserved: **YES**.

Classification: `EXPLORATORY_PRE_CORRESPONDENCE_INFERENCE`.

Warning classification: `PIPELINE_CORRESPONDENCE_WARNING`, `DEVICE_DOMAIN_MISMATCH_WARNING`.

Formal Accuracy/F1 claimed: **NO**. M-C0 correspondence claimed complete: **NO**. M-C2 claimed: **NO**. Single root cause claimed: **NO**. Clinical apnea evidence claimed: **NO**.

## Refinement 4 — raw policy

Final policy: `TRACKED_EXCEPTION`.

Existing Pilot JSONL files preserved: **YES**. Raw bytes unchanged: **YES**. Documentation/Git state consistent: **YES**. Unrelated JSONL accidentally tracked: **NO**.

The two curated Pilot paths remain tracked despite the general `*.jsonl` ignore rule. The exception does not authorize arbitrary, private, large, scratch, or unreviewed payloads.

## Technical boundaries

MR60 parser modified: **NO**

Firmware modified: **NO**

Frozen Phase-B model modified: **NO**

`BPF_ZSCORE` modified: **NO**

Training: **NO**

Additional inference: **NO**

M-C1: **NO**

M-C2: **NO**

M-D: **NO**

## Validation

- Tests: QA unit test covers valid/missing/invalid `phase_age_ms`, summary values, and the producer threshold.
- Schema validation: fixture contract validation passes; schema remains backward compatible.
- QA validation: both immutable Pilot raws regenerate machine-readable QA with stream integrity pass.
- Negative tests: repository negative suite passes.
- JSON parsing: all modified/generated JSON parses.
- D15 reproduction: source sample count and both `ddof` definitions reproduced independently.
- Raw SHA verification: both SHA-256/byte/record identities match the frozen pre-edit values.
- Documentation consistency: superseded D15, raw-policy, cadence, and 620/620 wording searched across the PR evidence area.
- `git diff --check`: pass.

## Findings

BLOCKER: Exact fresh-phase cadence and formal MR60-to-Phase-B correspondence remain unverified; independent aligned reference is absent.

REQUIRED REFINEMENT: All four requested PR #18 refinements are represented in code, machine-readable QA, and documentation.

NON-BLOCKING IMPROVEMENT: A future producer-side phase update sequence/event timestamp would permit exact fresh-arrival reconstruction. This task does not authorize that firmware change or any new capture.

## Final recommendation

YES — PR #18 now preserves the useful MR60 Pilot evidence while correctly separating telemetry cadence from fresh breath_phase evidence, correcting D15 evidence, constraining the all-APNEA inference claim, and documenting the intentional tracked raw-evidence exception
