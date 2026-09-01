# SafeNest CO₂ — Temperature / Humidity Feature Necessity Audit

## Decision

```text
T_RH_FEATURE_DEPENDENCE_INCONCLUSIVE
```

The existing offline evidence does not justify either dropping Temperature / Humidity from the future acquisition contract or declaring those features materially necessary. The primary A/B comparison is mixed: the four-feature arm improves validation Macro F1 and occupied precision, while the reduced arm improves occupied recall. No arbitrary equivalence margin was applied.

The current C-C1 Temperature / Humidity requirement therefore remains temporarily in force. This audit does not change C-C1 protocol 001, B5, the production scaler, the TFLite artifact, thresholds, labels, slope definitions, or the canonical split.

## Scope and boundary

This is an offline feature-necessity audit using the already-materialized C-A5 canonical evidence and the closed C-B2 procedure. It performs no new physical measurement, model promotion, runtime/firmware change, or team-repository modification.

The four comparison arms are:

| Arm | Inputs |
|---|---|
| A | CO₂ + Temperature + Humidity + CO₂_slope |
| B | CO₂ + CO₂_slope |
| C | CO₂ only |
| D | CO₂ + Temperature + Humidity |

All arms use the same `ENDPOINT_H150` slope values, original-TRAIN-only `StandardScaler`, `BALANCED_RANDOM_OVERSAMPLE` with seed `20260810`, `B2_FIXED_LOGISTIC_PROBE_001`, and the inherited frozen threshold `0.58`. The threshold was not retuned for this audit.

Feature selection uses TRAIN and VALIDATION only. `LOCKED_TEST` is sealed and was used only for membership accounting.

## Data lineage

| Item | Evidence |
|---|---|
| Audit branch | `feature/co2-trh-feature-necessity-audit` |
| Audit execution base | `7d30ec3` |
| Team repository `main` (read-only review) | `3d86bf2a7a4e527d7aba2dfabcb087201ffeb46e` |
| TRAIN | 8,140 rows; ID fingerprint `492ca1f67e44b4a2018b743ec0fc3d20b418f7823d5f2643d8c90b0d39de8fab` |
| VALIDATION | 2,662 rows; ID fingerprint `19321e57fe72f6482b3c7b5d3714d21e9c13b753173ceb56ea694524ac6529ef` |
| LOCKED_TEST | 9,749 rows; ID fingerprint `0bac8dc1affae1de48ea68f01e866508ea19f31e194a7c0dccbf617e529344e7` |
| Canonical source JSONL | SHA-256 `d157290a6ddcb7ff14f99f37331b713d897f64ca480e91912acde40f11d229f7` |
| Eligible-ID JSONL | SHA-256 `5c69db52bf86e4045c54b65277e623c7920dcd7e8e685f970799a6a5530f5863` |
| Declared source archive lineage | SHA-256 `4ae3f46aa98eedff564a9f6924d1635173e2fd2c816004342a9be93076d3a81a` |

The raw UCI archive was not required for this run; the existing canonical materialization was used. The synthetic `.npz` fixture was not used as real training data, and no random row-wise split was created.

## Validation results

All values below are from the fixed validation population at threshold `0.58`.

| Arm | Accuracy | Balanced accuracy | Occupied precision | Occupied recall | Vacant precision | Vacant recall | Macro F1 |
|---|---:|---:|---:|---:|---:|---:|---:|
| A | 0.913599 | 0.914862 | 0.854267 | 0.919505 | 0.951822 | 0.910219 | 0.908121 |
| B | 0.904207 | 0.909906 | 0.827523 | 0.930857 | 0.957379 | 0.888955 | 0.899026 |
| C | 0.867393 | 0.871695 | 0.778986 | 0.887513 | 0.930039 | 0.855877 | 0.860567 |
| D | 0.868520 | 0.868830 | 0.790066 | 0.869969 | 0.921003 | 0.867690 | 0.860823 |

### A minus B

```text
accuracy              +0.009391435011
balanced_accuracy     +0.004956059584
occupied_precision    +0.026743603050
occupied_recall       -0.011351909185
vacant_precision      -0.005557022445
vacant_recall         +0.021264028352
macro_f1              +0.009094519832
```

The A/B result is not directionally dominant on the three primary feature-dependence metrics (`macro_f1`, occupied precision, occupied recall). That is the basis for `INCONCLUSIVE`, without an effect-size or equivalence threshold.

The `MATERIAL` and `LOW` labels in this audit are directional decision classifications only. They are not statistical-significance claims or predefined practical-equivalence findings. No approved effect-size or equivalence margin existed for this audit.

The A reference-probe validation result reproduces the existing C-B2 reference-threshold result at threshold `0.58`. Its scaler fingerprint is unchanged at:

```text
d0cf83558fb0de9dcdc97f0d94781a5a475a6f68e8d818121aee929030e5dc89
```

## LOCKED_TEST protection

```text
LOCKED_TEST feature rows decoded:     0
LOCKED_TEST target rows decoded:      0
LOCKED_TEST predictive metrics:       0
LOCKED_TEST scaler/model fit usage:   0
LOCKED_TEST threshold/tuning usage:    0
```

The 9,749 sealed eligible IDs were counted for integrity accounting only. No LOCKED_TEST feature or target value entered arm construction, scaling, training, thresholding, or comparison.

## Consequences for the active roadmap

- Keep C-C1 protocol 001 and its Temperature / Humidity acquisition requirement unchanged for now.
- Do not replace or retrain the frozen four-feature B5 candidate based on this audit.
- Keep C-C2 behind its existing controlled-intake and protocol-compliance gate.
- Do not claim that T/RH are unnecessary; the current offline result is mixed and cannot isolate a safe feature removal decision.
- A later, separately authorized reduced-feature phase may be designed after the C-C1 evidence and decision gate, with fresh protocol-controlled data and no adaptive tuning during acquisition.

No edits were justified in the existing roadmap, C-C0 reports, C-C1 technical protocol, operator prompt, or protocol manifest for this inconclusive result.

## Validation status

```text
Audit generator, first run:                         PASS
Audit generator, deterministic second run:          PASS
Audit result checksum manifest:                     PASS
C-C1 protocol validator:                            PASS
B5 lock validator:                                  PASS_WITH_WARNINGS
Focused C-C1 + B5 tests:                            16 passed
git diff --check / authored-file whitespace check:   PASS
Hardware / C-C2 measurement:                        NOT PERFORMED
```

The full raw-dependent C-A5 and C-B2 validators could not complete in this worktree because `datasets/raw_archives/external_datasets/occupancy+detection.zip` is absent. The C-B2 validator also has a phase-local path allowlist that does not include this later follow-up artifact. These are reported as unverified validation conditions; no C-A5 or C-B2 predecessor artifact was modified, and the audit result did not rely on LOCKED_TEST or the synthetic fixture.

## B5 and repository mutation status

```text
B5 feature order:              CO2, Temperature, Humidity, CO2_slope
B5 threshold:                  0.58
B5 scaler fingerprint:         d0cf83558fb0de9dcdc97f0d94781a5a475a6f68e8d818121aee929030e5dc89
B5 model SHA-256:              bb2ed28533bca75d4fa3d06348e017c506df47d7c34b29574b77f70b6b386816
B5 metadata/model/scaler edit: NO
Team repository edit:          NO (read-only)
```

This audit performed no production model modification, physical measurement, runtime/firmware modification, or team-repository modification.

## Reproduction and changed files

The comparison is reproducible with:

```text
scripts/audit_co2_trh_feature_necessity.py
```

The result JSON was generated twice with the same output SHA-256:

```text
ef7053adb38328feb5080e8845d39fd3b73e6ff4138ddc4af9439d490c8d9d08
```

Files included in this audit change:

```text
docs/reports/20260815_SafeNest_CO2_Temperature_Humidity_Feature_Necessity_Audit_01.md
datasets/co2/manifests/c_c1_trh_feature_necessity_audit/feature_necessity_result.json
datasets/co2/manifests/c_c1_trh_feature_necessity_audit/checksums.sha256
scripts/audit_co2_trh_feature_necessity.py
```
