# SafeNest 비상 대응 HMI 작업 진행 기록

## 목표

ZIP의 기존 `safenest_integration` 통합 경계를 유지하면서 Raspberry Pi 터치 대시보드에 DANGER 전이 기반 비상 HMI, 모의 119 신고, 담당자 SMS, 음성·부저, 경고 승인, 오프라인 표시, 이벤트 로그를 추가하고 자동 검증으로 동작을 확인한다.

## 현재 상태

- [x] 첨부 요청 전문을 읽고 요구사항을 정리했다.
- [x] 현재 workspace와 Git 상태를 확인했다. 센서 검증 관련 미커밋 변경은 보존한다.
- [x] `safenest_integration_package.zip`을 읽고 기존 통합 구조와 실행 문서를 확인했다.
- [x] 기존 흐름을 확인했다: TCP receiver → SensorStateManager → AI/Risk Engine → RuntimeStore/SQLite → FastAPI/WebSocket → dashboard.
- [x] 구현 기준을 결정했다: ZIP의 기존 통합 번들을 workspace에 반영하고 그 경계 안에서 비상 기능을 확장한다.
- [x] ZIP 통합 번들을 workspace에 반영했다.
- [x] 기준 테스트를 실행했다: 110개 중 순수 로직·DB·정적 대시보드는 대부분 통과했으나, `numpy/FastAPI/uvicorn/scipy` 미설치와 sandbox loopback bind 차단으로 선택적 AI/E2E 테스트가 실패했다.
- [x] 변경 범위를 확정했다: RuntimeStore 전이·alarm latch, backend action/service, GPIO/mock buzzer, SMS provider abstraction, browser emergency HMI, SQLite emergency state, 테스트·문서.
- [x] 비상 기능을 구현한다: RuntimeStore DANGER latch, GPIO/mock buzzer, server-side SMS, 119 simulation, action API, SQLite state, dashboard HMI/offline fallback.
- [x] 자동·정적 검증을 수행한다: 긴급 회귀 5건 포함 focused suite 32건 PASS, Python compileall, Node syntax, diff check.
- [x] 운영 문서를 추가·갱신한다: `.env.example`, 긴급 HMI 운영 가이드, README와 package guide 링크/운영 주의사항.
- [x] 전체 회귀 테스트와 최종 변경 범위 감사를 완료한다.
- [x] 다른 사람이 원본 패키지 위에 적용할 수 있도록 변경사항 전용 ZIP과 한국어 통합 가이드를 만들고 압축 해제 검증을 완료했다.

## 주요 결정과 이유

1. 위험 판정은 `safenest_integration/risk/engine.py`에 계속 둔다. 프론트엔드에서 위험 점수를 재계산하지 않는다.
2. 119는 외부 전화·VoIP·API를 절대 호출하지 않는 명시적 시뮬레이션으로 구현한다.
3. SMS는 브라우저에서 provider를 호출하지 않고 백엔드 서비스 계층에서만 처리한다. 담당자 번호는 서버 환경변수로만 결정한다.
4. SMS 중복 방지는 프론트엔드 잠금과 백엔드 cooldown/idempotency를 함께 둔다.
5. GPIO, 오디오 파일, SMS provider가 없는 개발 환경에서도 서버와 UI가 유지되도록 mock/fallback을 둔다.

## 변경 예정 범위

- `safenest_integration/backend/`: emergency action API 및 상태 연계
- `safenest_integration/services/`: SMS, GPIO buzzer, local audio 추상화
- `safenest_integration/database/`: 비상 이벤트 영속화
- `safenest_integration/web/dashboard/`: 터치용 비상 overlay/modal/버튼 및 오프라인 UI
- `safenest_integration/tests/`: 전이·중복·시뮬레이션·오프라인·fallback 회귀 테스트
- `safenest_integration/docs/` 및 실행 문서: Pi, 환경변수, 시연 절차

## 기준선 실행 결과

- 명령: `python3 -m unittest discover -s safenest_integration/tests -p 'test_*.py' -v`
- 결과: `Ran 110 tests`, `FAILED (failures=3, errors=12)`.
- 환경성 실패: loopback TCP socket bind 차단, `numpy/FastAPI/uvicorn/scipy` 미설치.
- 구현성 참고: 기존 AI 테스트 중 Thermal failure metadata 경계 1건과 gateway risk pipeline 1건도 별도로 확인했으며, 비상 기능 변경과 분리해 최종 회귀에서 재판정한다.

## 현재 구현·검증 결과

- `safenest_integration/services/{buzzer,sms_service,emergency}.py`를 추가했다.
- `backend/store.py`, `database/{repository,store,schema.sql}.py`, `backend/{views,app}.py`를 DANGER latch와 action API에 맞게 확장했다.
- `web/dashboard/{index.html,app.js,styles.css}`에 DANGER 전용 touch HMI, 모의 119 modal/countdown, SMS/acknowledge/voice 동작, offline/polling 상태를 연결했다.
- 추가 테스트 `tests/test_emergency_actions.py`를 포함한 focused command는 `Ran 32 tests ... OK`였고, SMS 서명 계약 추가 후에는 17건이 `OK`였다.
- 처음 기본 Python에서 확인된 실패는 workspace `.venv`에 `numpy/scipy/FastAPI/uvicorn`을 설치한 뒤 loopback 허용 환경에서 재검증했다.
- 최종 전체 회귀는 `Ran 117 tests in 1.684s`와 `OK`였다.
- 최종 정적 검증도 `compileall`, `node --check`, `bash -n`, `git diff --check`, 시크릿 패턴 감사를 통과했다. `.venv`는 기존 ignore 규칙으로 추적되지 않는다.
- 변경 ZIP은 `safenest_emergency_changes_20260813.zip`이며 25개 파일을 포함한다. `unzip -t`와 임시 디렉터리 압축 해제·내용 비교가 모두 통과했다.

## 다음 단계

최종 보고서에서 기존 통합 구조, 변경 파일, 긴급 동작 흐름, 실행·환경변수, 117건 테스트 결과, 실제 Pi/SMS/GPIO 확인 범위를 사용자에게 전달한다.
