# SafeNest CO₂ C-B6 Reduced-Feature Candidate Development and Lock

- Document Version: `01`
- Author: `Codex` (CO₂ C-B6 Offline Candidate Agent)
- Execution Date: `2026-08-15`
- Phase: `C-B6 — Reduced-Feature Candidate Development and Lock`
- Status: `C_B6_PASS_WITH_LIMITATIONS`

**Candidate ID:** `C_B6_REDUCED_CO2_SLOPE_CANDIDATE_001`
**Execution base:** `88d7cef7a4e9783e77aac84fb885d5db8bca6b7c`
**Standalone main:** `88d7cef7a4e9783e77aac84fb885d5db8bca6b7c`
**Team main reference:** `3d86bf2a7a4e527d7aba2dfabcb087201ffeb46e`

## Executive result

The already-selected `CO2 + CO2_slope` direction was implemented as a new,
independently scaled and independently thresholded offline logistic candidate.
The historical four-feature B5 candidate was not modified. The candidate status
is `C_B6_PASS_WITH_LIMITATIONS`. Physical acquisition, C-C2, and C-D remain unauthorized.

This report records offline construction evidence only:

```text
C-B6 OFFLINE VALIDATION != SCD40 DEVICE-DOMAIN VALIDATION
```

## Predecessor decision and frozen contract

The merged predecessor decision was `ADOPT_REDUCED_FEATURE_DIRECTION`, based on
`SYSTEM_CONTRACT_BURDEN_OF_PROOF`. Four-feature predictive benefit remains
observed, reduced-feature predictive superiority was not established, and the
old C-C1 four-feature protocol remains historical evidence. The C-B6 feature
selection question was not reopened.

```text
FEATURE_ORDER: CO2, CO2_slope
TEMPERATURE_MODEL_INPUT: FORBIDDEN
HUMIDITY_MODEL_INPUT: FORBIDDEN
SLOPE_PROFILE: CO2_SLOPE_FEATURE_PROFILE_001
SLOPE_METHOD: ENDPOINT_DIFFERENCE
HISTORY_SECONDS: 150.0
MAX_INTERNAL_GAP_SECONDS: 90.0
```

## Dataset lineage and access boundary

The candidate consumes the locked A5 canonical materialization rather than the
absent Git-ignored raw ZIP. A-series release and artifact-lock verification
passed. TRAIN and VALIDATION use the canonical eligible IDs and fingerprints;
the sealed LOCKED_TEST is membership-verified only.

| Population | Rows | Fingerprint | Role |
|---|---:|---|---|
| TRAIN | 8140 | `492ca1f67e44b4a2018b743ec0fc3d20b418f7823d5f2643d8c90b0d39de8fab` | scaler, threshold OOF, model fitting |
| VALIDATION | 2662 | `19321e57fe72f6482b3c7b5d3714d21e9c13b753173ceb56ea694524ac6529ef` | frozen-threshold consistency evidence |
| LOCKED_TEST | 9749 | `0bac8dc1affae1de48ea68f01e866508ea19f31e194a7c0dccbf617e529344e7` | membership only |

```text
LOCKED_TEST_FEATURE_ROWS_DECODED: 0
LOCKED_TEST_TARGET_ROWS_DECODED: 0
LOCKED_TEST_PREDICTIVE_METRICS: 0
LOCKED_TEST_THRESHOLD_SELECTION: 0
LOCKED_TEST_MODEL_SELECTION: 0
LOCKED_TEST_HYPERPARAMETER_SELECTION: 0
```

The raw-dependent standalone A5/A6 validators cannot independently reopen the
ZIP in this worktree because the ignored archive is absent. The locked A5
materialization, checksums, A-series release tag, and A-series artifact lock
were verified; no raw-dependent PASS claim is made here.

## Scaler and training procedure

A new two-feature `StandardScaler` was fit on the original TRAIN rows only.
The historical four-feature scaler was not reused.

```text
SCALER_FIT_SOURCE: ORIGINAL_TRAIN_ONLY
SCALER_FEATURE_ORDER: CO2, CO2_slope
SCALER_FINGERPRINT: a92123ad37e9b284929ba0fe53179126345d54d487ec4b3a73c910d00490a462
MEAN: [606.5058118345612, 0.011527303414630624]
SCALE: [314.3524240597083, 5.661675596121919]
```

The model family remained `LINEAR_LOGISTIC` with the existing B-series
parameters (`L2`, `C=1.0`, `lbfgs`, intercept, `max_iter=2000`). The existing
`BALANCED_RANDOM_OVERSAMPLE` policy and seed `20260810` were applied to TRAIN
only. No architecture, hyperparameter, split, label, slope, or feature search
was performed.

## Threshold-selection policy and result

The machine-readable threshold policy was written with status
`PREDECLARED_BEFORE_THRESHOLD_SELECTION` before calculating OOF thresholds.
It uses five-fold stratified TRAIN-internal OOF probabilities, fold-local
TRAIN-only scalers and oversampling, and a grid from 0.05 to 0.95 in 0.01
increments. The objective is to maximize Macro F1 among candidates with
occupied recall at least `0.90`, then apply the declared
recall/precision/balanced-accuracy/FPR/tie-break rules.

```text
B5_THRESHOLD_0_58_INHERITED: NO
THRESHOLD_SOURCE: TRAIN_INTERNAL_ONLY
FINAL_THRESHOLD: 0.43
COINCIDENTAL_MATCH_TO_B5: FALSE
```

The existing VALIDATION population was not used to tune this threshold. It has
historical development use and is reported only as frozen-threshold
development-validation/consistency evidence.

## Reference model and VALIDATION results

The reference model coefficients, intercept, feature order, scaler identity,
class mapping, and training lineage are stored in the candidate directory.
The following values are from the frozen-threshold reference model:

| Metric | Reference Float | Float TFLite | INT8 TFLite |
|---|---:|---:|---:|
| Accuracy | 0.892938 | 0.892938 | 0.891811 |
| Balanced Accuracy | 0.908107 | 0.908107 | 0.907441 |
| Macro F1 | 0.888875 | 0.888875 | 0.887788 |
| OCCUPIED Precision | 0.788851 | 0.788851 | 0.786375 |
| OCCUPIED Recall | 0.963880 | 0.963880 | 0.964912 |
| OCCUPIED F1 | 0.867627 | 0.867627 | 0.866543 |
| PR-AUC | 0.946366 | 0.946366 | 0.939729 |
| ROC-AUC | 0.966039 | 0.966039 | 0.965348 |
| Brier score | 0.083376 | 0.083376 | 0.083426 |
| Log loss | 0.306609 | 0.306609 | 0.304359 |

## TFLite conversion and INT8 diagnostics

Two new TFLite artifacts were created; no B5 TFLite artifact was overwritten.
The INT8 model uses one integer input and one integer output tensor. The
representative dataset is all natural TRAIN rows after the new TRAIN-only
scaler; VALIDATION and LOCKED_TEST rows are excluded.

```text
FLOAT_TFLITE: models/co2/candidates/c_b6/float_reference.tflite
FLOAT_TFLITE_SHA256: fc1d4150a818473758f1f2a7c3a5f3afe604cf7c59171524f21dac3a22c3a87c
INT8_TFLITE: models/co2/candidates/c_b6/full_integer_int8.tflite
INT8_TFLITE_SHA256: c5969b367f5b5e28c4d27f1bdd6220f7d02da92e99604e3f85c9f1291e98dd3b
INT8_INPUT_DTYPE: int8
INT8_INPUT_SHAPE: [1, 2]
INT8_INPUT_SCALE_ZERO_POINT: 0.03921568766236305, 0
INT8_OUTPUT_DTYPE: int8
INT8_OUTPUT_SCALE_ZERO_POINT: 0.00390625, -128
```

The conversion/equivalence gate is `PASS`. Float-to-INT8
probability MAE was `0.004778`, p95 drift
was `0.014608`, maximum
drift was `0.034470`, and
label disagreement was `7`
of `2662`.

Saturation is reported separately by feature. TRAIN representative saturation
was CO2 `0` and
CO2_slope `12`;
VALIDATION saturation was CO2 `0`
and CO2_slope `3`.
This known slope saturation is retained as a limitation and is not silently
treated as proof of device-domain suitability.

## Candidate lock and immutability

The dedicated C-B6 lock binds the candidate ID, two-feature contract, new
scaler hash, reference model evidence, threshold result, TFLite hashes,
quantization contract, validation evidence, and TRAIN/VALIDATION lineage.
The lock does not hash itself; the checksum manifest covers the lock.

```text
CANDIDATE_LOCK: datasets/co2/manifests/c_b6_reduced_feature_candidate/candidate_lock.json
LOCK_SHA256: 5f7772ff26ca10ca95aa5216b45f3eebd96c2429b98a7ee66963ec4ea73c6fd2
CHECKSUM_MANIFEST: datasets/co2/manifests/c_b6_reduced_feature_candidate/checksums.sha256
DETERMINISTIC_RERUN: PASS
B5_MODIFIED: NO
```

All selected B5 frozen artifact hashes matched before and after generation.
The B5 model, scaler, threshold, metadata, and final lock remain historical
and untouched.

## Known limitations and non-claims

- VALIDATION has already participated in historical development and decision work; it is not an untouched final holdout.
- C-B6 does not prove generalization to real SCD40 data.
- INT8 input saturation is observed for CO2_slope in the TRAIN representative population and requires review before operator handoff.
- No physical acquisition, SCD40 device-domain validation, runtime/firmware change, telemetry change, C-C2, or C-D work occurred.
- Occupancy recall is not a direct safety metric; this candidate has room-occupancy semantics only.

## Roadmap impact and next phase

The canonical roadmap records this C-B6 candidate and its status. The next
conceptual phase is `C-C1R — Reduced-Feature Measurement Protocol Revision and
Operator Handoff`. That phase requires separate authorization and must review
the INT8 slope-saturation limitation before any operator guide is distributed.
Physical acquisition remains `HOLD`.

## Validation boundary

```text
NEW_PHYSICAL_MEASUREMENT: NO
PHYSICAL_ACQUISITION_STARTED: NO
C_C2_STARTED: NO
FORMAL_DEVICE_DOMAIN_VALIDATION: NO
C_D_AUTHORIZED: NO
```
