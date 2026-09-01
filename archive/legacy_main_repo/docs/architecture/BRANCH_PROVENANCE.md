# 브랜치 및 자산 provenance

원본 ref와 원본 커밋 값은 역사적 사실이므로 바꾸거나 축약하지 않는다. 구조가 바뀔 때는 **최종 경로만** 갱신한다.

## 통합 기준

아래 "원본 경로"는 통합 당시의 경로이며 현재 실행 경로가 아니다. 현재 경로는 "최종 경로" 열을 따른다.

| 영역 | 원본 ref | 원본 경로 | 최종 경로 |
|---|---|---|---|
| V4 추론·위험도·통합·테스트 | `origin/Ondevice_AI` (`d97df3e`) | `./`의 `src/`, `models/`, `datasets/`, `config/`, `tests/` | `ondevice_ai/src/`, `ondevice_ai/models/`, `ondevice_ai/datasets/`, `ondevice_ai/config/`, `ondevice_ai/tests/`, `ondevice_ai/benchmarks/` |
| V4 센서 어댑터 | `origin/Ondevice_AI` (`d97df3e`) | `src/sensors/<device>/` | `devices/co2/src/`, `devices/pir/src/`, `devices/mmwave/src/`, `devices/thermal/src/` |
| 공용 센서 계약 | `origin/Ondevice_AI` (`d97df3e`) | `src/sensors/base_sensor.py` | `shared/contracts/base_sensor.py` |
| MR60 AI/ESP 보강 | `codex/mmwave-phase-integration` (`b0d3c95`) | `./`, `firmware/esp_wroom32_mr60_monitor/`, `SafeNest_V4_OnDevice_AI/` | `devices/mmwave/firmware/`, `devices/mmwave/config/`, `devices/mmwave/tests/`, `docs/mmwave/`, `ondevice_ai/` |
| CAD 4종 | `origin/3D_Print` (`35c1e1f`) | 루트 STL 4종 → `hardware/3d_print/` | `hardware/3d_models/` |
| 초기 위험도 엔진 | `origin/main` 계보 | `pi/` | `archive/legacy_prototypes/pi/` |
| 기획 PDF | `66eb105` | `docs/ai/roadmap_and_setup/` | `docs/planning/` |

통합 기준 브랜치는 fetch 후 `origin/main`의 `01a4acb`이며, 작업 시작 전 로컬 복구 지점과 전체 해시는 루트 `INTEGRATION_PROGRESS.md`에 기록했다.

역사적 문맥에 등장하는 `SafeNest_V4_OnDevice_AI/`, `firmware/esp_wroom32_mr60_monitor/`, `src/sensors/`, `hardware/3d_print/`는 **원본 경로**이며 현재 저장소에는 존재하지 않는다.

## 책임 영역 재편 (2026-08-03)

파일 종류별 최상위 디렉터리(`src/`, `models/`, `datasets/`, `config/`, `tests/`)를 기기·책임 영역 중심 구조로 재편했다. 목적은 소규모 팀에서 각 담당 영역을 즉시 파악하면서도 V4 구현의 전체 맥락을 `ondevice_ai/` 한 곳에 유지하는 것이다.

작업은 책임이 섞이지 않도록 커밋을 분리했다.

| 커밋 | 제목 | 범위 |
|---|---|---|
| `38274c0` | `refactor: move files into responsibility domains` | `git mv`만 사용한 순수 이동. 331 files changed, **0 insertions, 0 deletions** |
| `3313f4b` | `refactor: update paths for responsibility domains` | import 및 설정·실행 경로 수정. 39 files, 167+/147− |
| `32cdd1d` | `refactor: update remaining tool and analysis paths` | 2차에서 누락된 analysis_tools 절대경로, benchmark 출력 경로, 학습 가이드 인용 경로 |
| (본 커밋) | `docs: define responsibility ownership and provenance` | README, `.github/CODEOWNERS`, provenance |

기준 커밋은 원격 `refactor/integrated-v4-architecture`의 `2509525`다.

### 경로 매핑

| 이전 경로 | 새 경로 |
|---|---|
| `firmware/esp_wroom32_mr60_monitor/` | `devices/mmwave/firmware/` |
| `src/sensors/co2/` | `devices/co2/src/` |
| `src/sensors/pir/` | `devices/pir/src/` |
| `src/sensors/mmwave/` | `devices/mmwave/src/` |
| `src/sensors/thermal44/` | `devices/thermal/src/` |
| `src/sensors/base_sensor.py` | `shared/contracts/base_sensor.py` |
| `src/inference/`, `src/risk/`, `src/integrated_node/`, `src/training/`, `src/tools/` | `ondevice_ai/src/` 아래 동일 이름 |
| `models/`, `datasets/`, `config/`(V4분) | `ondevice_ai/models/`, `ondevice_ai/datasets/`, `ondevice_ai/config/` |
| `config/mmwave_processing.json` | `devices/mmwave/config/mmwave_processing.json` |
| `tests/benchmarks/` | `ondevice_ai/benchmarks/` |
| `tests/`(mmWave 기기 단독 4종) | `devices/mmwave/tests/` |
| `tests/`(나머지) | `ondevice_ai/tests/` |
| `hardware/3d_print/` | `hardware/3d_models/` |
| `docs/ai/`(V4 문서) | `ondevice_ai/docs/` |
| `docs/`(mmWave 운용) | `docs/mmwave/` |
| `requirements*.txt` | `ondevice_ai/requirements*.txt` |

### 이동 무결성 검증

삭제나 재생성 없이 이동했음을 다음으로 확인했다.

- 추적 파일 수: 이동 전 **350** → 이동 후 **350**
- 경로 독립 SHA-256 multiset digest (`38274c0` 시점): `b572a90fe52b04aed07375deb900310df7255dcabd28d0cae75ab59c2e2c6a92` — 기준값과 일치
- Git blob multiset이 `2509525`와 `38274c0`에서 완전히 동일 — 모든 `.npz`, `.tflite`, `.stl`, `.jsonl`, PDF를 포함한 전 파일의 내용이 바이트 단위로 보존됨
- 순수 이동 커밋의 numstat 합계가 0 insertions / 0 deletions이며 모든 변경이 rename으로 인식됨

재현 명령:

```bash
git ls-files | wc -l
git ls-tree -r 38274c0 | awk '{print $3}' | while read b; do git cat-file blob $b | shasum -a 256 | awk '{print $1}'; done | LC_ALL=C sort | shasum -a 256
```

### legacy가 `archive/`로 간 이유

`archive/legacy_prototypes/pi/`의 초기 위험도 엔진은 `origin/main` 계보의 규칙 기반 프로토타입으로, V4 가중치 융합 엔진(`ondevice_ai/src/risk/risk_engine.py`)이 대체했다. 삭제하지 않고 보존한 이유는 판정 로직 변화를 비교·감사할 수 있어야 하기 때문이다. `archive/legacy_prototypes/config/legacy_risk_rules.json`은 V4 `ondevice_ai/config/risk_rules.yaml`로 대체된 JSON 사본이며, 실행 경로에서 분리해 이중 원본이 생기지 않게 했다. archive에서는 import하지 않는다.

## 팀 문서 배치 규칙 적용 (2026-08-03, 후속)

팀 규칙을 **코드는 `devices/<sensor>/`, 읽을 문서는 `docs/<sensor>/`** 로 확정하고, mmWave 문서 7개를 `devices/mmwave/docs/`에서 `docs/mmwave/`로 옮겼다. 코드·펌웨어·실측 로그·분석 산출물은 `devices/mmwave/`에 그대로 있다.

| 커밋 | 제목 | 범위 |
|---|---|---|
| `f0470c6` | `docs: move mmWave device docs into docs/mmwave` | `git mv`만 사용한 순수 이동. 7 files, **0 insertions, 0 deletions** |
| `def9a24` | `docs: update references to relocated mmWave docs` | 이동한 문서를 가리키던 참조 갱신 |
| (본 커밋) | `docs: establish team doc placement rule` | CONTRIBUTING 배치 표, CODEOWNERS, README, `docs/mmwave/README.md` 색인 |

이동 무결성:

- 추적 파일 수: 이동 전 **360** → 이동 후 **360**
- 경로 독립 SHA-256 multiset digest: `dec35e35935020a4a69b5b612384113fb2ac565064d4c21b7545023f3fec4743` — 이동 전후 동일
- 7개 전부 rename으로 인식됨

`ondevice_ai/docs/`의 V4 패키지 내부 문서(`MR60_INTEGRATION.md`, `TEAM_HANDOFF_GUIDE.md`, `walkthrough.md`)는 이번 이동 대상이 아니며 `@sheepmeat` 담당 영역에 그대로 있다.

## 중복 처리 원칙

- 팀원명 디렉터리의 파일은 삭제 전 기능 브랜치 tree와 비교했다.
- 최신 끝점에 없는 고유 자산은 별도 복원했으며, legacy 구현은 `archive/`로 이관했다.
- V4 `ondevice_ai/config/risk_rules.yaml`만 공식 위험 규칙 원본으로 사용한다. JSON 사본은 실행 경로 밖 archive에 둔다.
- 모델, NPZ, JSONL, STL은 이름이 같아도 blob 또는 내용 비교 없이 덮어쓰지 않는다.

## 현재 확인할 수 없는 자산

프롬프트에 언급된 `.docx`와 dashboard `index.html`은 접근 가능한 모든 로컬·원격 ref에서 발견되지 않았다. 원본이 제공될 때까지 결손으로 유지하며 임의 재생성하지 않는다.
