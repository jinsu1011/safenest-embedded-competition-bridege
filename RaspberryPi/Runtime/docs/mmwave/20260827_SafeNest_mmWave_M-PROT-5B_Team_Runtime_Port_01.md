# M-PROT-5B — Team repository Pi-runtime port (B23)

Software integration only. **No physical Raspberry Pi. No live MR60.**
`PI_TORCH_NOT_LIVE_VERIFIED`. M-PROT-5C remains deferred.

## Old active path

`RaspberryPi/Runtime/ai/mmwave_canonical_runtime.py` (M-N4, 30 s ~8 Hz **240** tensor)
→ spectral apnea contradiction
→ `LazyModel("mmwave")` / M-N9 INT8
→ `NORMAL / RAPID_OR_ABNORMAL / APNEA-proxy`

That path is **legacy / non-default**. Modules remain on disk for isolated tests.
There is no B23→M-N9 fallback, no spectral physiology override, and no vendor-RR model input.

## New active path

ESP nested telemetry
→ parse `breath_phase`
→ parse physical `ts_monotonic_ms / 1000` (**do not** subtract `phase_age_ms`)
→ parse nested `mmwave.seq` as `mmwave_sequence`
→ boot_id / tri-state presence
→ SW-01 / M-PROT-3 `Sample` (`Sample.seq` = nested phase seq)
→ R1 (exactly 300 @ 10 Hz)
→ R2 (621 features)
→ frozen B23 (`pytorch`)
→ existing `AIResult` / `/api` mmWave state

Not used: ESP → legacy M-N4 `ts - phase_age` reconstruction → M-N9.

Presence comes only from explicit occupancy (`human_detected_raw` / `presence` + `presence_available`).
`null` stays unavailable; it is never converted to `false`. ABSENT ≠ APNEA.
`breath_rate_raw` is diagnostic only and is never B23 model input.

### ESP producer mapping (firmware unchanged)

| ESP field | B23 / M-PROT-3 use |
|---|---|
| `mmwave.breath_phase` | `Sample.phase` |
| `mmwave.ts_monotonic_ms` | `Sample.t = ts_monotonic_ms / 1000.0` (already physical) |
| `mmwave.phase_age_ms` | freshness gate only (`0 ≤ age ≤ 1000 ms`); **not** subtracted |
| `mmwave.seq` | `Sample.seq` / `mmwave_sequence` (physical phase-event identity) |
| outer JSON / header `seq` | transport publication identity only |
| `boot_id` | hard reset boundary; M-PROT-3 `session_id = boot:{boot_id}` |
| packet `session_id` | provenance only when `boot_id` is present; not an independent history |
| `human_detected_raw` | tri-state presence gate |
| `breath_rate_raw` | logged/diagnostic; `Sample.scalar_rr` stays `None` |

Republication of the same nested `mmwave.seq` across 100 ms snapshots does not create another waveform sample. A nested-seq jump `> 1` increments M-PROT-5C diagnostic counters (`previous`, `current`, `delta`, `missing_phase_event_count`) and is a frozen M-PROT-3 temporal discontinuity: the previous causal window is not bridged; a new admission starts; the runtime stays alive and returns `WINDOW_NOT_READY` until coverage is rebuilt.

Invalid/stale source (null phase, stale `phase_age_ms`, missing timestamp, missing nested seq) invalidates any previously ready window. `boot_id` change resets immediately, before inspecting the first new-boot packet.

`valid.respiration` / vendor RR validity does **not** gate B23 waveform admission. `Sample.health_ok` is waveform/source health. Team `SensorStateManager` treats mmWave as valid when a structural B23 phase source is present (`breath_phase`, `ts_monotonic_ms`, `phase_age_ms`, `mmwave_sequence`) **or** vendor respiration **or** vendor heart. Missing phase and missing both vendor scalars remains INVALID.

ESP firmware is **not** modified in M-PROT-5B.

## Risk semantic

B23 does not emit the old three classes. Eligible prototype output is mapped with
`score=0.0` and `risk_contribution_deferred=True`. No APNEA invention.
When B23 is unavailable, the existing vendor-RR **risk rule_fallback** still applies
(unchanged formula). That rule is not B23 model input.

## Identities (unchanged)

| Item | Value |
|---|---|
| Artifact SHA-256 | `8f7de6f50d6ff62ff9b0ebfaed0b1fccd8d194c7e33781bc5b93366fae251a2c` |
| Parameter SHA-256 | `6db949c242e25888dd20c3fc8e2305af03448aa229e3ca73e4159216a266d78e` |
| Scaler content SHA | `5a2583b5b5064be5480b0cf56f2a2c12d40a4a2d005eb087dc8e12106881159c` |
| Source repo / SHA | `https://github.com/sheepmeat/test.git` / `809b78626b442f146eccd73595f239b93de3ae2e` |
| Target base | `aea6083ef2dd6fea8d8e911ebec8dcdc2e3e89e9` |

## Source file classification

| Source | Team destination | Action |
|---|---|---|
| `adapters/mmwave_sw01_interface_checker.py` | `Runtime/ai/mmwave_prototype/` | COPY_AS_RUNTIME_MODULE (imports retargeted) |
| `adapters/mmwave_sw01_source.py` | same | COPY_AS_RUNTIME_MODULE |
| `adapters/mmwave_r1_sensor_independent_trace.py` | same | COPY_AS_RUNTIME_MODULE |
| `adapters/mmwave_r2_representation_features.py` | same | COPY_AS_RUNTIME_MODULE |
| `adapters/mmwave_m_prot_2_b23_runtime.py` | same | ADAPT_INTO_TEAM_RUNTIME (asset root = Ondevice_AI) |
| `adapters/mmwave_m_prot_3_integration_runtime.py` | same | ADAPT_INTO_TEAM_RUNTIME |
| `scripts/mmwave_m_pv2_candidate_training.py` | `Runtime/ai/mmwave_prototype/trace_model_support.py` | ADAPT — runtime extract only, **no sklearn** |
| `models/mmwave/m_pv2/family_b/candidate_seed_23.pt` | `Ondevice_AI/models/mmwave/m_prot_b23/` | COPY_AS_MODEL_ASSET |
| `datasets/mmwave/manifests/M-PV2_candidate_training/scaler_statistics.json` | same dir | COPY_AS_CONFIG |
| Team `ai/pipeline.py` | — | REPLACE_ACTIVE_MMWAVE |
| Team `ai/mmwave_canonical_runtime.py` | — | LEGACY_RETAIN_NONACTIVE |
| Team `ai/mmwave_spectral_runtime.py` | — | LEGACY_RETAIN_NONACTIVE (non-authoritative) |
| Thermal / CO2 / PIR / LCD / Web / risk formula | — | PRESERVE |

## Dependencies

- Mac/dev: `torch>=2.1.0` in `Ondevice_AI/requirements.txt` and `requirements-mac.txt`
- Pi install file: torch **commented**; scipy added for R1 resampling
- `SCIKIT_LEARN_RUNTIME_DEPENDENCY`: **NO** for the B23 path (runtime extract)

## What remains for M-PROT-5C

Install/verify PyTorch on the Pi, pull this branch, run live MR60 smoke.
Do not start M-PROT-5C from this report.

Live runtime should expose nested phase-seq jump diagnostics already prepared here:
previous nested phase seq, current nested phase seq, delta, detected missing phase-event count.
Do not redesign ESP firmware in 5C solely for latest-only 100 ms publication.

## ESP producer contract (M-PROT-5B update)

```
ESP_FIRMWARE_CHANGED: NO
PHYSICAL_TIMESTAMP_SEMANTIC: ts_monotonic_ms is physical observation timestamp
PHASE_AGE_USAGE: FRESHNESS_ONLY
DOUBLE_AGE_SUBTRACTION: FIXED / NOT_PRESENT_IN_NEW_B23_PATH
NESTED_MMWAVE_SEQ_PARSED: YES
B23_SOURCE_SEQUENCE: NESTED_MMWAVE_SEQ
OUTER_SEQUENCE_ROLE: TRANSPORT_PUBLICATION_ONLY
REPUBLISH_DEDUPLICATION: PASS
BOOT_ID_BOUNDARY: PASS
LIVE_PHASE_SEQ_JUMP_MONITOR: PREPARED_FOR_M_PROT_5C
M_PROT_3_FROZEN_SEQ_BOUNDARY_RESTORED: YES
SEQ_JUMP_CAUSAL_WINDOW_BRIDGED: NO
STALE_PHASE_INVALIDATES_READY_WINDOW: YES
VENDOR_RR_VALIDITY_GATES_B23: NO
VENDOR_HEART_VALIDITY_GATES_B23: NO
PHASE_VALIDITY_RECOGNIZED_BY_STATE_MANAGER: YES
```
