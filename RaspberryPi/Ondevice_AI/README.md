# SafeNest active on-device AI workspace

> ⚠️ **RELEASE WARNING: DEPLOYMENT PROHIBITED / NOT_READY**
> 
> - **TFLite 파일 존재·SHA·텐서 규격**: CONFIRMED
> - **Mock 파이프라인**: CONFIRMED
> - **mmWave historical v0.1.0**: BLOCKED (`CLASS_COLLAPSE_ON_REPOSITORY_NPZ`)
> - **mmWave M-N9 FULL_INT8**: locked successor imported; Runtime still blocked v0.1.0; `DEVICE_VALIDATED=NO`. Handoff: `docs/reports/20260818_SafeNest_mmWave_M-N9_Team_Import_Handoff_KO_01.md`
> - **mmWave M-N10 protocol**: shared for later formal capture only; `CAPTURE_NOT_PERFORMED`. See `docs/reports/20260818_SafeNest_mmWave_M-N10_Protocol_Share_KO_01.md`
> - **mmWave v0.2.0 candidate**: `SYNTHETIC_SMOKE_ONLY`
> - **Zenodo real-data reconstruction**: A0–A6 `PASS_WITH_WARNINGS`; Phase B `READY_WITH_CONDITIONS`
> - **Thermal B6-R Public SDT FP32**: `FINAL_RUNTIME_MODEL`로 활성화. `HUMAN_FALL_PROXY`는 위험 점수 `0.4`로 판단에 반영하며 실제 낙상 emergency 권한은 없음; Pi/real sensor `BLOCKED_HARDWARE`
> - **Thermal 실제 낙상 성능**: NOT_VERIFIABLE (합성 NPZ 테스트 fixture만 존재)
> - **CO₂ 실제 재실 성능**: NOT_VERIFIABLE (합성 NPZ 테스트 fixture만 존재)
> - **Pi 5 실배포**: NOT_READY / BLOCKED_HARDWARE
> - **전체 릴리스 상태**: **NOT_READY**

`embed2/` 최상위가 유일한 활성 개발본이다. 과거 V4/V5/구 V6 전체 폴더는 `archive/version_snapshots/`에 읽기 전용으로 보존한다. 현재 모델 계보와 상태는 폴더명이 아니라 `models/model_manifest.json`과 phase 보고서로 관리한다.

현재 상세 검증 상태:

- **P0 소프트웨어 파이프라인 / Mock 테스트**: CONFIRMED (통과)
- **mmWave historical v0.1.0**: BLOCKED (저장소 합성 NPZ 평가 시 Class Collapse, APNEA/비정상 Recall 0%)
- **mmWave M-N9 FULL_INT8**: 팀 저장소에 잠긴 후속 INT8을 넣었으나 Runtime 라이브 키는 아직 v0.1.0. 인수인계 `docs/reports/20260818_SafeNest_mmWave_M-N9_Team_Import_Handoff_KO_01.md`
- **mmWave M-N10 프로토콜**: 나중에 쓸 측정 규칙만 공유. 캡처 안 함. `docs/reports/20260818_SafeNest_mmWave_M-N10_Protocol_Share_KO_01.md`
- **mmWave v0.2.0 candidate**: 학습·재현·양자화 파이프라인을 확인하는 합성 smoke 자산; 실세계 성능 근거로 사용 금지
- **Zenodo 110명 실데이터**: A0–A6 완료. TRAIN/VALIDATION/LOCKED_TEST = 77/17/16 subject split 고정, 440 recording·530 window 변환 및 무결성 감사 통과
- **Thermal B6-R Public SDT FP32**: `models/thermal/public_sdt/public_sdt_pooled_mlp_fp32_tflite_v1.tflite`가 최종 활성 runtime selector다. `HUMAN_FALL_PROXY`는 위험 점수 `0.4`로 융합 판단에 들어가지만 실제 낙상이나 단독 emergency로 승격하지 않는다. 활성화 인수인계 `docs/reports/20260828_SafeNest_Thermal_B6R_Public_SDT_FP32_Active_Runtime_Handoff_KO_01.md`
- **Thermal & CO₂ 오프라인 평가**: synthetic regression fixture 기반 99% 수준 (실센서/실공간 성능 주장 불가)
- **실센서 드라이버 & Pi 5 실배포**: NOT_READY (하드웨어 통합 전)

실센서 provider가 없는 real mode는 정상값을 합성하지 않는다. 네 센서를 `valid=false`, 오류 `EXTERNAL_SENSOR_PROVIDER_REQUIRED`로 출력하고 시스템을 `FAILED`로 판정한다.

## 공식 production 경로

```text
integrated_node/run_node.py
→ sensors/* adapter 또는 주입된 팀원 provider
→ inference/* interpreter
→ risk/risk_engine.py
→ risk/fallback.py
→ inference/inference_result.py
→ JSON Lines stdout
```

`integrated_node/safenest_risk_engine.py`는 기존 테스트·데모용 legacy compatibility 모듈이다. 신규 센서 연동과 production 융합에 사용하지 않는다.

과거 가상 센서 스트리머와 GUI 시연기는
`archive/project_history/legacy_simulator_20260816/`에 보관한다. 이 archive는
현재 runtime에서 import하거나 fallback으로 사용하지 않는다. legacy compatibility
engine의 별도 archive 여부는 역사 테스트·학습 문서의 소유권을 정리한 뒤 결정한다.

## 실행

Mock end-to-end:

```bash
python3 integrated_node/run_node.py --mode mock
```

외부 provider 없는 fail-closed 확인:

```bash
python3 integrated_node/run_node.py --mode real
```

팀원 provider 주입:

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

각 provider는 `connect() -> bool`, `read() -> InferenceResult`, `close() -> None`을 구현한다. 현재 상세 계약은 [sensor provider contract](docs/reports/V5_SENSOR_PROVIDER_CONTRACT.md)를 기준으로 사용하되, 팀 실센서 통합 전 활성 버전 메타데이터를 갱신한다.

## 위험도와 건강 상태

```text
R = 100 * (
    0.35 * S_mmwave
  + 0.35 * S_co2
  + 0.15 * S_pir
  + 0.15 * S_thermal
)
```

`risk_level`은 사람 위험, `system_health`는 센서·모델 파이프라인 상태다. 일부 센서 장애는 `DEGRADED`, 전 센서 장애는 `FAILED`이며 이때 `risk_score`와 `risk_level`은 `null`이다. Thermal 낙상 또는 mmWave 무호흡은 `DANGER`, `R=100` emergency override를 유지한다. 출력 `metadata.schema_version`은 `5.0`이다.

센서별 stale TTL은 [config/sensors.yaml](config/sensors.yaml)에서 읽어 runtime 위험도 엔진에 전달한다. 현재 합의 전 기본값은 Thermal 3초, mmWave 3초, CO₂ 10초, PIR 10초다. CO₂ 0.2 Hz 갱신은 3초 공통 TTL을 사용하지 않는다.

## 검증과 패키징

```bash
python3 scripts/validate_models.py
python3 -m unittest discover -s tests -p "test_*.py" -v
python3 -m compileall -q inference risk sensors integrated_node scripts tests
```

활성 runtime·validator·test는 현재 최상위의 `models/model_manifest.json`만 선택한다. sibling 버전 폴더나 `archive/`, `releases/`의 code·manifest·model을 자동 선택하지 않는다.

## 문서

- [멀티센서 병렬 A–E master roadmap](docs/20260810_ChatGPT_SafeNest_Multisensor_Parallel_Execution_Roadmap_01.md)
- [기존 mmWave A–E 상세 실행 순서](docs/20260806_ChatGPT_SafeNest_mmWave_Execution_Sequence_01.md)
- [mmWave Phase B 개요](docs/MMWAVE_PHASE_B_OVERVIEW.md)
- [팀 인수인계 기준판](docs/TEAM_HANDOFF_GUIDE_V5.md)
- [Sensor provider 계약](docs/reports/V5_SENSOR_PROVIDER_CONTRACT.md)
- [Release readiness](docs/reports/V5_RELEASE_READINESS.md)
- [Sensor data contract](docs/reports/SENSOR_DATA_CONTRACT.md)
