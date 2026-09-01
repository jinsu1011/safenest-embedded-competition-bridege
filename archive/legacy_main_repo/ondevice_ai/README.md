# SafeNest On-Device AI (`ondevice_ai/`)

> ⚠️ **배포 금지 / NOT_READY**
>
> 이 디렉터리는 팀 저장소의 **온디바이스 AI 컴포넌트**입니다.  
> 소프트웨어 mock·오프라인 데이터 계약·phase validator 증거는 동기화되어 있지만, **실센서/라즈베리파이/임상 성능 검증은 완료되지 않았습니다.**

## 비담당자가 먼저 알면 되는 것

| 질문 | 답 |
|---|---|
| 여기가 뭐하는 폴더인가요? | 전처리·추론·모델 자산·데이터 계약·위험도 로직·validator/보고서가 모인 AI 컴포넌트입니다. |
| 실기기 드라이버도 여기 있나요? | **아니요.** 실하드웨어 드라이버는 팀 저장소의 `devices/<device>/src/` 쪽입니다. |
| 지금 배포해도 되나요? | **안 됩니다.** Mock 통과 ≠ 실배포 승인입니다. |
| 최신 동기화 기준은? | 스탠드얼론 소스 `https://github.com/sheepmeat/test` 커밋 `efc7e2eb61a49e221ce0ebf6057b0c1617525ad1` (B-complete offline baseline) |
| 최신 Thermal 기준은? | 전체 `https://github.com/yuname121/safenest-thermal-ai` merged PR #1 / `main` `db51112` (source head `71c6d08`, SNTR UDP V2 pre-T-C tooling 포함) |

## 이번 동기화에서 바뀐 점 (요약)

이 동기화는 **재현 가능한 offline AI candidate baseline**을 팀 저장소에 맞추는 중간 배포입니다. Raspberry Pi 통합과 이후 실기기 Phase C의 공통 기준이지, 실하드웨어 성능 승인이 아닙니다.

1. **mmWave**
   - `M-A0`~`M-A6`, `M-B0`~`M-B12` frozen offline candidate 유지
   - 활성 offline INT8 후보는 `models/mmwave/experiments/M-B6_stage_equivalence/M-B3_CONV1D_GAP_BASELINE_seed42_M-B5_CAL_CLASS_BALANCED_120_int8.tflite`
   - MR60 입력 대응·실기기 분류 성능·Pi latency는 **미검증**
   - 실측 안내서는 PRE-M-C1 준비 문서이며 M-C1 시작 승인이 아님
2. **CO₂**
   - `C-A0`~`C-A6`, `C-B0`~`C-B5` 유지
   - `C-B6` reduced-feature (`CO2` + `CO2_slope`) INT8 occupancy candidate 추가
   - occupancy 모델 ≠ CO₂ safety threshold ≠ sensor health ≠ fusion
   - SCD40 device-domain validation은 **미완**. C-C1 측정 안내/도구는 문서·tooling일 뿐 정식 C 완료가 아님
3. **Thermal**
   - `T-A0`~`T-A6` 및 `T-B0`~`T-B5` offline lock 증거 추가
   - T-B5 FULL_INT8 바이너리는 git에 없고 외부 SSD identity만 기록됨
   - Thermal-90 raw frame 수집은 `devices/thermal/xiao_esp32c6_thermal90_udp_capture/`와 `scripts/thermal_udp_capture.py`의 SNTR UDP V2 계약을 사용
   - `HUMAN_FALL`/`LYING` ≠ verified `FALL_EVENT`
   - Thermal-90/44 실기기 검증은 **미완**
4. **통합 규칙**
   - 팀 전용 파일(`integrated_node/competition_runtime/`, `esp32_sensor_node.ino`, 구버전 모델/스크립트)은 **삭제하지 않고 보존**
   - 기본 runtime `config/models.yaml` / `models/model_manifest.json`은 여전히 역사적 v0.1.0을 가리킴. B-complete 후보는 `docs/integration/20260816_b_complete_active_offline_candidates.json`
   - 실드라이버 중복 복사 금지, fail-closed 유지
5. **문서**
   - mmWave/CO₂/Thermal 인수인계·실측 안내서 추가
   - 충돌 결정: `docs/integration/20260816_b_complete_collision_matrix.json`

## 현재 개발 상태 (정직하게)

### mmWave
- 완료: M-A0..M-A6, M-B0..M-B12 (offline candidate, 경고/조건 포함)
- 미완: standalone M-C0 correspondence, M-C1 protocolized acquisition, M-C2 device-domain evaluation, Pi latency
- LOCKED_TEST 모델 선택 접근: **0**
- MR60 실기기·Pi 배포 검증: **미완**

### CO₂
- 완료: C-A0..C-A6, C-B0..C-B6 (offline occupancy candidate, limitations 포함)
- 미완: SCD40 device-domain validation, formal C-C2
- UCI 소스만으로 cross-room/cross-building 일반화 주장 불가

### Thermal
- 완료: T-A0..T-A6, T-B0..T-B5 (offline lock, limitations 포함)
- 현재 분류: `TEAM-THERMAL-INTEGRATION / PRE-T-C DEVICE-CAPTURE PREPARATION`
- 준비 완료: Thermal-90 SNTR UDP V2 수집기·validator·XIAO compile-only 확인. transport identity와 unverified header word 0을 분리하고 raw chunk exact inventory 및 sender telemetry를 지원
- 미완: T-C device-domain, git-tracked T-B5 INT8 binary intake, 실제 XIAO/Pi 수신, Thermal-90/44 validation
- `T_C_EXECUTED = NO`, `T_C_DEVICE_CONTRACT_VERIFIED = NO`, `FINAL_THERMAL_HARDWARE_SELECTION = NOT_YET_FROZEN`
- `LYING`/`HUMAN_FALL` ≠ verified fall-event onset label

### 통합/배포
다음을 **주장하지 마세요.**
- 실센서 통합 완료
- Raspberry Pi 장기 검증 완료
- 임상 검증 완료
- final fusion 최적화 완료
- hardware-validated / production-ready / deployment complete

## 책임 경계

```text
devices/<device>/src/     실하드웨어 드라이버
shared/contracts/         공개 센서 인터페이스
ondevice_ai/              AI 전처리·추론·모델·데이터계약·risk·mock·validator
```

실센서 provider가 없는 `real` mode는 정상값을 합성하지 않습니다.  
센서는 `valid=false` / `EXTERNAL_SENSOR_PROVIDER_REQUIRED`로 실패하고 시스템은 `FAILED`로 판정합니다.

## 실행 (팀 저장소 루트 기준)

```bash
cd ondevice_ai

# Mock end-to-end
python3 integrated_node/run_node.py --mode mock

# provider 없는 fail-closed 확인
python3 integrated_node/run_node.py --mode real
```

Provider 주입 예:

```python
from integrated_node.run_node import SafeNestIntegratedNode

node = SafeNestIntegratedNode(
    mode="real",
    sensors={
        "thermal44": thermal_provider,
        "mmwave": mmwave_provider,
        "co2": co2_provider,
        "pir": pir_provider,
    },
)
node.start()
print(node.step().to_json())
node.shutdown()
```

각 provider는 `connect() -> bool`, `read() -> InferenceResult`, `close() -> None`을 구현해야 합니다.

## 위험도 수식

```text
R = 100 * (
    0.35 * S_mmwave
  + 0.35 * S_co2
  + 0.15 * S_pir
  + 0.15 * S_thermal
)
```

Thermal 낙상 또는 mmWave 무호흡(APNEA proxy)은 emergency override로 `R=100` / `DANGER`입니다.  
APNEA는 **자발적 호흡정지 프록시**이며 임상 apnea가 아닙니다.

## 검증

```bash
cd ondevice_ai
python3 scripts/validate_models.py
python3 -m unittest discover -s tests -p "test_*.py" -v
python3 -m compileall -q inference risk sensors integrated_node scripts tests
```

원본 raw archive가 팀 저장소에 전송되지 않은 phase validator는  
`NOT_RUN_RAW_PAYLOAD_NOT_TRANSFERRED`로 보고해야 하며, fixture를 만들어 통과시켜서는 안 됩니다.

## 문서

- [팀 인수인계 가이드](docs/TEAM_HANDOFF_GUIDE.md)
- [통합 충돌 요약](docs/integration/collision_summary.md)
- [멀티센서 병렬 roadmap](docs/20260810_ChatGPT_SafeNest_Multisensor_Parallel_Execution_Roadmap_01.md)
- [mmWave 실행 순서](docs/20260806_ChatGPT_SafeNest_mmWave_Execution_Sequence_01.md)
- [mmWave Phase B 개요](docs/MMWAVE_PHASE_B_OVERVIEW.md)
- [Sensor provider 계약](docs/reports/V5_SENSOR_PROVIDER_CONTRACT.md)
