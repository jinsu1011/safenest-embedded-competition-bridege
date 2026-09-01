# M-C0 검증 상태

판정은 센서 연결 없이 확인 가능한 사실과, 실제 장치가 있어야 확인되는 사실을 분리한다.

| 항목 | 상태 | 현재 근거 | 다음에 필요한 것 |
|---|---|---|---|
| 메인 저장소 기준 커밋과 장치 경로 | `VERIFIED` | read-only 감사 및 `manifests/main_repo_audit.json` | 없음 |
| 현재 firmware의 raw 필드 계약 | `VERIFIED` | `devices/mmwave/firmware/src/main.cpp` 기준으로 schema 작성 | 새 raw JSONL로 필드 존재·타입 확인 |
| session metadata 계약 | `VERIFIED` | `schemas/session_manifest.schema.json` 작성 | 실제 세션 manifest 작성 |
| raw JSONL QA 검증기 | `VERIFIED` | `validators/validate_contract.py`와 fixture | 실제 파일에 실행 |
| 기존 78개 raw JSONL 재분석 | `VERIFIED_WITH_EXCEPTIONS` | `reports/existing_evidence_audit.md`의 실제 scan 결과 | 새 formal 파일에도 동일 QA 적용 |
| CSV delivery 9개 무결성 및 기본 window 생성 | `VERIFIED_WITH_EXCEPTIONS` | `reports/offline_remaining_audit.md`, 실제 manifest/hash/record 대조와 620개 window replay | 새 formal 측정 CSV에도 동일 QA 적용 |
| 현재 MR60 ESP adapter의 offline replay | `VERIFIED_WITH_EXCEPTIONS` | 78개 JSONL replay, strict provenance·fail-closed·warmup/window 결과 | 새 장치 raw에서 실제 환경 조건 재확인 |
| M-B11 preprocessing/scaler/quantization identity 대조 | `VERIFIED_WITH_EXCEPTIONS` | `reports/offline_remaining_audit.md`, 서로 다른 metadata 세대와 locked candidate 비교 | 실제 raw를 locked BPF 입력까지 연결 |
| 정확한 M-B11 BPF 실행 | `VERIFIED_WITH_EXCEPTIONS` | 임시 `scipy 1.18.0` runtime으로 620개 CSV window replay | 실제 장치 raw에서도 동일 계약 확인 |
| M-B11 int8 quantization/dequantization | `VERIFIED_WITH_EXCEPTIONS` | saturation 0%, dequantization MAE 약 0.00865676 | 실제 장치 raw domain에서 재확인 |
| synthetic preprocessing edge cases | `VERIFIED` | 정상·상수·NaN/Inf·짧은 입력 4개 테스트 | 없음; physical 의미는 별도 |
| bundle audit 및 strict negative tests | `VERIFIED` | CSV/JSONL one-command audit, 오류 케이스 4/4 검출 | 새 formal 파일에 실행 |
| TFLite 실제 `invoke` 및 host latency | `VERIFIED_WITH_EXCEPTIONS` | 620/620 APNEA는 `EXPLORATORY_PRE_CORRESPONDENCE_INFERENCE`; correspondence/domain warning이며 formal metric 아님 | M-C0 신호·시간 대응을 먼저 확립 |
| 실제 측정 manifest·환경 metadata·capture checklist | `VERIFIED` | `templates/`에 작성 | 측정 시 실제 값으로 채움 |
| USB serial live monitor | `VERIFIED` | 실제 ESP32 USB에서 180초/1,799-record raw 저장, 9.993997Hz, max gap 103ms, 오류 0 | stationary/reference 세션에도 동일 도구 적용 |
| standalone MR60 physical JSON field population | `VERIFIED_WITH_EXCEPTIONS` | desk-work Pilot에서 presence·distance·respiration·heart·total/breath/heart phase 100% populated | sensor firmware version과 phase semantics 확인 |
| 기존 final manifest와 현재 raw tree 범위 일치 | `NOT_VERIFIED` | final manifest는 68개/154,413줄, 현재 tree scan은 78개/172,390줄 | scope/lineage를 세션 단위로 정리 |
| 기존 evidence의 M-C0 formal 적합성 | `NOT_VERIFIED` | 기존 로그·문서가 있으나 M-C0의 메타데이터/reference/QA 전체 충족은 확인되지 않음 | 부족한 metadata/reference만 보완 |
| MR60 telemetry-row cadence/gap/jitter | `VERIFIED_WITH_EXCEPTIONS` | desk-work 9.993997Hz, stationary 9.993330Hz; fresh phase cadence와 구분 | direct phase-update identity가 있어야 exact cadence 검증 |
| fresh `breath_phase` cadence | `NOT_VERIFIED` | producer validity threshold는 500ms지만 exact frame-arrival identity가 없음 | `FRESH_PHASE_CADENCE_NOT_YET_FULLY_VERIFIED` 유지 |
| phase 단위·스케일·리셋·결측 의미 | `NOT_VERIFIED` | 실제 세 phase가 1,799/1,799 populated됐으나 의미 검증 근거 없음 | stationary 및 독립 reference 비교 |
| 독립 호흡 reference 동기화 | `NOT_VERIFIED` | desk-work Pilot은 `none/not_collected` | reference와 timestamp 동기화 |
| 새 사람·새 세션 일반화 | `NOT_VERIFIED` | desk-work physical Pilot 1세션만 존재 | stationary baseline 및 추가 승인 세션 |
| MR60 → ESP32 → USB → Pi E2E | `VERIFIED_WITH_EXCEPTIONS` | MR60→ESP32→USB 10Hz physical stream은 검증, Pi 미포함 | Pi runtime 연결과 기록 |
| 임상 apnea 검증 | `NOT_VERIFIED` | offline 데이터의 apnea proxy는 임상 진단이 아님 | 이 프로토콜의 목표로 삼지 않음 |
| deployment-ready | `NOT_VERIFIED` | model lock에서 false | M-C 이후에도 별도 승인 필요 |

## 상태 의미

- `VERIFIED`: 현재 자료로 해당 문서·계약·정적 검사를 확인함
- `NOT_VERIFIED`: 자료는 있으나 요구 수준을 충족했다고 선언하지 않음
- `UNKNOWN`: 자료가 없어 의미를 판단할 수 없음
- `BLOCKED_HARDWARE`: 센서·물리 환경이 없어 확인할 수 없음
