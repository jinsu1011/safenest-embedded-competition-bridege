# MR60BHA2 M-C0 Device Measurements

기존 SafeNest 저장소 안에서 MR60BHA2 물리 장치 증거를 코드·모델 영역과 분리해 관리하는 standalone evidence 영역입니다. 센서 연결 전 **준비·감사·검증할 수 있는 작업**과 센서 연결 후 추가할 pilot/formal evidence를 같은 계약으로 관리합니다.

## 원칙

- `ondevice_ai/`, Phase-A/B 데이터, `LOCKED_TEST`, 기존 모델과 펌웨어 코드는 변경하지 않습니다.
- raw 기본 정책은 ignore입니다. 단, PR #18의 `M-C0-PILOT-DESKWORK-001.raw.jsonl`과 `M-C0-PILOT-STATIONARY-001.raw.jsonl`은 provenance, session identity, SHA-256, record/byte count와 QA 검토를 동반한 의도적인 좁은 `TRACKED_EXCEPTION`입니다. 이 예외는 다른 scratch·private·large·unreviewed payload의 추가를 허가하지 않습니다.
- 기존 raw 로그를 임의로 복사·수정하지 않고, 필요한 경우 원본 경로·커밋·검증 결과만 기록합니다.
- 사람을 식별할 수 있는 이름·얼굴·영상은 수집하지 않습니다.
- 호흡 정지, 과호흡, 극단적 동작, 가스·밀폐 환경 시험은 이 프로토콜의 범위가 아닙니다.
- M-C0는 물리 센서와 실제 환경에서 얻은 증거가 있어야 완료됩니다. 이 영역에서 먼저 하는 일은 그 측정을 위한 계약과 검증 틀을 고정하는 것입니다.

## 현재 범위

| 구분 | 지금 연결 없이 가능 | 실제 MR60 연결 필요 |
|---|---|---|
| 저장소 감사 | 현재 펌웨어 필드, 기존 로그·manifest·체크섬·cadence 경로 확인 | - |
| 계약 | session manifest, raw JSONL 필드, QA 상태 정의 | 실제 값으로 계약 충족 확인 |
| 검증기 | manifest 형식, 시간 순서, JSONL 파싱 검증 | 현재 장치의 실제 cadence·gap 확인 |
| 측정 | 기존 증거의 재사용 가능 여부 분류 | 새 세션 기록, 환경·거리·자세·방향·배경 조건 측정 |
| reference | 독립 reference가 필요한 위치 정의 | reference와 센서 timestamp 동기화 |
| 통합 | 기존 코드의 입력 계약과 offline candidate 계약 비교 | MR60 → ESP32 → USB → Pi end-to-end 확인 |

## 파일 안내

- `../../../docs/mmwave/MR60BHA2_DEVICE_MEASUREMENT_PROTOCOL_M-C0.md`: mmWave 없이 먼저 하는 작업과 이후 측정 순서
- `protocols/mc0_measurement_contract.json`: 센서 연결 전 고정한 machine-readable 측정 계약
- `schemas/session_manifest.schema.json`: 세션 메타데이터 계약
- `schemas/raw_record.schema.json`: 현재 MR60/ESP JSONL 계약. `phase_age_ms`는 역사 자료 호환을 위해 `EXPLICITLY_OPTIONAL_WITH_LIMITATION`이며, 없으면 fresh phase cadence를 입증할 수 없음
- `validators/validate_contract.py`: 외부 패키지 없이 실행하는 manifest/raw 검증기
- `manifests/main_repo_audit.json`: 메인 저장소 read-only 감사 결과
- `reports/existing_evidence_audit.md`: 기존 78개 raw JSONL의 실제 재분석 결과
- `reports/raw_file_index.json`: 감사 대상 raw 파일의 경로·Git blob SHA·크기
- `reports/offline_remaining_audit.md`: CSV·adapter replay·모델 입력 계약의 오프라인 추가 검증 결과
- `reports/offline_analysis_results.json`: 위 추가 검증의 machine-readable 결과
- `reports/offline_pipeline_audit.md`: M-B11 BPF·z-score·int8·synthetic edge-case 추가 결과
- `reports/offline_pipeline_results.json`: pipeline/bundle/negative-test machine-readable 결과
- `reports/tflite_offline_benchmark.md`: 실제 locked TFLite invoke·host latency·출력 분포 결과
- `reports/tflite_offline_benchmark_results.json`: TFLite benchmark machine-readable 결과
- `reports/verification_matrix.md`: `VERIFIED / NOT_VERIFIED / UNKNOWN / BLOCKED_HARDWARE` 판정표
- `fixtures/`: 실제 사람 데이터가 아닌 검증용 예시
- `tools/offline_pipeline_audit.py`: CSV를 locked preprocessing과 int8까지 재현하는 수치 감사
- `tools/verify_bundle.py`: CSV와 JSONL을 한 번에 검사하는 dependency-free 감사
- `tools/run_negative_tests.py`: 오류 입력 검출 테스트
- `tools/tflite_offline_benchmark.py`: 기존 CSV를 locked TFLite model에 넣는 offline benchmark
- `tools/live_mr60_monitor.py`: ESP32 serial raw 저장과 실시간 상태 표시
- `tools/physical_capture_qa.py`: 실제 immutable JSONL의 cadence·jitter·gap·sequence·field coverage QA
- `templates/`: 실제 측정에 사용할 manifest·환경 metadata·capture checklist
- `reports/M-C0_PILOT_DESKWORK_001.md`: 작은 팔 움직임이 있는 첫 physical Pilot 결과와 claim boundary
- `reports/M-C0_TEAMMATE_CONTINUATION_PROMPT.md`: 완료된 측정을 반복하지 않고 QA·Phase-B 대응을 이어가는 팀원 프롬프트

## 실행

```bash
python3 devices/mmwave/device_measurements/validators/validate_contract.py \
  --manifest devices/mmwave/device_measurements/fixtures/session_manifest.example.json \
  --raw-jsonl devices/mmwave/device_measurements/fixtures/example.raw.jsonl \
  --check-files
```

이 명령은 실제 센서 없이도 계약과 검증기의 기본 동작을 확인합니다.

추가 오프라인 검증은 `reports/offline_remaining_audit.md`, `reports/offline_pipeline_audit.md`, `reports/tflite_offline_benchmark.md`에 기록되어 있습니다. CSV 무결성·adapter replay·정확한 BPF·int8 quantization·synthetic edge-case·실제 TFLite invoke 검증을 완료했습니다.

```bash
python3 devices/mmwave/device_measurements/tools/verify_bundle.py \
  --csv-dir /path/to/csv_bundle \
  --raw-dir /path/to/raw_jsonl_bundle
```

정확한 BPF 수치 감사는 `numpy`와 `scipy`가 있는 runtime에서 다음처럼 실행합니다.

```bash
python3 devices/mmwave/device_measurements/tools/offline_pipeline_audit.py --csv-dir /path/to/csv_bundle
```

실제 TFLite benchmark는 TensorFlow runtime과 locked model binary가 모두 필요합니다. 결과의 latency는 Apple Silicon host 값이며 target Raspberry Pi/ESP32 성능으로 해석하지 않습니다. 기존 CSV label은 모델 class ground truth가 아니므로 accuracy/F1은 산출하지 않습니다.

센서 연결 후 live capture 예시:

```bash
python3 devices/mmwave/device_measurements/tools/live_mr60_monitor.py \
  --port /dev/cu.usbserial-XXXX \
  --baud 115200 \
  --output devices/mmwave/device_measurements/pilot/M-C0-PILOT-001.jsonl
```

터미널에는 1초마다 `rate`, `last_gap`, `max_gap`, `json_bad`, `uart_bad`, `checksum_bad`, `presence`, `distance`, `phase`, `window`, `state`가 표시됩니다. `Ctrl-C`로 종료하면 raw SHA-256·byte count도 출력됩니다. `pyserial`은 캡처용 환경에 별도로 설치합니다.

## 감사 기준점

- 메인 저장소: [jinsu1011/safenest-embedded-competition](https://github.com/jinsu1011/safenest-embedded-competition)
- 감사 기준 main commit: `fdf34b804f35e5868356f0ed6f804a248aa69131`
- 해당 감사는 통합 전 read-only 기준점입니다. 이후 실제 pilot/formal 측정 파일은 이 저장소의 `device_measurements/` 영역에 session 단위로 추가합니다.
