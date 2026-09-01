# Phase 0: Read-Only Audit Report

## 1. Current Branch / HEAD
- Branch: `main` (Currently switched to `feature/thermal-v5-real-validation`)
- HEAD: `9839061` (Merge PR #19)

## 2. Thermal Driver
- File: `devices/thermal/src/thermal44_driver.py` & `esp32_sensor_node.ino`
- Contains base logic for I2C and SPI, but Python driver throws `HardwareBackendUnavailable` unless real HW is attached.

## 3. Frame Parser
- File: `devices/thermal/src/frame_parser.py`
- Parses 4960 raw float values to (62, 80). Validates shape and NaN/Inf.
- SNST Protocol parsing in `shared/protocols/snst.py`.

## 4. Mock Implementation
- File: `devices/thermal/src/mock_sensor.py`
- Generates synthetic 22.0°C background with 34.5°C fall blob or 33.0°C human blob.

## 5. Real Hardware Interface (Implemented vs Missing)
- Implemented: ESP32 reads from sensor via I2C/SPI and sends via TCP (port 9000).
- Missing: End-to-end Python pipeline from TCP socket -> Parser -> AI has not been validated on real Raspberry Pi hardware.

## 6. Expected Raw Frame Format
- 5040 words (10080 bytes).
- Words 0-79: Header (Counter, VDD, Die Temp, etc).
- Words 80-5039: 4960 pixels.

## 7. Expected Frame Dimensions
- 62 x 80 pixels.

## 8. Preprocessing
- Min-Max normalization (0.0 to 1.0) -> INT8 Quantization (scale ~0.0039, zero_point -128).

## 9. ThermalInterpreter
- Loads TFLite model, runs inference on INT8 inputs, returns `ThermalPrediction`.

## 10. Model Path & Manifest
- File: `ondevice_ai/models/thermal/thermal_fall_int8_v0.1.0.tflite` (318KB)
- Manifest: `model_manifest.json` ensures SHA-256 match.

## 11. V5 InferenceResult
- Dataclass with `sensor_id="thermal44"`, strict validation on `valid`, `score`, `confidence`, `state`.

## 12. V5 Provider
- `SensorProvider` protocol ensures `connect()`, `read()`, `close()` exist.

## 13. Tests / Benchmarks
- Synthetic tests exist (`test_thermal_interpreter.py`).
- No real-hardware latency benchmarks (p50/p95/max) exist yet.

## 14. Stale V4 Imports
- Replaced by `ondevice_ai` domain architecture.
