# Contributing

## 어디에 커밋하는가

파일 종류가 아니라 **기기와 책임 영역**을 기준으로 둡니다. 사람 이름 폴더는 만들지 않습니다.

| 무엇을 | 어디에 |
|---|---|
| 센서 펌웨어·드라이버·어댑터·기기 설정·기기 단독 테스트 | `devices/<sensor>/` |
| 여러 센서를 한 보드에서 수집하는 노드 펌웨어 | `devices/<board>/` |
| 인수인계, 센서별 읽을 문서, 튜닝·검증 보고서 | `docs/<sensor>/` |
| 공통 운용·구조·기획 문서 | `docs/operations|architecture|planning/` |
| 온디바이스 AI 모델·추론·위험도·통합 노드 | `ondevice_ai/` |
| Pi 수신·표시·부저·통합 웹 실행 계층 | `integration/` |
| 여러 영역이 함께 쓰는 센서 계약 | `shared/contracts/` |
| 3D 프린팅 CAD/STL | `hardware/3d_models/` |

즉 **코드는 `devices/<sensor>/`, 읽을 문서는 `docs/<sensor>/`** 로 나눕니다. 원본 로그와 분석 산출물은 문서가 아니므로 `devices/<sensor>/` 아래에 둡니다.

한 보드가 여러 센서를 수집하면 센서별로 쪼개지 말고 보드 이름의 기기 디렉터리(`devices/esp32_node/`)에 둡니다. 그 텔레메트리를 받아 화면·부저·웹으로 내보내는 Pi 쪽 실행 계층은 `integration/`에 둡니다. `ondevice_ai/`는 TFLite 추론과 V4 위험도 융합을, `integration/`은 실행·표시·경보를 담당합니다.

새 센서 문서 디렉터리나 새 최상위 책임 영역을 만들면 `.github/CODEOWNERS`에 담당자 한 줄과 루트 `README.md`의 구조 표를 같이 갱신합니다.

## Branches

- `main`: 실행·검증된 통합 상태
- 기능 브랜치: `feature/<sensor-or-feature>`
- 수정 브랜치: `fix/<issue>`
- 실험 브랜치: `experiment/<topic>`
- 문서 브랜치: `docs/<topic>`

`main`에 direct push하지 않습니다. Pull Request로만 반영하며, 병합은 팀 확인 후 진행합니다.

## Pull requests

PR에는 다음을 포함합니다.

1. 변경 목적과 담당 센서
2. 변경한 필터 또는 임계값 하나
3. 사용한 원본 로그 경로와 SHA-256
4. 변경 전후 지표
5. 실행한 테스트와 결과
6. 남은 위험과 롤백 방법

## Sensor data

- 원본 로그는 수정·덮어쓰기하지 않습니다.
- 새 로그는 날짜·조건·거리·시험 종류가 드러나는 이름을 사용합니다.
- 실패한 실험도 삭제하지 않고 원인과 다음 방법을 기록합니다.
- 개인정보와 불필요한 영상·음성은 커밋하지 않습니다.

## Safety

- MR60 펌웨어는 승인 없이 업데이트하지 않습니다.
- 0/null/NaN/timeout을 정상값이나 무호흡으로 변환하지 않습니다.
- 최종 위험 판정은 Raspberry Pi에서 수행합니다.
- 위험한 숨참기, 과호흡, 밀폐공간, 가스 주입 시험을 금지합니다.

