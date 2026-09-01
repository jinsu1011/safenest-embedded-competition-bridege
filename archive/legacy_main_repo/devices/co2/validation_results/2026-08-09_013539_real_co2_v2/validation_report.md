# CO2 실제 센서 + AI Pipeline Validation (세션 리포트)

본 디렉터리는 **REAL SENSOR EVIDENCE** 입니다. synthetic fault injection 데이터는 포함되어 있지 않습니다.

## 1. 최종 판정

**`CO2_REAL_AI_VALIDATION_PASS`**

REAL SCD40 → ESP32 telemetry → V5 CO2 provider → production history/slope →
`[real slope, real humidity, real CO2]` → 실제 INT8 TFLite → `InferenceResult(sensor_id="co2")`
→ V5 provider 경계까지 실제 하드웨어 데이터로 통과했습니다.

이 판정은 **pipeline validation** 에 한정됩니다. 모델 release/accuracy validation이 아닙니다.
모델 `status`는 여전히 **`candidate`** 입니다.

## 2. 검증 환경

| 항목 | 값 |
|---|---|
| git branch | `codex/mmwave-20rpm-root-cause` |
| git HEAD | `0e8538c75354691fccf5f223029b0e633c1260af` |
| dirty | yes (CO2 firmware 수정 + CO2 provider/tests/tools 미추적) |
| host | macOS-26.5-arm64 (개발 Mac) |
| port / baud | `/dev/cu.usbserial-110` / 115200 |
| ESP firmware | `safenest-integrated-esp/1.0.0`, device_id `esp32-01` |
| telemetry schema | `safenest.co2.serial.v1` |
| session duration | 370.67 s (stabilization 70 s + qualified 300 s) |
| model | `ondevice_ai/models/co2/co2_occupancy_int8_v0.1.0.tflite` |
| model_id / version / status | `co2_occupancy_int8` / `0.1.0` / **candidate** |
| SHA-256 actual = expected | `3a8c86c4c132df0f1edaac668d9a136c3f6234789df48f02bdda8e92f29d0462` (**일치**) |

## 3. 실제 SCD40 telemetry

부팅 시 `[co2] ready: first measurement takes about 5 seconds` (I2C 0x62 검출 성공).

세션 시작 시점 ESP uptime은 713 s 였습니다. 즉 SCD40은 qualified window 이전에
이미 약 12분 연속 동작 중이었고, **물리 안정화 요구(≥60 s)를 크게 초과**합니다.

raw 예시 (`raw_serial.jsonl`):

```
{"schema":"safenest.co2.serial.v1","device_id":"esp32-01","firmware_version":"safenest-integrated-esp/1.0.0","seq":715,"ts_monotonic_ms":715000,"co2_ppm":1255,"humidity_pct":59.71,"temperature_c":26.70,"co2_valid":true,"co2_error":null,"co2_sample_seq":149,"co2_sample_ts_ms":714132,"co2_sample_age_ms":868}
```

| 측정값 (qualified window, valid=63) | mean | p50 | min | max |
|---|---|---|---|---|
| CO2 (ppm) | 1244.5 | 1244.0 | 1240 | 1253 |
| Humidity (%) | 61.18 | 61.22 | 59.63 | 62.25 |
| Temperature (°C) | 26.81 | 26.85 | 26.35 | 27.20 |
| CO2 slope (ppm/min) | −1.74 | −1.30 | −7.27 | +5.19 |

## 4. Physical sample cadence / quality

| 항목 | 값 |
|---|---|
| raw serial lines | 408 |
| physical sample count | 79 |
| duplicate heartbeat lines (history 미반영) | 292 |
| non-telemetry lines (`[health]` 등, skip) | 37 |
| physical sample interval mean / p50 / p95 / max / min (s) | 4.778 / 4.75 / 5.00 / 5.002 / 4.746 |
| physical timestamp 단조증가 | **true** |
| stale sample | 0 |
| communication error | 0 |

1 Hz heartbeat와 ~4.78 s 물리 cadence가 명확히 분리되어 있으며, 동일 `co2_sample_seq`
라인은 history에 중복 append되지 않았습니다.

## 5. 실제 feature vector (REAL provenance)

feature order = `[co2_slope, humidity, co2_ppm]` (manifest/scaling metadata와 일치)

| feature | source | 구분 | 근거 |
|---|---|---|---|
| `co2_ppm` | SCD40 telemetry | **REAL** | `raw_serial.jsonl` `co2_ppm` |
| `humidity` | SCD40 telemetry | **REAL** | `raw_serial.jsonl` `humidity_pct` |
| `co2_slope` | 실제 CO2 history + 실제 physical timestamp | **DERIVED_FROM_REAL** | production `calculate_co2_slope()` |
| `temperature` | SCD40 telemetry | **REAL (모델 입력 아님)** | evidence로만 저장 |

실제 샘플 (`co2_sample_seq=164`, `co2_sample_ts_ms=785881`):

```
raw feature vector : [-5.490196078431373, 59.63, 1248.0]
scaler mean        : [0.011184156, 25.730582, 606.481268]
scaler scale       : [4.373409, 5.532444, 314.387149]
scaled vector      : [-1.257916, 6.127386, 2.040537]
input quant        : scale=0.005828449968248606, zero_point=57
quantized int8     : [-128, 127, 127]
model class        : VACANT (index 0)
probabilities      : [0.95703125, 0.04296875]
provider score     : 0.0
provider state     : VACANT
```

## 6. Actual INT8 TFLite

| 항목 | 값 |
|---|---|
| actual TFLite invocation (REAL) | **77** |
| valid inference | 77 |
| fallback / mock substitution | **0** |
| model SHA manifest 일치 | **true** |
| input | `[1,3] int8`, scale `0.005828449968248606`, zp `57` |
| output | `[1,2] int8`, scale `0.00390625`, zp `-128` |
| class 분포 | VACANT 62 / OCCUPIED 15 |
| confidence 범위 | 0.535 ~ 0.957 |

**invoke 77 vs qualified valid 63 차이(14건) 설명:** 14건은 추론 실패가 아니라
**stabilization window(첫 70초) 안에서 수행된 정상 추론**입니다.
세션 전체 valid read는 77건(warm-up 14 + qualified 63)이고 TFLite invoke도 정확히 77회로
1:1 대응합니다. §10의 통계와 §8의 `node_adopted_valid_count = 63`은
qualified window만 집계한 값이며, warm-up 구간 14건은 REAL 성능 통계에서 의도적으로 제외했습니다.
inference failure는 0건입니다.

`CO2Interpreter`에는 rule fallback 경로가 존재하지 않으며, SHA 불일치 시 생성 자체가
실패합니다. 실행 경로 추적 결과 fallback/mock 대체는 0건입니다.

### 6.1 Fallback 0 증명 (코드 경로 + 실측 evidence)

`CO2Interpreter`에서 fallback처럼 동작할 수 있는 유일한 분기는
`decode_output()`의 `total <= 0` 방어 분기이며, 이 경우 모델 출력을 버리고
상수 `[0.5, 0.5]`를 반환합니다.

출력 양자화가 `scale=0.00390625 (=1/256)`, `zero_point=-128` 이므로
역양자화 결과는 항상 `(q + 128)/256 ∈ [0, 0.99609375]` 로 음수가 될 수 없고,
`total == 0` 은 두 출력 int8이 모두 정확히 `-128` 일 때만 성립합니다.
따라서 `np.clip(probs, 0.0, None)` 은 본 모델에서 no-op이며
`total <= 0` 분기는 구조적으로 도달하기 어렵습니다.

실측 evidence로도 확인했습니다.

| 항목 | 값 |
|---|---|
| REAL TFLite invoke count | **77** |
| normal decode count (`total > 0` 정상 정규화) | **77** |
| **fallback-like decode count (`probabilities == [0.5, 0.5]`)** | **0** |
| 음수 확률 clip 발생 | **0** |
| `CO2_TFLITE_INFERENCE_FAILED` | **0** |
| probabilities 합 (min/max) | 1.000000000 / 1.000000000 |
| confidence 최솟값 | 0.535156 (≠ 0.5) |

1차 세션(`2026-08-09_012725_real_co2`)에서도 동일하게
REAL invoke 77 / normal decode 77 / fallback-like 0 / inference failure 0 입니다.

`prepare_input()`의 int8 clip은 fallback이 아니라 입력 범위 포화이며
§11-1 known limitation으로 별도 기록합니다.

## 7. TFLite 분류 vs provider rule (구분)

| 계층 | 의미 |
|---|---|
| `model_class` / `model_confidence` | CO2 INT8 TFLite가 직접 낸 occupancy 분류 (VACANT/OCCUPIED) |
| `provider_score` / `provider_state` | `score = 1.0 if (class_index == 1 or co2_ppm > 1500.0) else 0.0` 규칙 적용 결과 |

`provider_state`는 TFLite 단독 예측이 아니라 **모델 분류 + 절대 ppm 규칙의 합성**입니다.
본 세션에서는 CO2가 1500 ppm 미만이었으므로 `provider_score`는 모델 클래스와 일치했습니다.
CO2 TFLite는 occupancy 보조 모델이며, SafeNest 전체 CO2 환경위험 판단(절대 농도 + 상승률
+ Risk Engine 규칙)을 단독으로 수행하지 않습니다.

## 8. V5 InferenceResult / Provider

- `sensor_id == "co2"` ✔
- V5 `validate_provider_result()` 실패 **0건**
- **`node_adopted_valid_count = 63`**, `node_replaced_provider_result_count = 0`
  → V5 node가 provider 결과를 그대로 채택 (PROVIDER_* 오류로 대체하지 않음)
- 나머지 3개 provider는 `EXTERNAL_SENSOR_PROVIDER_REQUIRED`로 유지되어
  node 전체는 `system_health=FAILED`, `risk_score=null` — 설계된 fail-closed 동작이며
  CO2 provider 검증 실패가 아닙니다. Risk Engine은 수정하지 않았습니다.

## 9. Fail-closed (REAL 관측 + SYNTHETIC 분리)

**REAL 관측:**
- 세션 초반 `INSUFFICIENT_HISTORY` / `WARMING_UP` → history 미충족 시 추론 안 함
- `CO2_NO_NEW_PHYSICAL_SAMPLE` 61회 → 새 물리 샘플이 없으면 이전 값을 재사용하지 않고 invalid
- 모든 invalid에서 `score=0.0`, `confidence=0.0`, `state != NORMAL`

**SYNTHETIC FAULT INJECTION — NOT REAL SENSOR EVIDENCE:**
malformed JSON / wrong schema / `co2_valid=false` / null CO2 / null RH / NaN / Inf /
범위 이탈 / stale / timestamp 역전 / sequence reset / serial timeout / serial 예외 /
connect 전 read / close 후 read / 복구 — `devices/co2/tests/test_co2_v5_provider.py`

두 데이터는 통계상 혼합되지 않았습니다.

## 10. 개발 Mac 성능 (DEVELOPMENT MAC RESULT)

| 지표 | mean | p50 | p95 | max |
|---|---|---|---|---|
| **TFLite pure invoke latency (ms)** | 0.0762 | 0.0729 | 0.1133 | 0.2389 |
| provider end-to-end read latency (ms) | 1888.7 | 1999.7 | 2999.8 | 3006.2 |
| node step end-to-end (ms) | 1889.2 | 2000.0 | 3000.3 | 3006.6 |

provider read latency의 대부분은 **SCD40의 ~4.78 s 물리 cadence를 기다리는 시간**이며
연산 비용이 아닙니다. TFLite 순수 추론과 반드시 구분해야 합니다.

**본 수치는 개발 Mac 측정치이며 Raspberry Pi 5 On-Device AI KPI(≤100 ms) 검증 결과가 아닙니다.**

## 11. Known limitations

1. **INT8 입력 포화 (가장 중요).** 모델 입력 양자화가 표현 가능한 원시 범위는
   `CO2_slope [-4.705, +1.795] ppm/min`, `Humidity [19.77, 27.99] %`, `CO2 [267, 735] ppm`
   입니다. 실제 측정 환경(CO2 ~1244 ppm, RH ~61 %)은 이 범위 밖이라
   **77/77 샘플에서 humidity와 co2_ppm이 INT8 상한(+127)에 고정**되었고,
   slope도 34/77에서 포화했습니다. 즉 이 환경에서 모델을 실질적으로 구동한 입력은
   slope 하나뿐입니다. pipeline은 정상 동작하지만, 현재 모델의 학습/양자화 분포가
   본 검증 환경을 커버하지 않습니다. `status: candidate`와 일관된 결과입니다.
2. 독립 reference CO2 meter가 없으므로 **절대 ppm 정확도, 오차율, 센서 정확도를 주장할 수 없습니다.**
3. ground truth occupancy 라벨이 없으므로 **모델 분류 정확도를 주장할 수 없습니다.**
   confidence는 accuracy가 아닙니다.
4. 의도적 환기/고농도 조성 없이 자연 실내 상태만 관측했습니다.
5. ESP `millis()` 기반 physical timestamp는 약 49.7일에서 wrap합니다.
6. 개발 Mac에는 TFLite 런타임이 없어 저장소 밖 venv(`ai-edge-litert`)를 사용했습니다.
7. 통합 펌웨어 빌드는 저장소 밖 PlatformIO 프로젝트에서 수행했습니다
   (mmWave 라이브러리는 비공식 `Love4yzp/Seeed-mmWave-library` 사용).

## 12. Raspberry Pi 5 next step

본 결과는 **개발 Mac 사전 검증**입니다. 다음 단계:

1. Raspberry Pi 5에 `requirements-pi.txt` 기준 TFLite 런타임 설치 및 동일 provider 실행
2. Pi에서 TFLite invoke latency 재측정 → ≤100 ms KPI 판정
3. 4개 provider 동시 주입 후 Risk Engine 통합 검증
4. 모델 재학습 검토: 현재 환경 CO2/RH 분포를 커버하도록 scaler/양자화 범위 재설정
   (본 검증 범위 밖, 별도 승인 필요)
