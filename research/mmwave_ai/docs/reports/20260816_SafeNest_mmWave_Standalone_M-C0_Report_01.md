# SafeNest mmWave M-C0 correspondence audit

- Repository: `jinsu1011/safenest-embedded-competition`
- Branch: `codex/mmwave-m-c0-correspondence`
- Head at audit: `230f1b6d6dc63996dc0e3d89a023e3e153da79c8`
- Evidence-root used: `devices/mmwave/firmware`
- Decision: **`BLOCKED_PENDING_SIGNAL_CORRESPONDENCE`**
- Blocking reason: **`SIGNAL_CORRESPONDENCE_NOT_ESTABLISHED`**
- Correspondence evaluated: `true`
- Correspondence disproven: `false`
- Semantic correspondence: `UNDETERMINED`
- Temporal correspondence: `MEASURED_SUFFICIENT_FOR_PR18_PILOT_CAPTURE_ONLY`
- Valid 300-fresh windows, PRE_PR18_LEGACY_LOGS: `27`
- Valid 300-fresh windows, PR18_PILOT_CAPTURE: `9`
- Cross-group aggregate: **not reported**
- Model scoring/inference: **not executed**
- Raw modification/copy: **none**

## Method and write boundary

The audit logic and the raw MR60 evidence are kept separate; raw evidence is accessed read-only and is never modified, rewritten, or committed to the repository.

The script opened `259` regular files across the legacy and PR18 evidence roots in `rb` read-only mode and separately SHA-256 hashed every present file in the enumerated expected input set. All output paths were asserted to be outside both evidence roots. Raw MR60 JSONL/CSV remained in place and was not copied into the repository.

Numeric conventions:
- telemetry row cadence = `(timestamp_count - 1) / (last_timestamp - first_timestamp)`
- corrected fresh cadence = count of advancing reconstructed update instants, where `update_ms = round(timestamp_s*1000) - phase_age_ms`, divided by timestamp span
- superseded fresh cadence = count of `phase_age_ms` decreases divided by timestamp span; retained only to document the faulty earlier estimator
- phase-age p95 uses linear percentile interpolation; `>30,000 ms` is a reporting partition, not an official failure threshold
- 30-second fresh-window count uses fixed non-overlapping 30-second bins and counts bins with at least 300 reset-proxy events
- phase rpm = 60 divided by the median interval between positive crossings of the session-mean-centered phase; it is a signal diagnostic, not a paced-cue-to-label mapping
- interpolation and INT8 calculations are diagnostics only; the frozen BPF/resampling contract was not silently applied

## Expected evidence and SHA-256

| Expected item | Group | Status | Evidence path (repo-relative, personal path component redacted) | Records | SHA-256 |
|---|---|---|---|---:|---|
| `S001_NORMAL_D06` | `PRE_PR18_LEGACY_LOGS` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-25_occupied_d06_v1_360s__S001_NORMAL_D06.csv` | 2998 | `8a2b8cb8aa017110672fd3045f0d2b0228dfc7da6e40f6ce30e03dbca9cfee98` |
| `S001_NORMAL_D09` | `PRE_PR18_LEGACY_LOGS` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-25_occupied_d09_v1_360s__S001_NORMAL_D09.csv` | 2998 | `23c7eb303f679cd6134c84db8d735c756f70c39a21de8e41bca77b7e4889505b` |
| `S001_NORMAL_D12` | `PRE_PR18_LEGACY_LOGS` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-25_occupied_d12_v1_360s__S001_NORMAL_D12.csv` | 2998 | `4b52b83367f67e6f317bb3178c641372eb9f5f81c4b9535dba3008c5aef04617` |
| `S001_NORMAL_D15` | `PRE_PR18_LEGACY_LOGS` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-25_occupied_d15_v1_360s__S001_NORMAL_D15.csv` | 2999 | `cf98144314ba2e339a7dd660f2ce5e1296dc7d83bf81b994ba3e77d06245c60e` |
| `S001_BREATH_PACED_12_01` | `PRE_PR18_LEGACY_LOGS` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-25_breath_paced_12rpm__S001_BREATH_PACED_12_01.csv` | 2087 | `2502ff4d4f66613c062231ec3a3a2de8d3a045fdb1efe52731c87cff364478fb` |
| `S001_BREATH_PACED_12_02` | `PRE_PR18_LEGACY_LOGS` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-28_breath_paced_12rpm_explicit_v2_attempt03__S001_BREATH_PACED_12_02.csv` | 1774 | `6ea49a108e89c7b1627cb3f04009ea1ae0a05d13b82c54a92de5d3b72a799de1` |
| `S001_BREATH_PACED_15_03` | `PRE_PR18_LEGACY_LOGS` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-26_breath_paced_15rpm__S001_BREATH_PACED_15_03.csv` | 1779 | `5d630fd40a59a2b484581584ac311f85c507503bb5856eea6b84327b75b3c645` |
| `S001_BREATH_PACED_20_04` | `PRE_PR18_LEGACY_LOGS` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-26_breath_paced_20rpm__S001_BREATH_PACED_20_04.csv` | 1784 | `87e9292254cef55696f25d1550b295612f7f2721bb79dd61306e4c02650b88dd` |
| `S001_BREATH_PACED_20_05` | `PRE_PR18_LEGACY_LOGS` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-26_breath_paced_20rpm_deep__S001_BREATH_PACED_20_05.csv` | 1784 | `6bd13bd5de4242fc3147746031b236516947dfebb85923ef1421f88413444a06` |
| `2026-08-01_occupied_d09_v120_31min_attempt02` | `PRE_PR18_LEGACY_LOGS` | `PRESENT` | `devices/mmwave/firmware/logs/final/2026-08-01_occupied_d09_v120_31min_attempt02.jsonl` | 18574 | `7f9e9ac65377c6dc217af92f9dee2401b6162540e2245fce97acf2ed49368a34` |
| `M-C0-PILOT-DESKWORK-001` | `PR18_PILOT_CAPTURE` | `PRESENT` | `devices/mmwave/device_measurements/pilot/M-C0-PILOT-DESKWORK-001.raw.jsonl` | 1799 | `368e6a16e897b9231ff5fcdecd3edcc5b725a0a4dc6b20dee1e3162405bc2876` |
| `M-C0-PILOT-STATIONARY-001` | `PR18_PILOT_CAPTURE` | `PRESENT` | `devices/mmwave/device_measurements/pilot/M-C0-PILOT-STATIONARY-001.raw.jsonl` | 1799 | `e2b832fd3a72f18b4c3a370738c10e58c0269283dac218ae2d7d4dad48036f6f` |

Present expected files: `12` / `12`. Missing items were recorded as `KNOWN_BUT_NOT_PROVIDED`; they were not silently skipped.

Evidence groups are kept separate: `PRE_PR18_LEGACY_LOGS` contains the nine legacy CSVs and the long JSONL; `PR18_PILOT_CAPTURE` contains the two 1799-record pilot expectations. Pilot cadence is never merged into legacy cadence.

### PR18 retrieval and path search

| Command | Result |
|---|---|
| `git fetch origin pull/18/head:pr18-head` | `SUCCESS: refs/pull/18/head -> pr18-head` |
| `git fetch origin 62eb0d867cfa02295c9a1d023b813134c434b8eb` | `SUCCESS: 62eb0d867cfa02295c9a1d023b813134c434b8eb -> FETCH_HEAD` |
| `git fetch origin refs/pull/18/head` | `SUCCESS: refs/pull/18/head -> FETCH_HEAD` |

| Ref | Path checked | Result |
|---|---|---|
| `HEAD` | `devices/mmwave/device_measurements/` | `NOT_FOUND` |
| `pr18-head@62eb0d867cfa02295c9a1d023b813134c434b8eb` | `devices/mmwave/device_measurements/` | `FOUND` |
| `HEAD` | `devices/mmwave/firmware/device_measurements/M-C0-PILOT-DESKWORK-001.jsonl` | `NOT_FOUND` |
| `HEAD` | `devices/mmwave/firmware/device_measurements/M-C0-PILOT-STATIONARY-001.jsonl` | `NOT_FOUND` |
| `HEAD` | `devices/mmwave/firmware/device_measurements/M-C0-PILOT-DESKWORK-001/records.jsonl` | `NOT_FOUND` |
| `HEAD` | `devices/mmwave/firmware/device_measurements/M-C0-PILOT-STATIONARY-001/records.jsonl` | `NOT_FOUND` |
| `pr18-head@62eb0d867cfa02295c9a1d023b813134c434b8eb` | `devices/mmwave/device_measurements/M-C0-PILOT-DESKWORK-001.jsonl` | `NOT_FOUND` |
| `pr18-head@62eb0d867cfa02295c9a1d023b813134c434b8eb` | `devices/mmwave/device_measurements/M-C0-PILOT-STATIONARY-001.jsonl` | `NOT_FOUND` |
| `pr18-head@62eb0d867cfa02295c9a1d023b813134c434b8eb` | `devices/mmwave/device_measurements/M-C0-PILOT-DESKWORK-001/records.jsonl` | `NOT_FOUND` |
| `pr18-head@62eb0d867cfa02295c9a1d023b813134c434b8eb` | `devices/mmwave/device_measurements/M-C0-PILOT-STATIONARY-001/records.jsonl` | `NOT_FOUND` |
| `pr18-head@62eb0d867cfa02295c9a1d023b813134c434b8eb` | `devices/mmwave/device_measurements/pilot/M-C0-PILOT-DESKWORK-001.raw.jsonl` | `FOUND` |
| `pr18-head@62eb0d867cfa02295c9a1d023b813134c434b8eb` | `devices/mmwave/device_measurements/pilot/M-C0-PILOT-STATIONARY-001.raw.jsonl` | `FOUND` |

## Per-session measured findings

| Group | Session | Records | Row Hz | Fresh 0x0A13 Hz | Phase rpm | Phase age min / median / p95 / max ms | >30 s | 300-fresh windows | Interp RMSE |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|
| `PRE_PR18_LEGACY_LOGS` | `S001_NORMAL_D06` | 2998 | 9.994964166 | N/A | 20.04468266 | None / None / None / None | None | 0 | N/A |
| `PRE_PR18_LEGACY_LOGS` | `S001_NORMAL_D09` | 2998 | 9.99613096 | N/A | 19.699214478 | None / None / None / None | None | 0 | N/A |
| `PRE_PR18_LEGACY_LOGS` | `S001_NORMAL_D12` | 2998 | 9.995797563 | N/A | 20.266696872 | None / None / None / None | None | 0 | N/A |
| `PRE_PR18_LEGACY_LOGS` | `S001_NORMAL_D15` | 2999 | 9.998365844 | N/A | None | None / None / None / None | None | 0 | N/A |
| `PRE_PR18_LEGACY_LOGS` | `S001_BREATH_PACED_12_01` | 2087 | 9.995304219 | N/A | 10.598330195 | None / None / None / None | None | 0 | N/A |
| `PRE_PR18_LEGACY_LOGS` | `S001_BREATH_PACED_12_02` | 1774 | 9.995433558 | N/A | 12.18605948 | None / None / None / None | None | 0 | N/A |
| `PRE_PR18_LEGACY_LOGS` | `S001_BREATH_PACED_15_03` | 1779 | 9.994097974 | N/A | 14.928893032 | None / None / None / None | None | 0 | N/A |
| `PRE_PR18_LEGACY_LOGS` | `S001_BREATH_PACED_20_04` | 1784 | 9.994226554 | N/A | 20.170279064 | None / None / None / None | None | 0 | N/A |
| `PRE_PR18_LEGACY_LOGS` | `S001_BREATH_PACED_20_05` | 1784 | 9.992994255 | N/A | 20.030636268 | None / None / None / None | None | 0 | N/A |
| `PRE_PR18_LEGACY_LOGS` | `2026-08-01_occupied_d09_v120_31min_attempt02` | 18574 | 9.986342911 | 8.419003785 | 19.264097775 | 0.0 / 12.0 / 195627.0 / 288530.0 | 0.139173038 | 27 | 0.008928878 |
| `PR18_PILOT_CAPTURE` | `M-C0-PILOT-DESKWORK-001` | 1799 | 9.993996932 | 9.988438535 | 20.347847528 | 0.0 / 12.0 / 15.0 / 111.0 | 0.0 | 4 | 0.017641003 |
| `PR18_PILOT_CAPTURE` | `M-C0-PILOT-STATIONARY-001` | 1799 | 9.993330369 | 9.993330369 | 22.329196977 | 0.0 / 12.0 / 15.0 / 17.0 | 0.0 | 5 | 0.013461468 |

### Freshness estimator re-audit

The previous implementation counted only age decreases:

```python
for previous, current in zip(age_pairs, age_pairs[1:]):
    if current[2] < previous[2]:
        reset_indices.append(current[0])
        reset_times.append(current[1])
span = age_pairs[-1][1] - age_pairs[0][1]
cadence = len(reset_times) / span if span > 0 else None
```

| Session | Age decrease (`RETRACTED_FAULTY_ESTIMATOR`) | Phase change or age decrease | Age < prior row interval | Reconstructed update advances | Selected |
|---|---:|---:|---:|---:|---|
| `2026-08-01_occupied_d09_v120_31min_attempt02` | 8006 / 4.30467137 Hz | 14250 / 7.661949415 Hz | 15658 / 8.419003785 Hz | 15658 / 8.419003785 Hz | `reconstructed_update_instant_advances` |
| `M-C0-PILOT-DESKWORK-001` | 662 / 3.679658492 Hz | 1642 / 9.126887076 Hz | 1797 / 9.988438535 Hz | 1797 / 9.988438535 Hz | `reconstructed_update_instant_advances` |
| `M-C0-PILOT-STATIONARY-001` | 633 / 3.518230325 Hz | 1643 / 9.131836372 Hz | 1798 / 9.993330369 Hz | 1798 / 9.993330369 Hz | `reconstructed_update_instant_advances` |

The methods materially disagree. Phase-value transitions are only a lower bound because a genuinely new quantized phase may repeat the previous value. The age-versus-row-interval method and reconstructed-update method independently agree for both pilots. The reconstructed method is selected because it directly tests whether the source update instant advances; no methods are averaged. Full definitions, source SHA-256 values, and computations are in `datasets/mmwave/manifests/M-C0_correspondence_audit/freshness_estimator_reaudit.json`.

### PR18 pilot cadence finding

Verdict: **`B_2026_07_26_LEGACY_CAPTURE_METHOD_LIMITATION_SUPPORTED`**. Both corrected pilot cadences approach their telemetry row cadences, and pilot phase_age_ms p95 is 15 ms versus 195627 ms in the legacy long log. The earlier (a) verdict was based on a faulty phase-age-decrease estimator that undercounted always-low pilot age values.
The corrected comparison uses advancing `timestamp-phase_age_ms` update instants and never merges pilot statistics with `PRE_PR18_LEGACY_LOGS`. Legacy `phase_age_ms` p95 is `195627 ms`, while both pilot p95 values are `15 ms`; the four-order-of-magnitude freshness-age difference is consistent with the corrected (b) verdict and incompatible with the retracted ~3.5 Hz interpretation.

### Corrected 300-fresh-sample window audit

- `PRE_PR18_LEGACY_LOGS` valid windows: `27`; this value is reported separately and is never added to the other evidence group.
  - `2026-08-01_occupied_d09_v120_31min_attempt02`: window counts `[300, 300, 299, 300, 299, 300, 299, 300, 300, 269, 300, 299, 300, 299, 299, 300, 299, 300, 299, 299, 300, 300, 299, 300, 299, 299, 300, 299, 300, 299, 300, 300, 299, 300, 299, 300, 299, 300, 299, 299, 300, 299, 300, 300, 299, 300, 299, 300, 299, 300, 300, 299, 114, 0, 0, 0, 0, 0, 0, 0, 0, 0]`; valid `27` / evaluated `62`; maximum `300`. Computation: anchor fixed non-overlapping 30 s bins at the first telemetry timestamp; include the first identifiable timestamp-age update, then each advancing reconstructed update instant; count bins with >=300 fresh samples
- `PR18_PILOT_CAPTURE` valid windows: `9`; this value is reported separately and is never added to the other evidence group.
  - `M-C0-PILOT-DESKWORK-001`: window counts `[300, 300, 300, 300, 299, 299]`; valid `4` / evaluated `6`; maximum `300`. Computation: anchor fixed non-overlapping 30 s bins at the first telemetry timestamp; include the first identifiable timestamp-age update, then each advancing reconstructed update instant; count bins with >=300 fresh samples
  - `M-C0-PILOT-STATIONARY-001`: window counts `[300, 300, 300, 300, 299, 300]`; valid `5` / evaluated `6`; maximum `300`. Computation: anchor fixed non-overlapping 30 s bins at the first telemetry timestamp; include the first identifiable timestamp-age update, then each advancing reconstructed update instant; count bins with >=300 fresh samples

The legacy JSONL yields a corrected fresh cadence of `8.419003785 Hz` and `27` valid 300-fresh-sample windows because its `phase_age_ms` field permits timestamp-age reconstruction. The legacy-CSV-derived windows remain `0/620` contract-proven because those CSVs carry no freshness field, so fresh provenance cannot be proven for them; this is a provenance limitation, not a contradiction of the JSONL cadence result.

## Preserved measurement corrections

- `S001_NORMAL_D15`: the finite `range_m` sample standard deviation is `2.93759692` cm, computed from `2639` rows in `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-25_occupied_d15_v1_360s__S001_NORMAL_D15.csv`. The same file's `resp_phase` population std is `0.0`; the frozen value is the phase/vitals signal, not distance.
- `S001_BREATH_PACED_12_01` is not treated as a 12-rpm ground truth: `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/DELIVERY_NOTES.md` records an actual trial of approximately `6.06` rpm. The cue remains metadata only.
- Existing project records retain the corrected phase periods `12.34` / `15.00–15.01` / `20.00` rpm versus vendor medians `14.0` / `19.0` / `23.0` (`docs/operations/PROJECT_PROGRESS.md` and the delivery notes). These are measurement notes and do not create a paced-rpm-to-class mapping.
- The phase-rpm values in the table are independently recomputed from each listed evidence file using the positive-crossing formula above; they are not substituted with paced cues or vendor medians.

### Question 1 — signal-semantic correspondence

`breath_phase`/`resp_phase` was present and periodic components were measurable in the supplied captures. That establishes a phase-like telemetry signal, not equivalence to the frozen Phase-B `resp_phase_model_ready_bpf_zscore` semantic. No independent canonical reference waveform is present, so semantic correspondence is `UNDETERMINED`; this is not a semantic disproof (`correspondence_disproven=false`).

### Question 2 — `breath_rate_raw` as waveform input

The measured answer is **no**. The static pipeline scan found waveform input paths `["devices/mmwave/firmware/export_mmwave_csv.py", "devices/mmwave/firmware/src/main.cpp", "devices/mmwave/src/mr60_esp_adapter.py", "ondevice_ai/adapters/mmwave_csv_adapter.py", "ondevice_ai/inference/mmwave_interpreter.py"]` and recorded `breath_rate_raw` only in telemetry/export/diagnostic matches. Per-session parsing also used `{"legacy_csv": "resp_phase", "long_jsonl": "breath_phase", "pr18_pilot": "breath_phase"}` as the waveform field.

### Question 3 — row cadence vs fresh cadence

The table reports telemetry and corrected fresh cadence separately and by evidence group. Legacy CSV has no `phase_age_ms`/0x0A13 freshness field, so its fresh cadence is `N/A`, not assumed to be the row cadence. For JSONL sessions, fresh cadence is reconstructed from advancing `timestamp-phase_age_ms` update instants. The old age-decrease proxy is retained only as a superseded value; PR18 pilot statistics remain within `PR18_PILOT_CAPTURE`.

### Question 4 — timestamp integrity

Per-session gaps, duplicates, non-monotonic timestamps, timestamp freezes, sequence loss, and freeze flags are in `offline_contract_correspondence.json` under `per_session[].timestamp_integrity`. Long-log measured numbers are `gap_count=0`, `duplicate_timestamp_count=0`, `nonmonotonic_timestamp_count=0`, `timestamp_freeze_intervals=0`, `freeze_flag_count=2566`, and `sequence_missing_count=0`; all are computed from `devices/mmwave/firmware/logs/final/2026-08-01_occupied_d09_v120_31min_attempt02.jsonl`. Gap counts use the diagnostic threshold stated above; no official phase-age failure threshold was invented.

### Question 5 — `phase_age_ms` distribution

The long JSONL's min/median/p95/max and fraction over 30 seconds are measured in the table and JSON. Legacy CSV sessions report `FIELD_NOT_PRESENT`, so no phase-age statistic is fabricated.

### Question 6 — 300 genuinely fresh samples

The corrected results are reported without a cross-group aggregate: `PRE_PR18_LEGACY_LOGS=27` and `PR18_PILOT_CAPTURE=9`. The counts use advancing reconstructed update instants in fixed 30-second bins anchored at each session's first telemetry timestamp. Legacy CSV sessions are separately not provable because freshness metadata is absent; their historical adapter result remains 0/620.

### Question 7 — interpolation

Interpolation was **not applied** to any audit input. Where phase-age reset proxies existed, linear interpolation was simulated only to quantify distortion; its RMSE/MAE/max-absolute error are reported per session. For `devices/mmwave/firmware/logs/final/2026-08-01_occupied_d09_v120_31min_attempt02.jsonl`, simulated linear interpolation was not applied; the proxy distortion is `RMSE=0.008928878`, `MAE=0.004631681`, and `max_abs=0.084` over `15688` samples. The method remains unresolved.

### Question 8 — BPF + z-score identity

The answer is **not established as identical**. The frozen contract is `M-B10B_SELECTED_REAL_CANDIDATE_BPF_ZSCORE_V1` with 0.1–0.5 Hz, order 4, zero-phase filtfilt, mean `0.0031162832173884064`, and std `2.955399434649939`. Raw phase statistics and a clearly labeled affine-only proxy are in each session result; no BPF was silently substituted.

### Question 9 — pre/post INT8 distribution

The JSON contains diagnostic before-INT8, after-INT8-dequantized, quantized integer, saturation, and quantization-error distributions using scale `0.041720833629369736` and zero-point `-3`. For the long log, before-INT8 `n=18574`, `mean=-0.000530514`, `std=0.054656118`, `p05=-0.089029009`, `p95=0.086920135`, `min=-0.298814527`, `max=0.317007476`; after-INT8 dequantized `n=18574`, `mean=-0.000914202`, `std=0.055741911`, `p05=-0.083441667`, `p95=0.083441667`, `min=-0.292045835`, `max=0.333766669`; quantized saturation is `0.0`. No training-reference file was available in the target worktree, so a numeric training comparison was not fabricated. These are diagnostic affine values because BPF was not reconstructed.

### Question 10 — 620/620 all-APNEA collapse stage

The legacy adapter path `ondevice_ai/adapters/mmwave_csv_adapter.py` was replayed as input-side forensics only: 300 source rows per window, 30-row stride, and nominal 10 Hz `np.interp`. It reconstructs `620` windows, matching the historical 620 count. The evidence-proven fresh-sample fraction distribution is `min=0.0`, `median=0.0`, `mean=0.0`, `max=0.0` with status `EVIDENCE_PROVEN_FRACTION_ZERO_ACTUAL_FRACTION_UNKNOWN`. The actual fraction remains `UNKNOWN_NOT_OBSERVABLE_FROM_LEGACY_CSV` because the CSV has no `phase_age_ms`/0x0A13 field; the zeros are `fresh_sample_count_proven / 300`, not fabricated actual freshness measurements. Across `186000` evaluated sample slots, the adjacent-equal stale-repeat proxy is `53820 / 186000 = 0.289354839`; across the same slots, interpolated or synthesised samples are `169041 / 186000 = 0.908822581` (`synthesised_sample_count=0`). Windows meeting the 300-fresh-sample contract are `0 / 620`. The earliest measured divergence from `M-B10B_SELECTED_REAL_CANDIDATE_BPF_ZSCORE_V1` is `LEGACY_CSV_WINDOW_GENERATION_FRESHNESS_PROVENANCE` before BPF_ZSCORE. These headline values and their numerator/denominator computations are recorded in `datasets/mmwave/manifests/M-C0_correspondence_audit/620_window_input_forensics.json` under `headline`.
The historical 620/620 all-APNEA exploratory run is attributable here only to an input contract violation: the measured input composition contains 53820/186000 stale-repeat slots and 169041/186000 interpolated slots, 0/620 windows meet the 300-fresh-sample contract, and the first established divergence is LEGACY_CSV_WINDOW_GENERATION_FRESHNESS_PROVENANCE. These input-side facts do not measure or characterize model performance.

## Decision

**`BLOCKED_PENDING_SIGNAL_CORRESPONDENCE`** with `semantic_correspondence=UNDETERMINED`, `temporal_correspondence=MEASURED_SUFFICIENT_FOR_PR18_PILOT_CAPTURE_ONLY`, separately reported valid windows `PRE_PR18_LEGACY_LOGS=27` and `PR18_PILOT_CAPTURE=9`, `correspondence_evaluated=true`, and `correspondence_disproven=false`. Temporal correspondence now holds for the PR18 pilots, but semantic correspondence remains `UNDETERMINED` and exact frozen BPF/z-score preprocessing correspondence remains `NOT_ESTABLISHED`. The decision therefore stands: temporal sufficiency alone does not authorize exploratory inference or any model invocation.

## What remains unknown

- Exact physical/numeric semantic mapping from MR60 `breath_phase` to the frozen Phase-B input.
- Official phase-age failure threshold; 30 seconds is only a reporting partition here.
- Direct 0x0A13 packet identity/update cadence versus phase-age reset proxy.
- Approved interpolation/resampling method and its acceptable distortion.
- Formal pre-BPF/post-BPF training-distribution comparison for MR60.
- Stage responsible for the historical all-APNEA collapse.
- Independent M-C1 reference hardware, sample size, and paced-rpm-to-label mapping.
- Official measurement distances; practical starting points and freeze observations remain evidence, not a frozen protocol.

## Boundaries preserved

No retraining, preprocessing change, INT8 recalibration, LOCKED_TEST reopening, M-C1 capture, clinical apnea claim, paced-cue class mapping, or raw-file modification was performed.
