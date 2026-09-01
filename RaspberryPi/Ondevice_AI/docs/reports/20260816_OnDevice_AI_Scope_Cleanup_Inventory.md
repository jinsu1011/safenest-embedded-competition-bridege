# SafeNest AI 작업본 범위 정리 인벤토리

**기준 저장소:** `sheepmeat/test`
**기준 커밋:** `efc7e2eb61a49e221ce0ebf6057b0c1617525ad1`
**정리일:** 2026-08-16

## 실제 실행 경로

현재 공식 AI 실행 경로는 `integrated_node/run_node.py`다. 이 entry point는
sensor provider 또는 fail-closed sensor adapter에서 결과를 받고, `inference/`의
모델 adapter를 거쳐 `risk/risk_engine.py`와 `risk/fallback.py`를 호출한다. 실센서
provider가 아직 없으면 정상값을 만들어내지 않고 `FAILED`를 출력한다.

따라서 `risk/`는 이름과 달리 과거 simulator가 아니라 현재 AI runtime·B9 validator·
active regression test가 쓰는 경로다. 이번 정리에서 risk 수식, threshold, fallback,
emergency 정책은 변경하지 않는다.

## 사전 분류

| 경로 | 목적과 근거 | 결정 |
|---|---|---|
| `models/`, `datasets/`, `scripts/` | 모델 계보, A/B evidence, validator 및 재현 계약 | `KEEP_ACTIVE_AI` |
| `inference/`, `preprocessing/`, `sensors/` | TFLite 추론, 입력 변환, provider와 AI의 경계 | `KEEP_ACTIVE_AI` |
| `risk/` | `run_node.py`, B9 script, active test가 import하는 fail-closed AI 위험도 경로 | `KEEP_ACTIVE_DEPENDENCY` |
| `integrated_node/run_node.py`, `runtime_config.py` | 현재 provider 주입과 mock/real fail-closed integration contract | `KEEP_ACTIVE_AI` |
| `integrated_node/virtual_sensor_streamer.py`, `safenest_integrated_plotter.py` | 합성 생체 packet과 GUI로 구성된 시연기이며 current runtime·test import 없음 | `ARCHIVE_LEGACY_SIMULATOR` |
| `integrated_node/safenest_risk_engine.py` | legacy compatibility이나 역사 test와 학습 문서가 직접 참조 | `DEFER_OWNER_DECISION` |
| `integrated_node/run_demo.py` | 현재 `run_node.py` mock mode를 호출하는 간단한 smoke demo | `KEEP_ACTIVE_DEPENDENCY` |

## archive 결과와 남은 경계

두 simulator 파일은 `git mv`로
`archive/project_history/legacy_simulator_20260816/integrated_node/`에 보관한다.
해당 archive는 `LEGACY_SIMULATOR_ONLY`, `NOT_CURRENT_PI_RUNTIME`이며 새 production
risk engine이 아니다.

`benchmarks/v5_file_sha256_audit.json`에 남아 있는 이전 경로와 해시는 당시 release
상태를 보존하는 역사 audit evidence다. 현재 runtime이나 test discovery가 읽는 import
목록이 아니므로, 이번 archive에 맞추려고 그 과거 증거를 다시 쓰지 않는다.

`safenest_risk_engine.py`는 legacy라는 사실과 archive 가능 여부를 분리한다. 이 파일을
옮기려면 이를 직접 import하는 역사 테스트와 학습 안내를 함께 archive하거나 재구성해야
한다. 현재 active tree의 회귀 범위를 임의로 줄이지 않기 위해 이번 변경에서는 남겨 둔다.

## 정리 후 활성 AI 책임

- **models:** runtime model metadata와 B-complete 후보의 계보·무결성 정보
- **inference:** TFLite 입출력 계약과 interpreter adapter
- **preprocessing:** 센서 입력을 모델 입력으로 바꾸는 규칙
- **scripts/validators:** A/B 단계 재현, 누수 검사, model/evidence 검증
- **tests:** active provider, fail-closed, model 계약 회귀 검사
- **sensor AI adapters:** 팀 device provider와 AI 사이의 표준 경계
- **integration contracts:** `run_node.py`의 provider injection과 향후 C 실측 검증 연결점

모델 기본값, B 후보 promotion, preprocessing, 실센서 코드, Pi capture, risk policy는 이
정리의 범위 밖이며 변경하지 않았다.
