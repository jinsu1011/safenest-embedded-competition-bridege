# SafeNest 책임 영역별 저장소 재편 작업용 상세 실행 프롬프트

아래 프롬프트를 새 Codex 작업 또는 다른 작업자에게 그대로 전달한다. 이 문서는 현재 작업 트리에서 중단된 상태를 이어서 처리하는 방법과, 필요할 경우 기준 커밋부터 처음 재현하는 방법을 모두 포함한다.

---

## 실행 프롬프트 시작

당신은 SafeNest 저장소의 구조 재편 작업을 안전하게 마무리하는 담당자다. 단순히 파일을 정리하는 것이 아니라 Git 이력과 팀별 책임 경계, 기존 온디바이스 AI V4 패키지의 응집도, 바이너리 자산의 무결성을 모두 보존해야 한다.

### 1. 최종 목표와 완료 조건

저장소를 사람 이름이나 파일 종류만으로 나누지 말고, 다음과 같은 **기기 및 책임 영역 중심 구조**로 재편한다.

```text
devices/
├── co2/
├── pir/
├── mmwave/
└── thermal/

ondevice_ai/
├── config/
├── datasets/
├── models/
├── src/
│   ├── sensors/
│   ├── inference/
│   ├── risk/
│   ├── integrated_node/
│   ├── training/
│   └── tools/
├── benchmarks/
├── tests/
└── docs/

hardware/
└── 3d_models/

shared/
└── contracts/

docs/
archive/
```

완료 조건은 다음과 같다.

1. 사용자명 기반 디렉터리가 없고, 파일이 기기 또는 책임 영역 기준으로 배치되어 있다.
2. SafeNest V4 구현이 `ondevice_ai/` 아래에서 한 패키지로 파악 가능하다.
3. 여러 영역이 함께 쓰는 센서 계약만 `shared/contracts/`에 있다.
4. 3D 프린팅 자산은 `hardware/3d_models/`에 있다.
5. 이동 전후 추적 파일 수와 파일 내용의 SHA-256 집합이 동일하다.
6. import, 설정, 모델·데이터 경로, 테스트 경로가 새 구조와 일치한다.
7. Python 단위·통합 테스트와 ESP32 PlatformIO 빌드가 통과한다.
8. 각 책임 영역 README, `.github/CODEOWNERS`, provenance 문서가 갱신되어 있다.
9. 아래 세 커밋의 책임이 섞이지 않는다.
   - 1차: `git mv`만 사용한 순수 이동
   - 2차: import 및 설정·실행 경로 수정
   - 3차: README, CODEOWNERS, provenance 및 문서 수정
10. 작업 브랜치만 push하고 기존 Draft PR을 갱신한다. `main` 병합, force push, 기존 담당자 브랜치 삭제는 하지 않는다.

이 작업은 핵심 구조와 이력에 영향을 주므로 신중 모드로 진행한다. 각 단계가 끝날 때마다 `git status`, diff, 파일 수, 해시 또는 테스트 결과로 확인한 후 다음 단계로 넘어간다.

### 2. 저장소와 현재 알려진 기준점

- 저장소: `https://github.com/jinsu1011/safenest-embedded-competition`
- 로컬 작업 경로: `/Users/kimjinsu/Documents/임베디드 소프트웨어 경진대회`
- 작업 브랜치: `refactor/integrated-v4-architecture`
- 원격 작업 브랜치 기준 커밋: `2509525a06a46e154896118df58decb0256aee05`
- 순수 이동 커밋: `38274c084544af6f26b1377e593b012628a7eb05`
- 기존 Draft PR: `https://github.com/jinsu1011/safenest-embedded-competition/pull/2`

원본 추적 정보는 다음 값을 유지한다.

| 책임 영역 | 원본 ref | 원본 커밋 |
|---|---|---|
| 온디바이스 AI V4 | `origin/Ondevice_AI` | `d97df3e` |
| mmWave 통합 | `codex/mmwave-phase-integration` | `b0d3c95` |
| 3D 프린팅 | `origin/3D_Print` | `35c1e1f` |
| 통합 기준 | `origin/main` | `01a4acb` |
| 기획 PDF 원본 | 관련 이력 | `66eb105` |

`BRANCH_PROVENANCE.md`에 이미 기록된 원본 ref와 커밋 값은 바꾸거나 축약하지 말고, 이동한 새 경로만 갱신한다.

### 3. 절대 안전 규칙

- `main`에서 직접 작업하거나 `main`에 push하지 않는다.
- `git reset --hard`, `git clean -fdx`, force push를 사용하지 않는다.
- 기존 원격 브랜치를 병합·삭제하지 않는다.
- 이름이 같다는 이유로 파일을 삭제하거나 덮어쓰지 않는다.
- `.npz`, `.jsonl`, `.tflite`, `.stl`, 측정 자료, PDF, DOCX를 삭제하거나 다시 생성하지 않는다.
- 작업 트리의 기존 변경을 먼저 확인하고, 사용자 변경을 임의로 되돌리지 않는다.
- 실패한 테스트를 성공으로 보고하지 않는다.
- 순수 이동 커밋에는 내용 수정이나 새 문서를 넣지 않는다.
- 2차 경로 수정 커밋에는 README, CODEOWNERS, provenance 변경을 섞지 않는다.
- 3차 문서 커밋에 코드 변경을 섞지 않는다.
- 팀 검토 전에는 PR을 merge하지 않는다.
- 이 프롬프트 자체는 3차 문서 작업에 해당한다. 2차 커밋에 포함하지 않는다.

### 4. 시작 직후 반드시 수행할 사전 점검

먼저 다음을 실행하고 결과를 기록한다.

```bash
cd '/Users/kimjinsu/Documents/임베디드 소프트웨어 경진대회'
git status --short --branch
git branch --show-current
git rev-parse HEAD
git log --oneline --decorate -5
git remote -v
```

네트워크가 허용되면 원격 ref만 갱신한다. pull 또는 merge는 하지 않는다.

```bash
git fetch --all --prune
git status --short --branch
```

현재 작업 트리에 사용자 변경이나 예상하지 못한 파일이 있으면 즉시 덮어쓰지 않는다. `git diff --name-status`, `git diff --stat`, `git status --short`로 범위를 파악하고 이 문서의 “현재 중단 상태”와 비교한다.

### 5. 시작 경로 선택

현재 checkout 상태에 따라 아래 두 경로 중 하나만 선택한다.

#### 경로 A — 현재 중단 지점에서 이어서 작업하기(권장)

다음 조건이면 경로 A를 사용한다.

- 현재 브랜치가 `refactor/integrated-v4-architecture`다.
- HEAD가 `38274c084544af6f26b1377e593b012628a7eb05`다.
- 2차 경로 수정에 해당하는 수정 파일들이 작업 트리에 남아 있다.

이 경우 1차 이동을 다시 수행하거나 다시 커밋하지 않는다. 곧바로 6절의 현재 중단 상태를 확인한 뒤 8절의 2차 작업을 이어간다.

#### 경로 B — 원격 기준 커밋부터 처음 재현하기

현재 작업 트리가 깨끗하고, 이동 커밋 이전부터 다시 실행해야 할 때만 사용한다. 기존 변경이 있으면 먼저 별도 임시 브랜치 또는 stash로 보호하고, 보호 사실과 복구 명령을 기록한다.

```bash
git switch refactor/integrated-v4-architecture
git rev-parse HEAD
```

HEAD가 `2509525a06a46e154896118df58decb0256aee05`인 깨끗한 상태에서만 7절의 순수 이동을 수행한다. 이미 `38274c0`이 있으면 7절을 건너뛴다.

### 6. 현재 중단 상태 — 이어서 작업할 때 가장 중요한 정보

현재 로컬 작업은 다음 상태에서 중단되었다.

- 브랜치: `refactor/integrated-v4-architecture`
- 로컬 HEAD: `38274c084544af6f26b1377e593b012628a7eb05`
- 원격 브랜치 HEAD: `2509525a06a46e154896118df58decb0256aee05`
- 로컬 브랜치가 원격보다 1커밋 앞서 있다.
- `38274c0`은 순수 이동 커밋이며 331 files changed, 0 insertions, 0 deletions이다.
- 이 커밋은 아직 push하지 않았다.
- 2차 경로 수정이 작업 트리에 남아 있으며 아직 테스트·커밋되지 않았다.
- 3차 README, CODEOWNERS, provenance 작업은 아직 시작하지 않았다.
- 이 프롬프트 파일은 새 문서이므로 3차 커밋에만 포함한다.

현재 2차 작업으로 수정된 것으로 알려진 파일은 다음과 같다.

```text
devices/co2/src/co2_adapter.py
devices/co2/src/mock_sensor.py
devices/mmwave/firmware/build_valid_log_manifest.py
devices/mmwave/src/mmwave_adapter.py
devices/mmwave/src/mock_sensor.py
devices/mmwave/src/mr60_esp_adapter.py
devices/mmwave/src/run_mr60_serial_adapter.py
devices/mmwave/tests/test_mmwave_input_adapter.py
devices/mmwave/tests/test_mmwave_stream_adapter.py
devices/mmwave/tests/test_mr60_esp_adapter.py
devices/mmwave/tests/test_mr60_manifest.py
devices/pir/src/mock_sensor.py
devices/pir/src/pir_adapter.py
devices/thermal/src/mock_sensor.py
devices/thermal/src/thermal44_driver.py
ondevice_ai/benchmarks/benchmark_thermal.py
ondevice_ai/src/inference/infer_pi_thermal.py
ondevice_ai/src/integrated_node/run_demo.py
ondevice_ai/src/integrated_node/run_mr60_usb_node.py
ondevice_ai/src/integrated_node/run_node.py
ondevice_ai/src/integrated_node/safenest_risk_engine.py
ondevice_ai/src/risk/fallback.py
ondevice_ai/src/risk/risk_engine.py
ondevice_ai/src/tools/build_v4_archive.py
ondevice_ai/src/tools/test_thermal_tflite.py
ondevice_ai/src/tools/verify_safenest_learning_examples.py
ondevice_ai/src/training/thermal_prep.py
ondevice_ai/src/training/thermal_train.py
ondevice_ai/tests/test_fallback.py
ondevice_ai/tests/test_fault_injection.py
ondevice_ai/tests/test_mmwave_interpreter.py
ondevice_ai/tests/test_risk_engine.py
ondevice_ai/tests/test_risk_rules.py
ondevice_ai/tests/test_sensor_adapters.py
ondevice_ai/tests/test_thermal_interpreter.py
ondevice_ai/tests/test_three_model_integration.py
ondevice_ai/tests/test_v4_pipeline.py
shared/contracts/base_sensor.py
```

예상 diff 통계는 38 files changed, 161 insertions, 141 deletions이지만, 이것을 진실로 가정하지 말고 실제 상태를 확인한다.

```bash
git status --short
git diff --stat
git diff --name-only
git diff --check
```

이미 반영된 것으로 보이는 주요 변경은 다음과 같지만 전수 검토와 테스트가 필요하다.

- `src.inference` → `ondevice_ai.src.inference`
- `src.risk` → `ondevice_ai.src.risk`
- `src.integrated_node` → `ondevice_ai.src.integrated_node`
- 센서 import → `devices.<device>.src...`
- 공용 센서 계약 import → `shared.contracts.base_sensor`
- 일부 실행 스크립트와 테스트의 저장소 루트 계산 수정
- MR60 기본 설정 경로를 `devices/mmwave/config/` 기준으로 수정
- MR60 manifest builder의 신규 경로 일부 수정
- `build_v4_archive.py`의 새 디렉터리 트리 반영
- thermal 학습·전처리 스크립트의 기준 경로 수정

아직 어떤 변경도 검증되었다고 간주하지 않는다.

### 7. 1차 커밋을 처음 재현할 때의 순수 이동 절차

이 절은 경로 B에서만 수행한다. 새 파일 생성, 내용 수정, import 수정 없이 `mkdir -p`와 `git mv`만 사용한다. 빈 디렉터리는 Git이 추적하지 않으므로 필요한 README는 3차에 만든다.

이동 전 기준을 기록한다.

```bash
git ls-files | wc -l
git ls-files -z | xargs -0 shasum -a 256 | awk '{print $1}' | LC_ALL=C sort | shasum -a 256
git status --short
```

기대 기준값은 다음과 같다.

- 추적 파일 수: `350`
- 경로 독립 SHA-256 multiset digest: `b572a90fe52b04aed07375deb900310df7255dcabd28d0cae75ab59c2e2c6a92`

디렉터리를 준비한다.

```bash
mkdir -p devices/co2/src devices/pir/src devices/mmwave/src devices/mmwave/config devices/mmwave/tests devices/mmwave/docs devices/thermal/src
mkdir -p ondevice_ai/src ondevice_ai/config ondevice_ai/datasets ondevice_ai/models ondevice_ai/benchmarks ondevice_ai/tests ondevice_ai/docs
mkdir -p shared/contracts hardware/3d_models
```

다음 매핑 원칙으로 `git mv`한다.

1. `firmware/README.md` → `devices/mmwave/README.md`
2. ESP32 mmWave PlatformIO 프로젝트 → `devices/mmwave/firmware/`
3. CO2, PIR, mmWave, Thermal 센서 구현 → 각 `devices/<device>/src/`
4. 공용 `base_sensor.py` → `shared/contracts/base_sensor.py`
5. 온디바이스 AI inference, risk, integrated node, training, tools → `ondevice_ai/src/`
6. mmWave processing 설정 → `devices/mmwave/config/`
7. 나머지 V4 설정 → `ondevice_ai/config/`
8. 데이터셋과 모델 → 각각 `ondevice_ai/datasets/`, `ondevice_ai/models/`
9. 벤치마크 → `ondevice_ai/benchmarks/`
10. mmWave 기기 단독 테스트 4종 → `devices/mmwave/tests/`
11. 나머지 V4 테스트 → `ondevice_ai/tests/`
12. V4 문서 → `ondevice_ai/docs/`, V4 메인 README → `ondevice_ai/README.md`
13. mmWave 운용 문서 → `devices/mmwave/docs/`
14. STL/CAD → `hardware/3d_models/`
15. V4 requirements 파일 → `ondevice_ai/`

파일별 실제 이름은 먼저 `git ls-files`로 확인하고, 존재하지 않는 경로를 추측해 생성하지 않는다. 충돌 가능성이 있으면 양쪽 SHA-256과 내용을 비교한 뒤 중단하고 기록한다.

순수 이동 후 반드시 확인한다.

```bash
git status --short
git diff --cached --stat
git diff --cached --summary
git diff --cached --numstat
git ls-files | wc -l
git ls-files -z | xargs -0 shasum -a 256 | awk '{print $1}' | LC_ALL=C sort | shasum -a 256
```

다음 조건을 모두 만족할 때만 커밋한다.

- 파일 수가 350이다.
- digest가 `b572a90f...e2c6a92`와 일치한다.
- `git diff --cached --numstat`에 내용 삽입·삭제가 없다.
- 삭제만 된 파일 또는 새 파일만 된 파일이 아니라 rename으로 인식된다.

```bash
git commit -m 'refactor: move files into responsibility domains'
```

이미 존재하는 정상 커밋은 `38274c084544af6f26b1377e593b012628a7eb05`다. 이 커밋을 수정하거나 amend하지 않는다.

### 8. 2차 커밋 — import 및 설정·실행 경로 수정

#### 8.1 패키지 경계 원칙

- 기기 담당 구현은 `devices.<device>.src`에서 import한다.
- 공용 센서 인터페이스는 `shared.contracts.base_sensor`에서 import한다.
- V4 내부 모듈은 `ondevice_ai.src.<area>` 경로를 사용한다.
- 온디바이스 AI가 기기별 실구현을 사용할 때는 명시적으로 `devices.<device>...`를 import한다.
- `ondevice_ai/src/sensors/`에는 공용 registry 또는 V4 관점의 sensor orchestration만 둔다. 기기 드라이버 복사본을 새로 만들지 않는다.
- 임시 `sys.path` 추가가 불가피한 CLI 파일은 저장소 루트를 정확히 계산하고, 중복 또는 현재 디렉터리에 의존하는 경로를 제거한다.

#### 8.2 전수 검색

이동 전 경로와 과거 패키지명이 남아 있는지 검색한다.

```bash
rg -n 'SafeNest_V4_OnDevice_AI|sheepmeat|src\.inference|src\.risk|src\.integrated_node|src\.sensors|models/|datasets/|config/' \
  devices ondevice_ai shared tests docs README.md BRANCH_PROVENANCE.md 2>/dev/null
```

검색 결과를 무조건 일괄 치환하지 않는다. 다음 세 종류를 구분한다.

1. 실행 코드·설정의 실제 경로: 반드시 새 경로로 수정
2. 사용자 안내 문서의 실행 명령·링크: 3차 문서 커밋에서 수정
3. 원본 이력이나 과거 구조를 설명하는 provenance: 원본 경로는 역사적 사실로 유지하고 새 경로만 병기

#### 8.3 설정 및 자산 경로

아래 파일과 관련 호출부를 우선 점검한다.

- `ondevice_ai/config/models.yaml`
- `ondevice_ai/config/sensors.yaml`
- `ondevice_ai/config/risk_rules.yaml`
- `ondevice_ai/src/inference/model_registry.py`
- `ondevice_ai/src/integrated_node/run_node.py`
- `ondevice_ai/src/integrated_node/run_demo.py`
- `ondevice_ai/src/integrated_node/run_mr60_usb_node.py`
- `devices/mmwave/src/run_mr60_serial_adapter.py`
- `devices/mmwave/firmware/build_valid_log_manifest.py`
- `ondevice_ai/src/tools/build_v4_archive.py`
- thermal 학습·전처리·벤치마크 스크립트

경로는 실행 위치가 저장소 루트인지, `ondevice_ai/`인지, 해당 기기 디렉터리인지 명확히 정의한다. 가능하면 `Path(__file__).resolve()`를 기준으로 계산해 현재 셸 디렉터리에 대한 의존을 없앤다.

최종 자산 기준은 다음과 같다.

- 모델: `ondevice_ai/models/`
- 데이터셋: `ondevice_ai/datasets/`
- V4 설정: `ondevice_ai/config/`
- mmWave 기기 설정: `devices/mmwave/config/`
- mmWave firmware: `devices/mmwave/firmware/`
- 공용 계약: `shared/contracts/`

#### 8.4 Python 패키지 파일

필요한 `__init__.py`가 이동 후 존재하는지 확인한다.

```bash
find devices ondevice_ai shared -name '__init__.py' -print | sort
```

import가 테스트 환경에서 namespace package에 우연히 의존하지 않도록 확인하되, 새 `__init__.py` 추가는 내용 변경이므로 2차 커밋에 포함한다. 기존 파일을 복제하지 않는다.

#### 8.5 테스트 실행

기존 작업에서 사용한 가상환경이 있으면 다음 인터프리터를 우선 사용한다.

```bash
/private/tmp/safenest-refactor-venv/bin/python -m unittest discover -s ondevice_ai/tests -p 'test_*.py'
/private/tmp/safenest-refactor-venv/bin/python -m unittest discover -s devices/mmwave/tests -p 'test_*.py'
```

가상환경이 없으면 저장소 의존성을 확인한 뒤 별도의 임시 가상환경을 만든다. 저장소 안에 `.venv`나 생성 자산을 추가하지 않는다. 의존성 설치가 네트워크 승인을 요구하면 사용자 승인을 받는다.

기존 기준으로 예상되는 결과는 합계 84개 테스트 성공, 2개 skip이지만 실제 출력만 보고한다. 테스트 수가 달라졌다면 누락된 discovery 경로 또는 import 오류를 조사한다.

구문 및 import 점검도 수행한다.

```bash
python3 -m compileall -q devices ondevice_ai shared
git diff --check
```

#### 8.6 PlatformIO 빌드

```bash
cd '/Users/kimjinsu/Documents/임베디드 소프트웨어 경진대회/devices/mmwave/firmware'
pio run
cd '/Users/kimjinsu/Documents/임베디드 소프트웨어 경진대회'
```

빌드 출력 디렉터리는 Git에 추가하지 않는다. 실패하면 코드 오류와 로컬 도구·보드 패키지 부족을 구분해 기록한다.

#### 8.7 아카이브·패키징 도구 점검

`build_v4_archive.py`가 새 구조에서 필요한 V4 파일을 포함하고 기기별 구현과 공용 계약을 올바른 상대 경로로 담는지 확인한다. 생성 결과는 임시 디렉터리에 만들고 다음을 점검한다.

- `.tflite`, `.npz`, 설정 파일 포함 여부
- 사용자명 기반 디렉터리 미포함
- 절대 경로 미포함
- archive 안의 import 경로가 실제 디렉터리와 일치
- 생성물은 별도 요청이 없으면 Git에 추가하지 않음

#### 8.8 2차 커밋 직전 선택적 staging

이 프롬프트, README, CODEOWNERS, provenance는 stage하지 않는다. 코드와 설정 경로 수정만 명시적으로 stage한다.

```bash
git status --short
git diff --check
git diff --name-only
```

파일 목록을 확인한 뒤 `git add`에는 2차 대상 경로만 명시한다. `git add .`는 사용하지 않는다. staged diff에 문서가 없는지 확인한다.

```bash
git diff --cached --name-status
git diff --cached --stat
git diff --cached
git commit -m 'refactor: update paths for responsibility domains'
```

커밋 후 테스트를 한 번 더 실행하고 결과를 기록한다.

### 9. 3차 커밋 — README, CODEOWNERS, provenance, 링크 갱신

#### 9.1 README 범위

최소 다음 README를 확인하거나 작성한다.

```text
devices/README.md
devices/co2/README.md
devices/pir/README.md
devices/mmwave/README.md
devices/thermal/README.md
ondevice_ai/README.md
hardware/README.md
hardware/3d_models/README.md
shared/README.md
shared/contracts/README.md
docs/README.md
archive/README.md
```

기존 README가 있으면 내용을 덮어쓰지 말고 새 구조에 맞게 확장한다. 모든 README에는 아래 11개 항목이 명확히 있어야 한다.

1. 디렉터리 목적
2. 시스템에서 담당하는 기능
3. 포함해야 하는 파일 유형
4. 포함하면 안 되는 파일 유형
5. 주요 하위 구성
6. 입력과 출력 인터페이스
7. 다른 기능 영역과의 관계
8. 실행·학습·추론 또는 활용 방법
9. 현재 개발 상태 및 버전
10. 향후 파일 추가 및 관리 규칙
11. 주요 기여자와 원본 브랜치·커밋 추적 정보

담당자 이름만 적지 말고 GitHub handle, 책임 범위, 원본 ref/commit을 함께 기록한다. 개인정보성 사용자 폴더는 만들지 않는다.

현재 문서에서 추정되는 기본 책임자는 다음과 같다. 최종 반영 전에 저장소 기여 이력과 collaborator handle을 확인한다.

| 책임 영역 | 담당 | GitHub handle |
|---|---|---|
| mmWave 및 통합 | Jinsu | `@jinsu1011` |
| OnDevice AI 및 융합 | Junwoo | `@sheepmeat` |
| CO2 및 배선 | Seungha | `@yuseungha` |
| Thermal | Taegyun | `@rla1729` — 반드시 확인 |
| PIR, 하우징, UX | Yuna | `@yuname121` |

#### 9.2 CODEOWNERS

`.github/CODEOWNERS`를 추가한다. 초안은 다음과 같지만 존재하는 collaborator와 정확한 handle을 확인한 뒤 확정한다.

```text
* @jinsu1011
/devices/co2/ @yuseungha
/devices/pir/ @yuname121
/devices/mmwave/ @jinsu1011
/devices/thermal/ @rla1729
/ondevice_ai/ @sheepmeat @jinsu1011
/hardware/3d_models/ @yuname121
/shared/contracts/ @sheepmeat @jinsu1011
/docs/ @jinsu1011
/archive/ @jinsu1011
```

특히 `@rla1729`가 정확한지, 각 사용자가 저장소에 review 권한을 가질 수 있는지 확인한다. 확인할 수 없으면 추정값을 확정 사실로 쓰지 말고 TODO와 근거를 명시한다.

#### 9.3 provenance 문서

`BRANCH_PROVENANCE.md`의 원본 ref와 commit을 그대로 보존한다. 다음을 추가 또는 갱신한다.

- 이전 경로
- 새 책임 영역 경로
- 이동 커밋 `38274c0`
- 경로 수정 커밋
- 어떤 파일이 어느 원본 브랜치에서 왔는지
- legacy가 `archive/`로 간 이유와 원본 경로
- 삭제·재생성 없이 이동했음을 검증한 파일 수와 digest

역사적 문맥에 있는 `SafeNest_V4_OnDevice_AI` 같은 이름은 삭제하지 않는다. 현재 실행 경로와 혼동되지 않도록 “원본 경로”라고 표시한다.

#### 9.4 루트 README

루트 `README.md`에는 다음을 반영한다.

- 책임 영역별 디렉터리 설명
- 전체 실행·테스트 명령의 새 경로
- 기기별 담당 범위
- 기여자가 본인 코드를 커밋하는 과정
- 규칙에 맞는 작업 브랜치 생성 방법
- Pull Request가 무엇인지와 생성·리뷰·수정·병합 절차
- `main` direct push 금지
- PR 전 테스트와 reviewer 지정 방법

권장 Git 흐름 예시는 다음과 같다.

```bash
git switch main
git pull --ff-only origin main
git switch -c '<type>/<device-or-topic>-<short-description>'

# 작업 후
git status
git add <검토한 파일만 명시>
git diff --cached
git commit -m '<type>: <summary>'
git push -u origin '<branch-name>'
```

브랜치 예시:

- `feature/co2-calibration`
- `fix/mmwave-serial-parser`
- `refactor/ondevice-ai-model-registry`
- `docs/hardware-assembly-guide`

PR 설명에는 변경 목적, 변경 범위, 검증 명령과 결과, 하드웨어 영향, 남은 위험, reviewer를 적도록 안내한다.

#### 9.5 Markdown 링크와 명령 전수 점검

```bash
rg -n 'firmware/esp_wroom32_mr60_monitor|src/sensors|src/inference|src/risk|src/integrated_node|models/|datasets/|config/|hardware/3d_print|SafeNest_V4_OnDevice_AI' \
  --glob '*.md' .
```

각 결과를 실행 경로, 링크, 역사적 provenance로 구분해 수정한다. Markdown 상대 링크는 실제 존재하는지 확인한다.

#### 9.6 3차 커밋

코드 변경이 섞이지 않았는지 확인한다.

```bash
git status --short
git diff --check
git diff --name-status
git diff --stat
```

문서, `.github/CODEOWNERS`, provenance만 선택적으로 stage하고 커밋한다.

```bash
git diff --cached --name-status
git diff --cached --stat
git commit -m 'docs: define responsibility ownership and provenance'
```

### 10. 바이너리와 파일 무결성 검증

순수 이동 전후 전체 내용 digest가 일치해야 한다. 현재 알려진 기준은 다음과 같다.

- 추적 파일 수: `350`
- 전체 경로 독립 digest: `b572a90fe52b04aed07375deb900310df7255dcabd28d0cae75ab59c2e2c6a92`

중요 바이너리의 알려진 SHA-256은 다음과 같다. 실제 파일명과 새 경로를 찾아 각각 비교한다.

| 자산 | SHA-256 |
|---|---|
| CO2 NPZ | `bff5cd76...f6eea` |
| mmWave NPZ | `a08072f3...107fb` |
| planning PDF | `ba17b589...d0462` |
| STL 1 | `ebbb978c...32d2f` |
| STL 2 | `b409d754...bd5e` |
| STL 3 | `9c2bae53...68da` |
| STL 4 | `6d7c9804...59a` |
| CO2 TFLite | `3a8c86c4...d0462` |
| mmWave TFLite | `43cdd6f3...f0158` |
| Thermal TFLite | `5b56da8d...6ae84` |

위 표의 값은 사람이 읽기 쉽게 축약되어 있으므로 검증 기준으로 직접 문자열 비교하지 않는다. Git 이동 전 커밋과 현재 파일의 blob 또는 전체 SHA-256을 직접 계산한다.

권장 검증 방식:

```bash
git ls-tree -r --long 2509525a06a46e154896118df58decb0256aee05
find ondevice_ai hardware docs -type f \( -name '*.npz' -o -name '*.tflite' -o -name '*.stl' -o -name '*.pdf' -o -name '*.docx' \) -print0 | xargs -0 shasum -a 256
```

경로가 바뀌었으므로 파일명과 크기, Git blob hash, SHA-256을 조합해 대응시킨다. 불일치가 하나라도 있으면 push하지 않는다.

### 11. 최종 회귀 검증

세 커밋이 준비된 뒤 다음을 순서대로 수행한다.

```bash
git status --short --branch
git log --oneline --decorate -6
git diff 2509525a06a46e154896118df58decb0256aee05..HEAD --stat
git diff --check 2509525a06a46e154896118df58decb0256aee05..HEAD
```

Python:

```bash
/private/tmp/safenest-refactor-venv/bin/python -m unittest discover -s ondevice_ai/tests -p 'test_*.py'
/private/tmp/safenest-refactor-venv/bin/python -m unittest discover -s devices/mmwave/tests -p 'test_*.py'
python3 -m compileall -q devices ondevice_ai shared
```

Firmware:

```bash
cd devices/mmwave/firmware
pio run
cd ../../..
```

구조와 잔존 경로:

```bash
find devices ondevice_ai hardware shared docs archive -maxdepth 3 -type d | sort
find . -type d \( -name 'sheepmeat' -o -name 'SafeNest_V4_OnDevice_AI' \) -print
rg -n 'firmware/esp_wroom32_mr60_monitor|hardware/3d_print' --glob '!*.git*' .
```

마지막으로 다음을 확인한다.

- 테스트 결과를 실제 실행 출력과 함께 기록했다.
- skip은 이유를 확인했다.
- PlatformIO 빌드 성공 또는 정확한 환경 blocker가 기록되었다.
- 작업 트리에 빌드 산출물, 캐시, 임시 archive가 없다.
- `.pyc`, `__pycache__`, `.pio` 같은 산출물이 stage되지 않았다.
- 세 커밋의 diff 범위가 서로 분리되어 있다.
- `main`을 수정하지 않았다.

### 12. Push와 기존 Draft PR 갱신

모든 검증이 통과한 뒤에만 현재 작업 브랜치를 push한다. force push하지 않는다.

```bash
git branch --show-current
git status --short --branch
git push origin refactor/integrated-v4-architecture
```

기존 Draft PR #2를 새로 만들지 말고 갱신한다. 인증 설정이 기존 임시 경로를 사용한다면 다음과 같이 조회한다.

```bash
env GH_CONFIG_DIR=/private/tmp/safenest-gh-config gh pr view 2 --json number,title,url,isDraft,headRefName,baseRefName,state
```

PR 설명에는 다음을 포함한다.

- 책임 영역 구조로 변경한 이유
- 3개 커밋의 역할
- 파일 수와 SHA-256 검증 결과
- Python 테스트 수와 결과
- PlatformIO 빌드 결과
- CODEOWNERS의 검토 필요 handle
- 기존 원격 담당자 브랜치를 삭제하지 않았다는 사실
- `main` 병합은 팀 검토 후 별도로 수행한다는 사실

PR은 Draft 상태를 유지하고 merge하지 않는다.

### 13. 실패 및 복구 원칙

- 같은 명령이 같은 이유로 두 번 실패하면 반복하지 않는다.
- import 실패 시 누락 패키지, 잘못된 repo root, 상대 import, 실행 위치를 분리해 진단한다.
- 테스트 discovery 수가 줄면 테스트 파일 이동 누락과 package import 실패를 우선 확인한다.
- 바이너리 hash 불일치 시 새 파일로 교체하지 말고 원본 커밋의 blob과 현재 파일을 비교한다.
- staging이 섞였으면 파일 내용을 되돌리지 말고 안전하게 unstage한 뒤 범위를 다시 선택한다. `reset --hard`는 금지한다.
- 예상하지 못한 사용자 변경과 충돌하면 그 파일은 건드리지 않고 변경 범위와 필요한 결정을 보고한다.
- 네트워크 또는 도구 설치가 막히면 로컬에서 가능한 정적 검증까지 수행하고 정확한 blocker와 미검증 항목을 남긴다.

### 14. 작업 완료 보고 형식

최종 보고는 다음 순서로 작성한다.

1. 결과 요약: 최종 구조와 브랜치·PR 상태
2. 커밋 목록: 해시, 제목, 포함 범위
3. 이동 무결성: 전후 파일 수, digest, 중요 바이너리 확인 결과
4. 검증 결과: 실행한 명령, 테스트 수, skip, PlatformIO 결과
5. 문서 및 ownership: 작성 README, CODEOWNERS reviewer, provenance 보존 상태
6. 미해결 사항: 확인이 필요한 GitHub handle, 하드웨어 실기 테스트 등
7. 안전 확인: main 미병합, force push 없음, 담당자 브랜치 삭제 없음

성공하지 않은 항목은 숨기지 말고 “미검증” 또는 “실패”로 명시한다. 완료 조건을 다시 읽고 모든 항목에 근거가 있을 때만 작업 완료라고 보고한다.

## 실행 프롬프트 끝

---

## 이 문서를 작성한 시점의 주의사항

이 문서는 후속 작업자를 위한 실행 지침이다. 작성 시점에는 순수 이동 커밋만 만들어졌고, 2차 경로 수정은 작업 트리에 있으나 아직 검증·커밋되지 않았다. 따라서 후속 작업자는 반드시 4절과 6절부터 실제 상태를 재확인해야 한다.
