# 열화상 필드 상황 인수인계 (NOT_HUMAN / 육안 불일치)

- **작성일:** 2026-08-22 (KST)
- **대상 레포:** `jinsu1011/safenest-embedded-competition`
- **세션 성격:** 실행 중 런타임 **수정 없이** 관측·누적 데이터 검토
- **관련 측정 기록:** [`measurements/20260822_thermal_field_measurement_record.json`](./measurements/20260822_thermal_field_measurement_record.json)

---

## 1. 한 줄 요약

열화상 **수신·저장·추론 파이프라인은 동작**한다.  
실시간 화면에서 사람 형체가 보여도, production 모델 `thermal_fall_int8@0.1.0` 은 필드에서 **`NOT_HUMAN`으로 과다 분류**한다.  
우선 확인할 것은 **재학습이 아니라 보정/전처리 계약(°C·학습 도메인 vs 런타임 `per_frame_minmax`)** 이다.

---

## 2. 네트워크 / 호스트 정리

| 역할 | 관측 주소 | 비고 |
|---|---|---|
| Raspberry Pi (SafeNest `:8000`) | **`192.168.137.249`** | health/status 응답. 사용자가 “와바튼 IP”로 부른 주소는 **Pi** |
| ESP peer (thermal/telemetry) | **`192.168.137.107`** | `thermal.state.peer` |
| 이전 필드 Wi‑Fi IP (참고) | `192.168.0.3` (`EELabO3 2G`) | 이후 `192.168.137.x` 망으로 이동 |

---

## 3. 관측된 증상

1. LCD/상태 API에서 열화상 AI가 **`NOT_HUMAN`**
2. 운영자가 **인식거리에서 실시간 열화상 화면으로 사람 형체를 육안 인지**
3. 동시에 mmWave는 종종 `presence=true` / `human_detected_raw=true`
4. Risk reasons에 **`MMWAVE_THERMAL_MISMATCH`** 등장
5. 시스템: `ONLINE` / **`DEGRADED`** (수신은 되나 센서 간 불일치·폴백)

---

## 4. 측정 기록 (요약)

상세 JSON:  
- [`20260822_thermal_live_api_snapshot.json`](./measurements/20260822_thermal_live_api_snapshot.json)  
- [`20260822_thermal_npz_tally.json`](./measurements/20260822_thermal_npz_tally.json)  
- 통합: [`20260822_thermal_field_measurement_record.json`](./measurements/20260822_thermal_field_measurement_record.json)

### 4.1 라이브 API 스냅샷 (동일 세션 후반)

| 항목 | 값 |
|---|---|
| Pi | `192.168.137.249:8000` |
| system | `ONLINE` / `DEGRADED` |
| TCP connections | 4 |
| telemetry_packets | 15987 |
| thermal completed_frames | 10074 |
| thermal incomplete_frames | 424 |
| effective_fps | ~5.19 |
| storage written thermal | 10068 |
| storage written mmwave | 15987 |
| thermal status | `LIVE` |
| AI state | **`NOT_HUMAN`** |
| confidence | ~0.992 |
| probabilities | `[0.992, 0.008, 0.0]` → class0 우세 |
| preprocessing | `per_frame_minmax` |
| temperature_calibrated | **`false`** |
| raw min–max (예) | 2722–3172 |
| model | `thermal_fall_int8` / `0.1.0` |
| mmWave presence / raw | `true` / `true` |
| risk formula | `SAFENEST_RISK_V1` |
| risk reasons (예) | `PRESENCE_FROM_MMWAVE`, `MMWAVE_THERMAL_MISMATCH`, `HIGH_CO2_WARNING`, `NO_MOTION_DETECTED` |
| component_status | thermal=`AI`, mmwave=`RULE_FALLBACK`, co2=`RULE`, pir=`RULE` |

### 4.2 누적 NPZ 집계 (디스크)

경로(파이): `/home/sandi/safenest-team-main/RaspberryPi/Runtime/data/thermal/`  
포맷: `frames (N,62,80) uint16` + `analysis_json`(프레임별 AI 스냅샷)

| 항목 | 값 |
|---|---|
| on-disk npz | 3516 |
| readable npz | 3484 |
| 최근 500파일 analysis frames | 6163 |
| `NOT_HUMAN` | 5879 (~95.4%) |
| `HUMAN_NORMAL` | 189 |
| `HUMAN_FALL` | 95 |
| HUMAN_* 합 | 284 (~4.6%) |
| raw span mean (최근) | ~465.5 (min 280 / max 1017) |
| hot≥0.75 픽셀 수 mean | ~434 (공간 핫스팟 존재) |

### 4.3 동일 밤 더 이른 프로브 (참고)

약 01:15 KST 부근 최근 500파일 창에서는 `HUMAN_* = 0`, `NOT_HUMAN` 지배였다.  
후반 창에서는 HUMAN 소수가 나타나지만 **여전히 NOT_HUMAN 과다**.

### 4.4 공간 구조 (육안과 정합)

최근 npz 샘플에서 per-frame min-max 후 상위 핫픽셀·centroid가 관측됨 → **빈 노이즈 프레임이 아님**.  
UI `heatmap_preview`도 동일 min-max로 대비를 키워 **형체가 잘 보이게** 만듦.

---

## 5. 원인 분석 (우선순위)

### P0 — 보정/전처리 계약 불일치 가능성 (**먼저 체크**)

| 런타임(production) | 오프라인 O2/문서 경로 |
|---|---|
| `temperature_calibrated: false` | `uint16 → Celsius (raw/10 − 273.15)` 등 물리 도메인 |
| `preprocessing: per_frame_minmax` | P1 global z-score 등 학습 파이프라인 |
| 모델 입력: min-max 후 INT8 | T-B5/O2 리플레이는 별 계약 |

문서(`PHASE5_AI` 등)도 production은 “°C 미추정, 공간 패턴만”이라고 명시.  
**학습/검증이 물리 도메인이면**, 지금 런타임 경로만으로 `NOT_HUMAN` 과다 → **재학습 전에 계약 정렬·재추론 비교**가 맞다.

### P1 — 도메인 시프트 / 모델 편향 (계약이 맞을 때의 후보)

전처리가 학습과 동일한데도 HUMAN이 희귀하면 → 재학습·필드 데이터 적응 검토.

### 아님 (이번 세션에서 기각)

- ESP↔Pi 미연결, thermal `NO_DATA` → **아님** (`LIVE`, fps·written 증가)
- “형체가 데이터에 없다” → **아님** (핫픽셀·centroid·육안 preview)

---

## 6. UI vs AI가 어긋나 보이는 이유

1. 화면 preview와 모델 모두 **프레임별 min-max** → 눈에는 사람처럼 보임.  
2. 분류기는 학습 분포의 ‘사람’ 특징을 요구 → 필드 raw/스케일이 다르면 **고대비 블롭 ≠ HUMAN_***.  
3. mmWave는 재실을 말하고 thermal은 `NOT_HUMAN` → Risk가 mismatch를 기록 (정상 동작).

---

## 7. 인수인계 — 다음에 할 일 (권장 순서)

1. **(수정 없이)** 저장된 npz raw에 O2식 `°C = raw/10 − 273.15` 적용 후 **동일 `thermal_fall_int8` 재추론** → 클래스 분포 비교.  
2. 학습/매니페스트 계약이 `normalized_thermal_frame` + min-max인지, °C/P1인지 **문서·학습 스크립트와 대조**.  
3. 전처리만 맞춰도 HUMAN이 유의미하게 늘면 → **런타임 전처리 PR** (재학습 아님).  
4. 맞춰도 `NOT_HUMAN` 고착이면 → 필드 npz 라벨/재학습 이슈로 에스컬레이션.  
5. 운영 PASS 관점: thermal AI만으로 재실을 단정하지 말 것. mmWave mismatch·`DEGRADED`를 명시.

**금지(현 세션 합의):** 라이브 런타임 핫패치로 결론 확정하지 말 것. worktree → PR → merge → Pi pull.

---

## 8. 관련 코드/문서 포인터

| 항목 | 위치 |
|---|---|
| production AI 경로 | `RaspberryPi/Runtime/ai/pipeline.py` (`temperature_calibrated: False`, `per_frame_minmax`) |
| TFLite wrapper | `RaspberryPi/Ondevice_AI/inference/thermal_interpreter.py` (`_prepare_float_frame` min-max) |
| 클래스맵 | `NOT_HUMAN` / `HUMAN_NORMAL` / `HUMAN_FALL` |
| 필드 모니터 | `RaspberryPi/Runtime/hil/pi_field_monitor.py` (표3 thermal `ai_state`) |
| Pi 런북 | `PI_RUNBOOK.md` |
| O2 °C 리플레이 | `RaspberryPi/Runtime/hil/thermal_o2_real_snapshot_replay.py` |

---

## 9. 측정 재현 명령 (읽기 전용)

```bash
# 라이브
curl -s http://192.168.137.249:8000/api/status | python3 -m json.tool | less

# 필드 모니터
cd /home/sandi/safenest-team-main/RaspberryPi/Runtime
python3 hil/pi_field_monitor.py --once

# 누적 npz (파이 로컬)
ls RaspberryPi/Runtime/data/thermal | wc -l
```

---

## 10. 인수 체크리스트

- [ ] Pi IP / ESP peer 구분 이해 (`249` = Pi, `107` = ESP)
- [ ] thermal LIVE·저장 증가·`NOT_HUMAN` 과다 재현 가능
- [ ] 육안 형체 vs AI 불일치가 “수신 실패”가 아님을 공유
- [ ] **다음 액션 = 보정/전처리 계약 검증** (재학습은 그 다음)
- [ ] 본 문서 + `measurements/*.json` 이 팀 main에 merge됨
