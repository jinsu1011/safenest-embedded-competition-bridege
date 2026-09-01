# Thermal V2 Team Multi-Model Test Staging

Date: 2026-08-31
Team repo: `jinsu1011/safenest-embedded-competition`
Standalone source: `sheepmeat/test` @ `4dccd25205af8994d29d03d75ebd0d7a7d6263e2` (PR #197 merged)

## Why this exists

The owner is not replacing the current Team Thermal model yet. This change stages
Candidate A and Candidate B next to the existing baseline so the operator can run
the **same** SafeNest stack three times and compare Thermal models.

`./run_safenest.sh` is unchanged and still starts the current Team baseline.

## Choices

| Choice | Selector | Meaning |
| --- | --- | --- |
| `baseline` | `thermal_public_sdt_fp32_active` | Current Team Thermal model |
| `a` | `thermal_tv2_candidate_a_a0_fp32_v1` | Thermal V2 Candidate A A0 |
| `b` | `thermal_tv2_candidate_b_seed42_fp32_test_v1` | Thermal V2 Candidate B seed-42 |

C1 is not in this selector. It is a matched control, not a user-facing prototype.

## Commands

```bash
./run_safenest_thermal_test.sh baseline
./run_safenest_thermal_test.sh a
./run_safenest_thermal_test.sh b
```

Remaining SafeNest arguments are forwarded:

```bash
./run_safenest_thermal_test.sh a --api-port 8080
```

The launcher only sets:

- `SAFENEST_THERMAL_TEST_MODE=1`
- `SAFENEST_THERMAL_MODEL_SELECTOR=<selector>`

then `exec`s `./run_safenest.sh`. There is no second backend.

## Artifact identity

### Baseline (default)

- Path: `RaspberryPi/Ondevice_AI/models/thermal/public_sdt/public_sdt_pooled_mlp_fp32_tflite_v1.tflite`
- SHA-256: `f88d65d76dbb21862e1f3cdff17cefb038a432047ded6ac8d5563bc8bc8c52ff`
- Preprocessing: existing per-frame min-max
- `active_runtime_selectors.thermal` remains this selector

### Candidate A (A_PREFERRED offline, Team test only)

- Team path: `RaspberryPi/Ondevice_AI/models/thermal/tv2/thermal_tv2_candidate_a_a0_fp32_v1.tflite`
- Size: 264704
- SHA-256: `a158a70c4735e28eec70b5a996f82c91f452b94bcc24c040838143f4a55b1985`
- Exact standalone G5 TFLite import (no reconversion)
- Preprocessing: `RELATIVE_THERMAL_APPEARANCE_V1` + `FRAME_ROBUST_P2_P98_V1`
- Status: `STANDALONE_G5_PASS_WITH_LIMITATIONS` / `A_PREFERRED_OFFLINE` / `CONTROLLED_TEAM_TEST`
- Not production. Not device validated.

### Candidate B (B_NOT_COMPETITIVE, comparison only)

- Source Keras (standalone, not committed to Team): `models/thermal/candidates/tv2_candidate_b/B_DEPTHWISE_SEPARABLE_seed42.keras`
- Source Keras SHA-256: `42563c3316e9e8511ab897aaa4dfd9a154887f3a0270d5dfb77a7a344cd3ff35`
- Team TFLite: `RaspberryPi/Ondevice_AI/models/thermal/tv2/thermal_tv2_candidate_b_seed42_fp32_test_v1.tflite`
- Team TFLite size: 24100
- Team TFLite SHA-256: `f5b9ecef8def2668bb65131671134e443c600e38c2575d4350e242f1abc0dfb4`
- Converter: TensorFlow 2.21.0, ordinary FP32, no quantization
- Preprocessing: same V2 robust path as A
- Status: `B_NOT_COMPETITIVE` / `CONTROLLED_COMPARISON_ONLY` / `NOT_PREFERRED`
- Packaging smoke only. Not scientifically revalidated.

## Preprocessing difference

Do not send A/B through the old min-max path.

- Baseline: existing Team `_prepare_float_frame` min-max (unchanged)
- A and B: per-frame `p2`/`p98` robust normalization

```text
p2 = percentile(frame, 2)
p98 = percentile(frame, 98)
y = clip((frame - p2) / max(p98 - p2, 1e-6), 0, 1)
```

Output is `[1,62,80,1]` float32, unit `RELATIVE_DIMENSIONLESS_NOT_CELSIUS`.

A and B share one implementation.

## Controlled-test semantics

- `active_runtime_selectors.thermal` is the default/current runtime and stays baseline.
- `controlled_test_runtime_selectors.thermal` is the operator opt-in allowlist.
- Unknown selector: fail closed.
- Test selector without `SAFENEST_THERMAL_TEST_MODE=1`: fail closed.
- Selection is once per process. Stop SafeNest and launch again to change models.

## Source geometry / device validation

Team Thermal UDP frames are already assembled as `[62,80]` (`height=62`, `width=80`)
before `ThermalInterpreter.predict`. This staging uses that array as received:

`TEAM_RUNTIME_62X80_AS_RECEIVED_EXPERIMENTAL_BRIDGE`

This does **not** prove MI48/G1 source equivalence.

`DEVICE_DOMAIN / SOURCE_GEOMETRY VALIDATION PENDING`

`LIVE_DEVICE_TEST = NOT_PERFORMED`

`LOCKED PUBLIC TEST = NOT ACCESSED`

## What was not changed

- `./run_safenest.sh`
- Risk thresholds / emergency logic / sensor weighting
- CO2, mmWave B23, PIR, voice, UI
- Baseline Thermal preprocessing
- Default Thermal selector

## Next step

After merge, pull onto the test machine/Pi and run the three launcher commands
for real integrated comparison. That live comparison is not claimed by this PR.
