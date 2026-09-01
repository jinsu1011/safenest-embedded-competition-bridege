# MH-Z19B Pi ingest into frozen C-B6 H150

| Item | Value |
|---|---|
| Date | 2026-08-31 |
| Repository | `jinsu1011/safenest-embedded-competition` |
| Branch | `feature/pi-co2-h150-mhz19b-ingest` |
| Base | `origin/main` |
| ESP32 sketches | not in this change (parallel `feature/esp32-mhz19b-co2-v2-port`) |
| Model / scaler / threshold | unchanged (`C_B6_REDUCED_CO2_SLOPE_CANDIDATE_001`, TRAIN-only scaler, **0.43**) |

SCD40 is out of service. MH-Z19B is the live CO₂ source. ppm-unit match is not domain equivalence. This note is the Pi ingest contract only.

## Frozen slope (unchanged)

`RaspberryPi/Runtime/ai/co2_canonical_runtime.py` `CO2SlopeWindowBuilder` still implements `CO2_SLOPE_FEATURE_PROFILE_001`:

- `feature_order`: `CO2`, `CO2_slope`
- method: `ENDPOINT_DIFFERENCE` / protocol name `ENDPOINT_H150`
- unit: ppm/min
- history: 150 s, `PAST_ONLY`
- gap reset: valid-event source-clock gap > 90 s restarts history
- interpolation / forward-fill / synthetic 60 s samples: forbidden
- history key: `(device_id, boot_id, measurement_event_id)` only

Pi does not invent event ids from packet `seq`, LCD `/health` `fresh`, or `age_seconds`. Same `event_id` on a later TCP packet is a cached retransmission and does not advance H150.

## Wire fields

Required for H150 (already on `safenest.telemetry.v1`; still optional-together so legacy packets decode):

- `co2_ppm`, `valid.co2`
- `boot_id`, `seq`, `uptime_ms`
- `co2_measurement_event_id`, `co2_measurement_monotonic_ms`, `co2_measurement_event_valid`

Optional MH-Z19B metadata (preserve when present; ignore when absent):

| Field | Meaning |
|---|---|
| `co2_sensor_model` | `"MH-Z19B"` |
| `co2_event_identity_class` | `"INFERRED_UART_SAMPLE"` |
| `co2_preheat_complete` | bool; 3 min Winsen preheat |
| `abc_enabled` | true / false / omit |
| `configured_range_ppm` | 2000 / 5000 / 10000 / omit |

`INFERRED_UART_SAMPLE` means a checksum-valid UART `0x86` sample accepted under firmware poll policy. It is **not** SCD40 `getDataReady` conversion. Same event id on later TCP packets is retransmission.

Parallel firmware (not this PR) currently emits `co2_preheat` as a bool alias. Pi maps that to `co2_preheat_complete`. Canonical `co2_preheat_complete` wins if both are present. `abc_enabled` and `configured_range_ppm` are not on current main firmware; they are parsed when the firmware PR adds them.

## H150 gating (live Runtime path)

`OnDeviceAIPipeline.observe_telemetry` feeds `CO2SlopeWindowBuilder.observe` only when all of:

1. `co2_measurement_event_valid` is true
2. event id is a new `(device_id, boot_id, event_id)` key (builder still dedupes)
3. ppm and source clock are finite
4. `co2_preheat_complete` is **true** (missing = unknown = not model-eligible)

Preheat samples may still appear on the wire, in the logger, and on LCD `/health`. They are not C-B6 inputs. A sensor-model change resets slope/baseline history so SCD40 and MH-Z19B sessions are not pooled.

Missing event triple: decode succeeds (legacy); formal slope/model input is `FEATURE_UNAVAILABLE` / no canonical clock. Transport-only `co2_ppm` may still be logged.

## `/health` (LCD `:8080`)

`SensorStore` no longer drops event identity. Snapshot keys include the event triple, `co2_sensor_model`, `co2_event_identity_class`, and `co2_preheat_complete`. `fresh` / `age_seconds` remain **transport** freshness.

## Remaining limitation

Identity is inferred UART sample, not SCD40 data-ready. This PR does not start C-C2 and does not claim Accuracy/F1.
