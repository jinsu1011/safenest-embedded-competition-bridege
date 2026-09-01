# SafeNest CO₂ Pre-Acquisition Model-Input Decision Audit

- Document Version: `01`
- Author: `Codex` (CO₂ Pre-Acquisition Decision Audit Agent)
- Execution Date: `2026-08-15`
- Phase: `C-C — Pre-Acquisition Model-Input Decision Audit`
- Status: `COMPLETE_WITH_HOLD`

**Audit ID:** `CO2_PRE_ACQUISITION_MODEL_INPUT_DECISION_AUDIT_001`
**Date:** `2026-08-15`
**Predecessor:** `CO2_TRH_FEATURE_NECESSITY_AUDIT_001` / PR #78 result `T_RH_FEATURE_DEPENDENCE_INCONCLUSIVE`
**Decision:** `ADOPT_REDUCED_FEATURE_DIRECTION`

## Executive decision

The final candidate-direction comparison selects:

```text
FUTURE_MODEL_INPUT_DIRECTION: CO2 + CO2_slope
FINAL_INPUT_DECISION: ADOPT_REDUCED_FEATURE_DIRECTION
PHYSICAL_ACQUISITION_STATUS: HOLD_PENDING_REDUCED_FEATURE_CANDIDATE_LOCK
OPERATOR_GUIDE_HANDOFF: HOLD
CURRENT_B5_STATUS: HISTORICAL_FROZEN_FOUR_FEATURE_CONTRACT
B5_MODIFIED: NO
C-C2_STARTED: NO
```

The four-feature B5 artifact and the four-feature C-C1 protocol remain unchanged as historical evidence. This result does not remove Temperature or Humidity from B5, does not claim that T/RH contain zero information, and does not authorize physical acquisition. A new reduced-feature candidate must be trained, validated, and locked before a revised acquisition protocol or operator guide is created.

The required interpretation is:

```text
FOUR_FEATURE_PREDICTIVE_BENEFIT_OBSERVED: YES
REDUCED_FEATURE_PREDICTIVE_SUPERIORITY: NO
OCCUPIED_RECALL_ADVANTAGE_AT_0_58: YES
OCCUPIED_RECALL_ADVANTAGE_THRESHOLD_CONDITIONED: YES
T_RH_ZERO_INFORMATION_CLAIM: NO
DECISION_BASIS: SYSTEM_CONTRACT_BURDEN_OF_PROOF
```

The reduced-feature direction is therefore not being adopted because the two-feature arm outperformed the four-feature arm overall. The four-feature arm showed modest, repeatable offline predictive advantages across most evaluated metrics. The system direction changed because the four-feature design did not clear the predeclared burden of proof for introducing new mandatory T/RH device-contract fields.

This audit is a model-input direction decision only. It is not C-C2, device-domain validation, new physical measurement, model deployment validation, or a C-D authorization.

## Predictive result vs system-contract decision

These are separate conclusions and must not be collapsed:

| Question | Evidence-backed answer |
|---|---|
| Which arm showed the stronger overall offline predictive pattern? | The four-feature arm A; it was better in all five seeds for accuracy, Macro F1, occupied precision, PR-AUC, ROC-AUC, Brier score, and log loss when each metric's proper direction is used. |
| Did the reduced arm establish predictive superiority? | No. `REDUCED_FEATURE_PREDICTIVE_SUPERIORITY = NO`. |
| What did B win? | Occupied recall at the inherited fixed threshold `0.58`, in all five seeds. |
| Is that recall result inherent reduced-feature superiority? | No. It is `THRESHOLD_CONDITIONED`. |
| Why select the reduced future direction? | The project requires affirmative evidence before adding T/RH as mandatory physical-data fields; that system-contract burden was not cleared. |

The two conclusions are not contradictory: a four-feature model can have modest overall predictive benefits while the system still declines to impose new mandatory device fields without stronger contract-level justification.

## Why this audit was required

PR #78 established that the four-feature and reduced-feature arms were directionally mixed in one prior comparison, so `T_RH_FEATURE_DEPENDENCE_INCONCLUSIVE` was the correct immediate result. That result was not sufficient to decide whether the newly required T/RH device fields should become mandatory for the next physical acquisition contract.

This audit therefore applied a predeclared burden-of-proof rule to repeated A/B comparisons. The burden was placed on the four-feature design because adding T/RH creates additional device, freshness, telemetry, calibration, and operator-contract requirements. The rule was fixed before the new seed results were read.

## Scope and non-scope

The audit did:

- compare only the final candidates A and B;
- reuse the canonical TRAIN/VALIDATION population, occupancy mapping, `ENDPOINT_H150`, past-only chronology, model family, imbalance procedure, and frozen threshold;
- fit an independent scaler for each arm on original TRAIN rows only;
- repeat the comparison over five fixed seeds;
- calculate paired bootstrap intervals on the same validation rows for both arms;
- record prediction disagreement and class distribution;
- verify that the current B5 lock was not modified;
- keep `LOCKED_TEST` sealed.

The audit did not:

- decode `LOCKED_TEST` feature or target rows;
- select a model from `LOCKED_TEST`;
- run B5 or a TFLite artifact on physical SCD40 data;
- collect new physical measurements or create a new raw payload;
- modify the B5 model, scaler, threshold, feature order, or slope contract;
- start C-C2 or formal device-domain validation;
- tune a threshold, search a hyperparameter, redesign `ENDPOINT_H150`, or resplit the data;
- claim statistical significance, practical equivalence, clinical performance, or safety performance.

## Repository and evidence lineage

| Item | Value |
|---|---|
| Standalone audit execution base | `266151d12a1e4b144d5a6f2bae28dda72f939cc5` |
| Standalone `origin/main` used by the audit | `266151d12a1e4b144d5a6f2bae28dda72f939cc5` |
| PR #78 merge commit | `266151d12a1e4b144d5a6f2bae28dda72f939cc5` |
| Read-only team `main` reference | `3d86bf2a7a4e527d7aba2dfabcb087201ffeb46e` |
| Canonical source SHA-256 | `d157290a6ddcb7ff14f99f37331b713d897f64ca480e91912acde40f11d229f7` |
| Declared source archive SHA-256 | `4ae3f46aa98eedff564a9f6924d1635173e2fd2c816004342a9be93076d3a81a` |
| Source archive availability in this worktree | Not present; canonical materialization and its recorded SHA were used |
| Synthetic fixture used | `NO` |
| Random row split used | `NO` |
| Split reused without resplitting | `YES` |

The team repository was read-only for this audit. No team implementation, telemetry contract, firmware, runtime, or device evidence was modified.

## Canonical population and sealed split

| Split | Rows | Fingerprint | Use in this audit |
|---|---:|---|---|
| TRAIN | 8,140 | `492ca1f67e44b4a2018b743ec0fc3d20b418f7823d5f2643d8c90b0d39de8fab` | scaler fitting and model fitting |
| VALIDATION | 2,662 | `19321e57fe72f6482b3c7b5d3714d21e9c13b753173ceb56ea694524ac6529ef` | all decision metrics and paired bootstrap |
| LOCKED_TEST | 9,749 | `0bac8dc1affae1de48ea68f01e866508ea19f31e194a7c0dccbf617e529344e7` | membership only; no feature/target decode |

`LOCKED_TEST` access was explicitly guarded:

```text
feature rows decoded: 0
target rows decoded: 0
predictive metrics: 0
selection usage: 0
model-selection usage: 0
sealed: YES
```

## Candidates and fixed training contract

```text
A = CO2 + Temperature + Humidity + CO2_slope
B = CO2 + CO2_slope
```

Both arms used the same:

- occupancy mapping and canonical split;
- `ENDPOINT_H150` history of 150 seconds;
- past-only chronology;
- maximum internal gap of 90 seconds;
- original-TRAIN-only scaler fitting policy;
- balanced random oversampling procedure;
- fixed logistic probe family `B2_FIXED_LOGISTIC_PROBE_001`;
- L2 penalty, `C=1.0`, `lbfgs`, intercept, `max_iter=2000`;
- threshold `0.58`, inherited from B5 and not retuned.

Each arm fit its own scaler to its own feature subset. The B arm did not reuse the four-feature B5 scaler.

## Repeated-seed and bootstrap design

The seed list was fixed before reading the new results:

```text
[20260810, 20260811, 20260812, 20260813, 20260814]
```

The paired bootstrap used the same validation-row indices for A and B within each replicate:

```text
bootstrap seed: 20260815
replicates: 2000
interval: percentile 2.5% / 97.5%
population: VALIDATION only
```

The `MATERIAL`/`LOW` vocabulary from the predecessor audit is not treated as statistical significance or practical equivalence here. This audit uses directional repeatability and paired uncertainty only; no approved effect-size or equivalence margin existed.

## Per-seed primary results

Values are measured on the same 2,662-row VALIDATION population. Higher is better for the first four metrics.

| Seed | Arm | Accuracy | Macro F1 | Occupied precision | Occupied recall |
|---:|:---:|---:|---:|---:|---:|
| 20260810 | A | 0.913599 | 0.908121 | 0.854267 | 0.919505 |
| 20260810 | B | 0.904207 | 0.899026 | 0.827523 | 0.930857 |
| 20260811 | A | 0.910218 | 0.904765 | 0.845644 | 0.921569 |
| 20260811 | B | 0.903080 | 0.898038 | 0.822888 | 0.934985 |
| 20260812 | A | 0.910594 | 0.905036 | 0.848427 | 0.918473 |
| 20260812 | B | 0.903080 | 0.897929 | 0.824658 | 0.931889 |
| 20260813 | A | 0.910969 | 0.905416 | 0.849237 | 0.918473 |
| 20260813 | B | 0.902705 | 0.897552 | 0.823905 | 0.931889 |
| 20260814 | A | 0.910969 | 0.905489 | 0.847909 | 0.920537 |
| 20260814 | B | 0.902705 | 0.897588 | 0.823315 | 0.932921 |

Seed directional counts:

| Metric | Direction | A better | B better | Ties |
|---|---|---:|---:|---:|
| Accuracy | higher | 5 | 0 | 0 |
| Macro F1 | higher | 5 | 0 | 0 |
| Occupied precision | higher | 5 | 0 | 0 |
| Occupied recall | higher | 0 | 5 | 0 |
| PR-AUC | higher | 5 | 0 | 0 |
| ROC-AUC | higher | 5 | 0 | 0 |
| Brier score | lower | 5 | 0 | 0 |
| Log loss | lower | 5 | 0 | 0 |

## Aggregate metrics

The aggregate is the mean across the five fixed seeds. Brier score and log loss are lower-is-better metrics.

| Metric | A: four features | B: CO₂ + slope | A − B | Direction |
|---|---:|---:|---:|---|
| Accuracy | 0.911270 | 0.903156 | +0.008114 | higher |
| Balanced accuracy | 0.913075 | 0.909432 | +0.003643 | higher |
| Macro F1 | 0.905765 | 0.898027 | +0.007739 | higher |
| Occupied precision | 0.849097 | 0.824458 | +0.024639 | higher |
| Occupied recall | 0.919711 | 0.932508 | −0.012797 | higher |
| Occupied F1 | 0.882991 | 0.875158 | +0.007833 | higher |
| Vacant precision | 0.951750 | 0.958239 | −0.006489 | higher |
| Vacant recall | 0.906438 | 0.886356 | +0.020083 | higher |
| Vacant F1 | 0.928540 | 0.920896 | +0.007644 | higher |
| PR-AUC | 0.951524 | 0.945724 | +0.005800 | higher |
| ROC-AUC | 0.969272 | 0.965629 | +0.003643 | higher |
| Brier score | 0.073051 | 0.084547 | −0.011495 | lower |
| Log loss | 0.272600 | 0.310753 | −0.038153 | lower |

The machine-readable result retains the exact values and per-seed details. The directionally relevant interpretation is that A is better for probability quality in every seed when lower-is-better metrics are evaluated correctly.

## Paired bootstrap uncertainty

Intervals are percentile intervals over paired validation-row resamples. Each delta is A minus B.

| Metric | Mean delta | 2.5% | 97.5% | Keep-rule requirement |
|---|---:|---:|---:|---|
| Accuracy | +0.008152 | +0.003156 | +0.013449 | lower bound > 0 |
| Macro F1 | +0.007786 | +0.002622 | +0.013259 | lower bound > 0 |
| Occupied precision | +0.024594 | +0.015862 | +0.034368 | lower bound > 0 |
| Occupied recall | −0.012593 | −0.019813 | −0.006048 | lower bound ≥ 0 |

The first three required positive bounds pass. Occupied recall fails the non-negative-bound requirement, and its interval remains entirely below zero.

## Prediction disagreement

The mean A/B prediction-disagreement rate was `0.020887`, ranging from `0.019534` to `0.021788` across seeds. The error tradeoff is directional rather than random noise:

- A-correct/B-wrong cases were mostly VACANT cases (`36`–`46` per seed), consistent with A's higher precision and vacant recall.
- B-correct/A-wrong cases included more OCCUPIED cases (`12`–`15` per seed), consistent with B's higher occupied recall.
- Both-correct and both-wrong cases remained the majority of validation rows.

| Seed | Disagreement rows | Rate | A correct / B wrong | B correct / A wrong | Both correct | Both wrong |
|---:|---:|---:|---:|---:|---:|---:|
| 20260810 | 57 | 0.021412 | 41 | 16 | 2391 | 214 |
| 20260811 | 57 | 0.021412 | 38 | 19 | 2385 | 220 |
| 20260812 | 54 | 0.020286 | 37 | 17 | 2387 | 221 |
| 20260813 | 52 | 0.019534 | 37 | 15 | 2388 | 222 |
| 20260814 | 58 | 0.021788 | 40 | 18 | 2385 | 219 |

## Predeclared decision rule

The four-feature contract could be kept only if all conditions passed:

1. A wins Macro F1, accuracy, and occupied precision in at least 4/5 seeds.
2. B does not win occupied recall in more than 1/5 seeds.
3. Paired bootstrap lower bounds are positive for Macro F1, accuracy, and occupied precision, and non-negative for occupied recall.
4. A is no worse in at least 4/5 seeds for PR-AUC, ROC-AUC, Brier score, and log loss, using each metric's proper direction.

The checks resolve as follows:

| Check | Result |
|---|---|
| A Macro F1 ≥ 4/5 | PASS (`5/5`) |
| A accuracy ≥ 4/5 | PASS (`5/5`) |
| A occupied precision ≥ 4/5 | PASS (`5/5`) |
| B occupied recall wins ≤ 1/5 | FAIL (`5/5`) |
| Bootstrap Macro F1 lower bound > 0 | PASS |
| Bootstrap accuracy lower bound > 0 | PASS |
| Bootstrap occupied precision lower bound > 0 | PASS |
| Bootstrap occupied recall lower bound ≥ 0 | FAIL |
| A PR-AUC no worse ≥ 4/5 | PASS (`5/5`) |
| A ROC-AUC no worse ≥ 4/5 | PASS (`5/5`) |
| A Brier score no worse ≥ 4/5 | PASS (`5/5`, lower is better) |
| A log loss no worse ≥ 4/5 | PASS (`5/5`, lower is better) |

Because the burden-of-proof checks do not all pass, the predeclared rule selects `ADOPT_REDUCED_FEATURE_DIRECTION`. No alternative `INCONCLUSIVE` final state was allowed for this audit; method failure would have selected `DECISION_BLOCKED_BY_METHOD_FAILURE`, but the method checks passed.

## Engineering interpretation

The four-feature arm demonstrated modest but consistent offline predictive advantages across most evaluated metrics. The reduced arm demonstrated higher occupied recall under the inherited fixed threshold of `0.58`.

That recall comparison is explicitly threshold-conditioned. The `0.58` threshold originated in the current four-feature B5 lineage, while arm B has a different feature dimension, a different TRAIN-only scaler, different coefficients, and a different output distribution. Therefore:

```text
B_HIGHER_OCCUPIED_RECALL_AT_THRESHOLD_0_58
!= INHERENT_REDUCED_FEATURE_RECALL_SUPERIORITY
```

No threshold search or post-result retuning was performed. `B5_THRESHOLD_0_58_INHERITANCE_TO_REDUCED_MODEL = FORBIDDEN` for the future candidate phase. The result is not evidence that T/RH provide zero predictive information, and it is not evidence that a properly trained and thresholded future two-feature candidate will inherently have higher occupied recall.

The system decision is therefore a contract decision: avoid making additional T/RH device-contract fields mandatory until affirmative evidence clears the declared burden of proof. It is not a model-superiority ranking.

The decision is also not a claim that the reduced candidate is deployment-ready. It is only a direction for a new offline candidate. The new candidate still requires its own scaler, model, metadata, TFLite artifact, validation evidence, and lock. The physical SCD40 domain remains unvalidated.

## Next model phase: C-B6 — Reduced-Feature Candidate Development and Lock

`C-B6` is the required next model-development phase. It is separate from C-C, which remains reserved for device-domain acquisition and formal validation. C-B6 is conceptual and not started by this audit.

| C-B6 item | Required policy |
|---|---|
| Input | `CO2`, `CO2_slope` |
| Slope | existing `ENDPOINT_H150` contract; no redesign implied |
| Scaler | new scaler fit on TRAIN-only data for the two-feature subset |
| Model | newly trained two-feature candidate with new coefficients |
| Metadata/identity | new metadata, artifact identity, checksums, and candidate lock |
| Conversion | new Float/TFLite/INT8 conversion and equivalence evidence |
| Quantization | new INT8 calibration/quantization evidence |
| Threshold | own predeclared threshold-selection procedure; B5 `0.58` inheritance forbidden |
| Validation | development evidence using data already acknowledged as previously used; no claim of a new unbiased held-out result from the old LOCKED_TEST |
| Physical acquisition | forbidden before C-B6 candidate lock and revised protocol |

C-B6 must not remove columns from B5 in place, reuse the four-feature scaler, automatically reuse the B5 threshold, overwrite B5 artifacts, or use the old `LOCKED_TEST` for feature, threshold, or model selection. Threshold selection must be defined before final candidate evaluation, preferably with TRAIN-only internal cross-validation or an internal development split. Formal new-domain validation remains a later, explicitly authorized C-C2 activity.

## B5, C-C1, and C-C2 status

| Item | Current status |
|---|---|
| Current B5 feature order | `CO2, Temperature, Humidity, CO2_slope` |
| Current B5 artifact/scaler/threshold | unchanged |
| Current B5 inference on legacy team evidence | remains blocked by `B5_INFERENCE_BLOCKED_FEATURE_INCOMPLETE` |
| Current C-C1 protocol | four-feature version `1.0.0`, retained as historical evidence |
| Current C-C1 machine-readable status | final decision recorded separately; physical acquisition `HOLD` |
| Next model phase | `C-B6` — Reduced-Feature Candidate Development and Lock |
| B5 threshold inheritance to reduced candidate | forbidden; reduced threshold not finalized |
| Revised reduced protocol | not created; deferred until candidate lock |
| New physical measurement | not performed |
| C-C2 intake | not started |
| Formal SCD40 device-domain validation | not performed |
| C-D | not authorized |

The existing four-feature operator prompt must not be distributed for collection under this decision. A revised prompt may be written only after the reduced candidate lock and a separately authorized documentation update.

## Document alignment

| Artifact | Action | Reason |
|---|---|---|
| Master roadmap | Updated | Adds the final decision, HOLD boundary, reduced-candidate gate, and revised C-C sequence |
| C-C0 English report | Unchanged | Historical legacy evidence and blocked inference classification are preserved immutably |
| C-C0 Korean report | Unchanged | Same historical-boundary reason |
| C-C1 technical protocol | Updated with post-decision HOLD status | Four-feature protocol identity and required fields remain unchanged |
| C-C1 `protocol.json` | Added post-decision status only | Historical four-feature fields, ID, version, and B5 reference remain unchanged |
| C-C1 operator prompt | Updated with HOLD banner | Prevents distribution/use of the historical four-feature guide for collection |
| B5 model/scaler/lock | Unchanged | Current B5 is not silently converted into a reduced candidate |
| Team repository | Read-only | No team code, firmware, runtime, or team contract was modified |

## Machine-readable outputs and validation

| Artifact | Purpose |
|---|---|
| `datasets/co2/manifests/c_c1_model_input_decision/model_input_decision_result.json` | complete A/B result, seed results, bootstrap, disagreement, decision logic, B5 identity, and status |
| `datasets/co2/manifests/c_c1_model_input_decision/checksums.sha256` | checksum coverage for this decision report, result, audit implementation, and focused validator |
| `scripts/audit_co2_model_input_final_decision.py` | deterministic experiment implementation |
| `scripts/validate_co2_model_input_final_decision.py` | focused contract/result validator |
| `tests/test_co2_model_input_final_decision.py` | regression coverage for the decision result and status boundary |

The report and machine-readable result are the evidence for review. This scientific report does not authorize any repository lifecycle action. Repository lifecycle status is intentionally handled as a separate review decision after the user inspects the uncommitted diff.

## Validation results

| Check | Result | Note |
|---|---|---|
| Decision audit rerun | NOT PERFORMED | corrective addendum changed interpretation/phase metadata only; numeric experiment fields were preserved; corrected result SHA: `fdb3436ba205f3f47318ac29e67dc5aeb1cad277e80a3de8ed86244cff03755d` |
| Final decision validator | PASS | five-seed, direction-aware, HOLD-boundary, and checksum checks |
| Existing C-C1 protocol validator | PASS | protocol ID/version and historical four-feature fields preserved |
| Report provenance headers | PASS | Document Version, Author/Agent, Execution Date, Phase, and Status present |
| Focused tests | PASS | `12 passed` across the new decision tests and existing C-C1 tests |
| B5 standalone validator | PASS_WITH_WARNINGS | warnings remain INT8 saturation, host latency sanity-only, and device-domain validation incomplete |
| C-A6 raw-dependent integrity validator | BLOCKED | required `datasets/raw_archives/external_datasets/occupancy+detection.zip` is absent from this worktree; no raw-dependent claim is made |
| `git diff --check` | PASS | no whitespace errors |

The B5 artifact itself was not modified. The raw archive availability issue is an upstream verification limitation, not a model-input decision result.
