# `devices/`

## 1. 디렉터리 목적
기기 담당자가 단독으로 책임지는 센서별 펌웨어, 드라이버, 배선·보정 문서, 기기 단독 테스트를 기기 단위로 모은다.

## 2. 시스템에서 담당하는 기능
각 물리 센서를 초기화·수집·검증해 `shared/contracts/base_sensor.py` 계약을 만족하는 정규화된 판독값으로 바꾼다.

## 3. 포함해야 하는 파일 유형
기기별 드라이버·어댑터·mock, 펌웨어 프로젝트, 기기 설정, 배선·보정 문서, 그 기기만으로 통과 가능한 테스트를 포함한다.

## 4. 포함하면 안 되는 파일 유형
여러 기기가 함께 쓰는 인터페이스(`shared/contracts/`), TFLite 추론·위험도 융합·통합 노드(`ondevice_ai/`), 빌드 산출물과 사용자명 디렉터리는 포함하지 않는다.

## 5. 주요 하위 구성
`co2/`, `pir/`, `mmwave/`, `thermal/` 네 기기가 있고 각 기기는 `src/`를 기본으로 필요에 따라 `firmware/`, `config/`, `tests/`, `docs/`를 갖는다.

## 6. 입력과 출력 인터페이스
입력은 UART/I2C/GPIO 원신호와 리플레이 로그이며, 출력은 `SensorReading` 계약을 따르는 판독값과 명시적인 결측 표시다.

## 7. 다른 기능 영역과의 관계
`shared/contracts/`의 계약을 구현하고, `ondevice_ai/src/`가 이 구현을 `devices.<device>.src...` 경로로 명시적으로 import한다. 반대 방향 의존은 만들지 않는다.

## 8. 실행·학습·추론 또는 활용 방법
기기 단독 테스트는 `python3 -m unittest discover -s devices/<device>/tests -p 'test_*.py'`로 실행하고, 펌웨어는 해당 기기 README의 빌드 절차를 따른다.

## 9. 현재 개발 상태 및 버전
mmWave는 MR60 schema 1.2 / 펌웨어 v1.2.0으로 실측 검증까지 완료했고, CO2·PIR·Thermal은 어댑터와 mock 단계다. 2026-08-03 책임 영역 재편(`38274c0`) 구조를 따른다.

## 10. 향후 파일 추가 및 관리 규칙
새 기기는 `devices/<device>/src/`부터 만들고 담당자·README·CODEOWNERS 항목을 함께 추가한다. 기기 코드를 다른 기기 디렉터리로 복사하지 말고, 공통이 필요해지면 `shared/contracts/`로 올린 뒤 양쪽에서 import한다.

## 11. 주요 기여자와 원본 브랜치·커밋 추적 정보
| 기기 | 담당 | GitHub handle | 책임 범위 |
|---|---|---|---|
| `co2/` | Seungha | `@yuseungha` | CO2 센서 드라이버, 배선, 보정 |
| `pir/` | Yuna | `@yuname121` | PIR 어댑터, 하우징 연계 |
| `mmwave/` | Jinsu | `@jinsu1011` | MR60 펌웨어, 텔레메트리, 실측 검증 |
| `thermal/` | Taegyun | `@rla1729` | Thermal-44 드라이버, 프레임 파서 |

원본은 `origin/Ondevice_AI`(`d97df3e`)의 센서 구현과 `codex/mmwave-phase-integration`(`b0d3c95`)의 MR60 작업이며, 상세 매핑은 [`docs/architecture/BRANCH_PROVENANCE.md`](../docs/architecture/BRANCH_PROVENANCE.md)에 있다.
