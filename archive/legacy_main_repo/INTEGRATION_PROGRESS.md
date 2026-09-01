# SafeNest 구조 통합 진행 기록

> [!NOTE]
> **경로 표기 안내 (2026-08-03 추가)**
> 이 문서는 시간순 작업 기록이므로 본문의 경로는 **기록 당시의 경로**를 그대로 둔다.
> 2026-08-03 책임 영역 재편(`38274c0`) 이후의 현재 경로는 아래와 같이 대응한다.
>
> | 기록 당시 경로 | 현재 경로 |
> |---|---|
> | `firmware/esp_wroom32_mr60_monitor/` | `devices/mmwave/firmware/` |
> | `src/sensors/<device>/` | `devices/<device>/src/` |
> | `src/sensors/base_sensor.py` | `shared/contracts/base_sensor.py` |
> | `src/inference|risk|integrated_node|training|tools/` | `ondevice_ai/src/` 아래 동일 이름 |
> | `models/`, `datasets/`, `config/` | `ondevice_ai/` 아래 동일 이름 |
> | `tests/`, `tests/benchmarks/` | `ondevice_ai/tests/`, `ondevice_ai/benchmarks/` (mmWave 기기 단독 4종은 `devices/mmwave/tests/`) |
> | `hardware/3d_print/` | `hardware/3d_models/` |
> | `SafeNest_V4_OnDevice_AI/` | `ondevice_ai/` |
>
> 전체 매핑과 무결성 검증 근거는 [`docs/architecture/BRANCH_PROVENANCE.md`](docs/architecture/BRANCH_PROVENANCE.md)에 있다.

## 목표와 성공 기준

원본 브랜치와 바이너리 자산의 기여 이력을 보존하면서 기능 중심 저장소 구조로 통합하고, 모든 경로 및 테스트를 검증한 뒤 전용 브랜치에 재현 가능한 커밋을 남긴다.

## 복구 지점 (2026-08-02, Asia/Seoul)

- 작업 시작 HEAD: `codex/mmwave-phase-integration` / `b0d3c95ef9c890779909a0ccef35daf0db9185ae`
- fetch 전 로컬 `main`: `729c713b3c3d826a2e8444cb984994635c9a55f0`
- fetch 전 `origin/main`: `34ae6c53f8be4e7f3f8cc3f5efd9ba8551ac5521`
- fetch 후 통합 기준 `origin/main`: `01a4acb8c4b059fa15a38603f12a2b4682980362`
- `origin/Ondevice_AI`: `d97df3e5a0110daa7eb64e868919cedc2256133e`
- fetch 전 `origin/3D_Print`: `df2b12f93753da4b10541b15fe94176da171fe72`
- fetch 후 `origin/3D_Print`: `35c1e1f511e62c65fb39460a49bd89b620d86daf`
- 통합 브랜치: `refactor/integrated-v4-architecture` (기준 `origin/main`)

## 생활 체크리스트

- [x] Git 상태·브랜치·자산 1차 조사 — 작업 시작 시 추적 파일 변경 없음; 최신 ref와 분기 관계 확인.
- [x] 기존 작업 보호 및 fetch — 기존 mmWave 작업은 `b0d3c95`에서 복구 가능하며 fetch 성공.
- [x] 통합 브랜치 생성 — 최신 `origin/main`에서 전용 브랜치 생성.
- [x] 브랜치별 트리·참조 비교 및 이동 매핑 확정 — 아래 원본 선택과 결손을 확인.
- [x] 기능 중심 구조 통합 및 상위 디렉터리 README 작성 — 9개 최상위 디렉터리 모두 필수 11항목 확인; STL 4종, TFLite 3종, NPZ 2종 배치 확인.
- [x] 코드·설정·모델·문서 경로 전수 수정 — `src.*` import, 저장소 루트 기준 모델·데이터·설정 경로와 문서 실행 경로 적용.
- [x] 정적 검사와 Python 단위·통합 회귀 테스트 — 아래 검증 증거 모두 통과.
- [x] 루트 README 기여·커밋·PR 절차 추가 및 최종 감사 — 브랜치 규칙, 개인 커밋 순서, PR 정의·생성·검토 절차 추가; Markdown link 0건 오류.
- [x] 검증된 변경을 통합 브랜치에 커밋 — `372aa2af2ffe7f1e547a5cf99bc8bd2cc3a44855` 생성 및 tree/부모/메시지 확인.
- [x] 작업 브랜치 push 및 `main` 대상 draft PR 생성 — [PR #2](https://github.com/jinsu1011/safenest-embedded-competition/pull/2).

## 현재 상태와 결정

- 최신 `origin/main`은 팀원별 디렉터리로 병합되어 있어 최종 목표 구조가 아니다.
- 작업 시작 브랜치의 `firmware/`, `SafeNest_V4_OnDevice_AI/`, `pi/`는 브랜치 전환 뒤 미추적으로 보이지만 원본 커밋에 보존되어 있다.
- `tmp/`는 작업 범위 밖의 사용자 자료로 취급하며 열거나 이동·삭제하지 않는다.
- 1차 이동 명령은 `integrated_node/*`가 미추적 `__pycache__`까지 확장되어 중단됐다. 앞선 `sensors`, `adapters`, `inference`, `risk/*.py` 이동은 정상 반영됐고 파일 손실은 없다. 이후 이동은 추적 파일을 명시해 수행한다.
- 팀원별 사본 제거 전 tree diff를 검증했다. `jinsu1011`에서 최신 mmWave 끝점으로 삭제는 없고 134개 추가·16개 개선, `sheepmeat` 고유 2개는 최신 README/보관 JSON으로 승계, `yuname121`의 차이는 최신 CAD 4종으로 승계된다.

## 다음 단계

팀원별 디렉터리, 원격 브랜치 끝점, mmWave 통합 브랜치의 파일을 내용 해시와 참조 관계로 비교해 이동 표를 확정한다.

## 확정된 원본 선택 및 이동 표

| 기능 영역 | 채택 원본 | 최종 위치 | 판단 근거 |
|---|---|---|---|
| MCU 펌웨어·측정·분석 | `codex/mmwave-phase-integration` (`b0d3c95`)의 `firmware/` | `firmware/` | `origin/main:jinsu1011/firmware`보다 134개 파일의 추가/수정이 있음 |
| V4 AI 기본 구현 | `origin/Ondevice_AI` 계보 | `src/`, `models/`, `datasets/`, `config/`, `tests/` | V4 원저작 브랜치이며 74개 테스트를 포함 |
| MR60 AI 연동 보강 | `b0d3c95`의 `SafeNest_V4_OnDevice_AI/` | 위 기능별 디렉터리 | V4 이후 9개 연동 파일, 290줄 추가 및 테스트 보강 |
| Legacy 위험 엔진 | `b0d3c95:pi/` | `archive/legacy_prototypes/pi/` | 삭제하지 않고 비교 가능한 상태로 격리 |
| CAD 4종 | `origin/3D_Print` (`35c1e1f`) | `hardware/3d_print/` | 최신 브랜치 파일이며 현재 팀원별 사본과 blob이 다름 |
| 운용·연구 문서 | `b0d3c95`의 루트 문서 및 V4 문서 | `docs/` | 가장 최신 mmWave 운영 이력 포함 |

### 확인된 결손

- 전체 접근 가능한 Git 이력에서 기획 문서로 확인된 바이너리는 `safenest_mmwave_latest_development_direction_20260726.pdf` 1개이다.
- 프롬프트에 언급된 `.docx` 및 `index.html`은 로컬/원격 전체 ref와 현재 작업 트리(`tmp/` 제외)에 존재하지 않는다.
- 없는 자산은 생성하거나 대체하지 않으며, 추후 원본 제공 시 `docs/planning/`과 `docs/dashboard/`에 추가한다.

## 게시 진행 상태

- GitHub CLI 2.97.0 설치 완료.
- GitHub 계정 `jinsu1011` 인증 및 `repo`, `workflow` 권한 확인 완료.
- 작업 브랜치 `refactor/integrated-v4-architecture`, staged 605개, unstaged/untracked 0개 확인.
- 통합 커밋 `372aa2a` 생성 완료. 커밋 명령은 종료 시 SIGBUS(138)를 반환했으나, 새 HEAD·부모·커밋 tree와 clean working tree를 독립 확인해 커밋 성공으로 판정했다.
- 작업 브랜치 최초 push 및 upstream 설정 완료; force push나 `main` 직접 push는 수행하지 않았다.
- `main` 대상 draft PR #2 생성 완료: https://github.com/jinsu1011/safenest-embedded-competition/pull/2
- PR 원격 검증: `OPEN`/`DRAFT`, base=`main`, head=`refactor/integrated-v4-architecture` 확인.
- 게시 시점 로컬·원격·PR head가 `46d3aaa88ac725454fb6ae84ec9a2148edb50c91`로 일치하고 working tree가 clean임을 확인.
- 다음 단계: 팀 검토와 승인 후 PR을 Ready for review로 전환하고 필수 검사를 거쳐 `main`에 병합한다.

## 검증 기록

- 기본 `python3`(3.14)는 `numpy`/`pandas`가 없어 import 단계에서 실패했다. 시스템을 변경하지 않고 `/private/tmp/safenest-refactor-venv`를 만들고 프로젝트 범위 `tensorflow>=2.15,<2.20`(설치 2.19.1)을 사용했다.
- `/private/tmp/safenest-refactor-venv/bin/python -m unittest discover -s tests -p "test_*.py"`: **84 tests OK, skipped=2**.
- Python 소스 93개 `py_compile`: 통과 (`.pio`, `.venv`, cache 제외).
- JSON 전체 파싱 및 `config/*.yaml` 3개 파싱: 통과.
- `src.tools.build_v4_archive.archive_inputs()`: 46개 입력, missing 0.
- `pio run`: 성공, RAM 9.9%(32,356/327,680), Flash 20.5%(268,765/1,310,720).
- Markdown 19개 상대 링크 검사: broken link 0.
- 원본 blob 보존: TFLite 3종·NPZ 2종이 `origin/Ondevice_AI`, STL 4종이 `origin/3D_Print`과 모두 일치.
- 설정 단일화: 활성 `config/risk_rules.json` 0개, 공식 `config/risk_rules.yaml` 존재. root/V4 legacy JSON은 SHA-256 `86a0e24…b51bd3`으로 동일함을 확인해 archive에 `legacy_risk_rules.json` 한 사본으로 보존.
- 충돌 파일 0개, 텍스트 대상 `git diff --check` 통과.

## 기기·주제별 2차 정리 (2026-08-02)

- [x] 추적 파일과 작업 트리의 사용자명 디렉터리 조사 — `jinsu1011/`, `sheepmeat/`, `yuname121/` 경로 0개 확인.
- [x] 남은 구형 로컬 폴더 내용 감사 — `SafeNest_V4_OnDevice_AI/`, `pi/`는 Python 캐시만, `thermal/`은 빈 폴더임을 확인하고 제거.
- [x] 일반 `src/sensors/adapters/` 분류 검토 — 포함된 4개 모듈이 모두 mmWave/MR60 전용임을 확인해 `src/sensors/mmwave/`로 이동.
- [x] 코드·테스트·도구·문서의 이전 adapter 경로 치환 — `src.sensors.adapters`와 `src/sensors/adapters` 잔존 참조 0개.
- [x] 정적 검사와 Python 회귀 테스트 완료 — 84 tests OK(skipped=2), 현재 Python 파일 컴파일 통과, Markdown 33개 링크 0건 오류, archive 입력 46개 missing 0.
- [x] 변경 커밋·push 및 draft PR #2 head 검증 — `ac8f95e85a2a1995c62be4b2fa4b51cf48808bc2`, 로컬·원격·PR head 일치.

향후 센서 전용 코드는 `src/sensors/<device>/`, 공용 추론·위험도·통합 코드는 각 기능 주제 패키지에 배치하며 사용자명 디렉터리를 만들지 않는다.
