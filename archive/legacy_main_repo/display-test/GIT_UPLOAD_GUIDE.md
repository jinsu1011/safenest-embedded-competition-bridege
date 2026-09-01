# SafeNest LCD·피에조 부저 Git 업로드 자료

작성 기준일: 2026-08-01

## 1. 업로드 범위

다음 파일을 저장소에 포함합니다.

```text
safenest_lcd_remote/
├─ server.py                    # 상태 API, 상태 저장, 부저 제어
├─ start_lcd.sh                 # 서버와 Chromium 키오스크 시작
├─ stop_lcd.sh                  # 브라우저·서버 종료
├─ deploy_buzzer.sh             # 부저 자동 검증(실제로 2초간 소리 남)
├─ test_buzzer.py               # GPIO 모의 객체 기반 회귀 테스트
├─ static/
│  ├─ display.html              # Raspberry Pi LCD 화면
│  ├─ control.html              # 노트북 원격 제어 화면
│  └─ common.css                # 공통 상태별 스타일
├─ LCD_BUZZER_TEAM_GUIDE.html   # 팀원용 통합 실행 문서
├─ README.md                    # 빠른 시작 안내
├─ state.example.json           # 런타임 상태 파일 예시
├─ .gitignore                   # 로그·PID·실행 상태 제외
└─ .gitattributes               # Windows/Linux 줄바꿈 통일
```

다음 항목은 실행 중 자동 생성되므로 업로드하지 않습니다.

- `state.json`, `state.json.tmp`
- `logs/`
- `.server.pid`, `.browser.pid`
- `.chromium-kiosk/`
- `__pycache__/`, `*.pyc`

## 2. 업로드 전 검증 결과

문서 작성 PC에서 확인한 결과입니다. Raspberry Pi 실물 확인 항목은 업로드 전에 담당자가 체크합니다.

- [x] `python -m unittest -v test_buzzer.py` — 2개 테스트 통과
- [x] `python -m py_compile server.py test_buzzer.py` — Python 문법 통과
- [x] `bash -n start_lcd.sh stop_lcd.sh deploy_buzzer.sh` — 셸 문법 통과
- [x] `--disable-buzzer` 로컬 스모크 테스트 — `/health`, `/display`, `/control` 응답 확인
- [ ] Raspberry Pi LCD에서 키오스크 전체화면 표시 확인
- [ ] `/health`에서 `available: true`, GPIO18, 880 Hz 확인
- [ ] 현장 고지 후 `deploy_buzzer.sh`로 긴급 ON 2초 → OFF 확인
- [ ] 종료 후 실제 부저가 꺼지고 프로세스가 정리되는지 확인

중요: 현재 화면의 CO₂·온도·움직임 값은 수동 시연용 예시값입니다. 실제 센서 데이터 연동 완료로 표시하면 안 됩니다.

## 3. 새 GitHub 저장소에 올리는 명령

아래 명령은 `safenest_lcd_remote` 폴더 안에서 실행합니다. `<조직또는계정>`과 `<저장소명>`은 실제 값으로 바꿉니다.

```powershell
git init
git branch -M main
git add .
git update-index --chmod=+x start_lcd.sh stop_lcd.sh deploy_buzzer.sh
git status --short
git diff --cached --check
git commit -m "feat: add SafeNest LCD control and emergency buzzer"
git remote add origin https://github.com/<조직또는계정>/<저장소명>.git
git push -u origin main
```

`git status --short`에서 `state.json`, `logs`, PID 파일, Chromium 프로필이 보이면 커밋하지 말고 `.gitignore` 적용 여부를 먼저 확인합니다.

## 4. 기존 저장소에 추가하는 명령

기존 저장소를 먼저 최신 상태로 받은 뒤, 저장소 안의 적절한 위치에 이 폴더를 복사합니다. 원격 이력을 덮어쓰는 `--force`는 사용하지 않습니다.

```powershell
git pull --ff-only
git switch -c feat/safenest-lcd-buzzer
git add safenest_lcd_remote
git update-index --chmod=+x safenest_lcd_remote/start_lcd.sh safenest_lcd_remote/stop_lcd.sh safenest_lcd_remote/deploy_buzzer.sh
git status --short
git diff --cached --check
git commit -m "feat: add SafeNest LCD control and emergency buzzer"
git push -u origin feat/safenest-lcd-buzzer
```

## 5. 커밋·PR 문구

커밋 제목:

```text
feat: add SafeNest LCD control and emergency buzzer
```

PR 제목:

```text
feat: Raspberry Pi LCD 원격 제어 및 긴급 피에조 경보 추가
```

PR 본문 초안:

```markdown
## 작업 내용

- Raspberry Pi LCD용 6단계 상태 화면과 노트북 원격 제어 화면 추가
- `/api/state` 기반 상태 변경 및 `state.json` 런타임 저장 구현
- `emergency` 상태에서만 BCM GPIO18 수동 피에조 부저를 880 Hz로 구동
- 시작·종료·부저 검증 스크립트와 팀원용 HTML 실행 가이드 추가

## 상태 흐름

노트북 `/control` → `POST /api/state` → 상태 저장 → LCD `/display` 동기화 → 긴급 상태일 때 부저 ON

## 검증

- [x] Python 단위 테스트 2개 통과
- [x] Python 및 셸 스크립트 문법 검사 통과
- [x] 부저 비활성 로컬 서버에서 주요 HTTP 경로 응답 확인
- [ ] Raspberry Pi LCD 키오스크 표시 확인
- [ ] 실물 GPIO18 부저 ON/OFF 확인

## 주의 사항

- 현재 센서 수치는 실제 센서 입력이 아닌 시연용 예시값입니다.
- `deploy_buzzer.sh`는 실제로 약 2초간 경보음을 냅니다.
- 실행 종료 시 `stop_lcd.sh`로 서버와 LCD 브라우저를 함께 종료합니다.
```
