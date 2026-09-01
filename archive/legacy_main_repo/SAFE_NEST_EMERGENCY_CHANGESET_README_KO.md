# SafeNest 긴급 대응 변경사항 통합 패키지

이 문서는 `safenest_integration_package.zip`에 추가 적용할 긴급 대응 기능 변경사항을 설명한다.

## 패키지 성격

- 이 ZIP은 원본 SafeNest 전체 패키지가 아니라 **긴급 대응 변경 파일 전용 패키지**다.
- 원본 기준 패키지인 `safenest_integration_package.zip`을 먼저 해제한 뒤 이 ZIP을 같은 위치에 해제한다.
- 압축 해제 시 `safenest_integration/` 아래의 같은 경로 파일을 덮어쓰면 된다.
- 실제 SMS credential, `.env`, SQLite 운영 DB, `.venv`, Python cache, 로그는 포함하지 않는다.
- 119 기능은 실제 긴급 서비스와 연결되지 않는 경진대회 시연용 시뮬레이션이다.

## 적용 방법

원본 ZIP과 변경 ZIP을 같은 디렉터리에 둔 경우:

```bash
unzip safenest_integration_package.zip
unzip safenest_emergency_changes_20260813.zip
```

Windows에서는 두 ZIP을 같은 폴더에 순서대로 해제하고, 두 번째 압축 해제에서 기존 파일 덮어쓰기를 허용한다. 대상 프로젝트의 `safenest_integration/`가 이미 존재하면 변경 ZIP의 파일을 해당 상대경로에 복사한다.

## 새로 추가된 파일

- `safenest_integration/services/__init__.py`
- `safenest_integration/services/buzzer.py`
- `safenest_integration/services/emergency.py`
- `safenest_integration/services/sms_service.py`
- `safenest_integration/.env.example`
- `safenest_integration/web/dashboard/audio/README.md`
- `safenest_integration/docs/EMERGENCY_HMI_AND_OPERATIONS_KO.md`
- `safenest_integration/tests/test_emergency_actions.py`

## 기존 파일 변경 목록

- `safenest_integration/backend/app.py`
- `safenest_integration/backend/store.py`
- `safenest_integration/backend/views.py`
- `safenest_integration/database/repository.py`
- `safenest_integration/database/store.py`
- `safenest_integration/database/schema.sql`
- `safenest_integration/deployment/run_pi.sh`
- `safenest_integration/web/dashboard/index.html`
- `safenest_integration/web/dashboard/app.js`
- `safenest_integration/web/dashboard/styles.css`
- `safenest_integration/README.md`
- `safenest_integration/PACKAGE_AND_OPERATION_GUIDE.md`
- `safenest_integration/tests/test_backend.py`
- `safenest_integration/tests/test_database.py`
- `safenest_integration/tests/test_dashboard.py`

## 통합 시 확인할 핵심 사항

1. `RuntimeStore`가 Risk Engine의 `DANGER` 전환 시 alarm latch와 `transition_id`를 생성하는지 확인한다.
2. 반복 DANGER publication은 같은 전환으로 처리되고, 음성·buzzer·overlay가 중복 실행되지 않는지 확인한다.
3. `경고 확인`은 buzzer만 끄고 Risk Engine 위험 단계는 변경하지 않아야 한다.
4. 실제 live `WARNING/NORMAL` publication이 오기 전에는 offline 또는 stale 상태만으로 DANGER가 해제되지 않아야 한다.
5. SQLite schema version은 2이며, 기존 schema version 1 DB는 emergency column을 추가해 자동 보정한다.
6. SMS는 브라우저에서 호출하지 않고 backend의 Naver Cloud SENS provider가 호출한다.
7. SMS 수신번호는 `MANAGER_PHONE_NUMBER` 환경변수만 사용하며 브라우저에는 마스킹된 값만 전달한다.
8. `SAFENEST_GPIO_MODE=mock`이면 Raspberry Pi가 아닌 개발 PC에서도 서버가 실행되어야 한다.

## 환경변수

`safenest_integration/.env.example`을 복사해 `.env`를 만들고 실제 운영 환경에 맞게 설정한다.

```text
SMS_ACCESS_KEY=
SMS_SECRET_KEY=
SMS_SERVICE_ID=
SMS_FROM_NUMBER=
MANAGER_PHONE_NUMBER=
MANAGER_NAME=안전 담당자
SMS_API_BASE_URL=https://sens.apigw.ntruss.com
SMS_TIMEOUT_SECONDS=8
SAFENEST_SMS_COOLDOWN_SECONDS=60
SAFENEST_GPIO_MODE=auto
SAFENEST_BUZZER_GPIO_PIN=18
SAFENEST_BUZZER_FREQUENCY_HZ=880
```

`.env`는 커밋하거나 전달 ZIP에 넣지 않는다. SMS credential이 비어 있으면 SMS는 성공으로 처리되지 않고 `SMS_NOT_CONFIGURED` 오류를 반환한다.

## 검증 명령

저장소 루트에서 실행한다.

```bash
python3 -m unittest discover -s safenest_integration/tests -p 'test_*.py' -v
node --check safenest_integration/web/dashboard/app.js
bash -n safenest_integration/deployment/run_pi.sh
```

변경 패키지 작성 시점의 검증 결과:

```text
Ran 117 tests in 1.684s
OK
```

실제 Raspberry Pi GPIO, Chromium 터치, MP3 autoplay, 외부 SMS 발송은 해당 장비와 계정에서 별도로 확인해야 한다.

## 실행 문서

상세 실행·시연 절차는 다음 문서를 참고한다.

- `safenest_integration/docs/EMERGENCY_HMI_AND_OPERATIONS_KO.md`
- `safenest_integration/PACKAGE_AND_OPERATION_GUIDE.md`

