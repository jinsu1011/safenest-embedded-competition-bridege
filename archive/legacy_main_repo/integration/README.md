# `integration/`

## 1. 디렉터리 목적
ESP32 텔레메트리를 받아 상태를 판정하고 LCD·부저·웹 화면으로 내보내는 Raspberry Pi 쪽 실행 계층을 한곳에 모은다.

## 2. 시스템에서 담당하는 기능
TCP 9000으로 들어온 센서 패킷을 검증·보관하고, 상태를 판정해 LCD 키오스크 화면과 GPIO 부저를 구동하며, 관리자·방문자 웹 화면과 REST API를 제공한다.

## 3. 포함해야 하는 파일 유형
Pi 수신·표시 서버, 웹 서버와 정적 화면, 실행·설치 스크립트, 이 계층만으로 통과 가능한 테스트를 포함한다.

## 4. 포함하면 안 되는 파일 유형
ESP32 펌웨어(`devices/esp32_node/`), 센서별 드라이버(`devices/<sensor>/`), TFLite 모델·추론(`ondevice_ai/`), 공용 계약(`shared/contracts/`), `node_modules/`와 `.env` 같은 로컬 산출물은 포함하지 않는다.

## 5. 주요 하위 구성
`pi_lcd/`는 Python 표준 라이브러리 기반 수신·표시 서버(`server.py`, `static/`, `tests/`, `start_lcd.sh`, `stop_lcd.sh`)다. `web/`은 Express 기반 통합 웹(`server.js`, `admin-api.js`, `preview.html`, `qr-codes/`)이다. `install_raspberry_pi.sh`와 `start_all.sh`는 두 서버를 설치·기동한다.

## 6. 입력과 출력 인터페이스
입력은 ESP32의 `safenest.telemetry.v1` JSON(TCP 9000)이다. 출력은 `GET /api/state`, `GET /api/thermal`, `GET /health`(:8080)와 통합 웹(:3000), 그리고 LCD 화면·부저다. `POST /api/state`로 판정 결과가 LCD에 반영된다. 결측·0·NaN·timeout은 정상값이나 무호흡으로 바꾸지 않고 `stale`/`waiting`으로 표시한다.

## 7. 다른 기능 영역과의 관계
`devices/esp32_node/`가 보내는 텔레메트리를 소비하는 하위 계층이며, 반대로 펌웨어를 import하지 않는다. 현재 판정은 `web/server.js`의 규칙 기반 `evaluate()`/`riskScore()`를 쓰며, `ondevice_ai/`의 V4 위험도 엔진과는 아직 연결돼 있지 않다. 두 판정 경로의 통합은 후속 작업이다.

## 8. 실행·학습·추론 또는 활용 방법
설치와 실행은 저장소 루트에서 수행한다.

```bash
bash integration/install_raspberry_pi.sh
bash integration/start_all.sh
```

스크립트는 `pi_lcd/`와 `web/`을 각각 `~/raspberry_pi_lcd`와 `~/SafeNest_Web`으로 복사한다. 저장소 경로와 실행 환경 폴더 이름이 다른 것은 실측 검증된 운용 절차를 그대로 유지하기 위해서다. 자세한 절차는 [`docs/operations/INTEGRATION_INSTALL_AND_RUN.md`](../docs/operations/INTEGRATION_INSTALL_AND_RUN.md)에 있다.

테스트는 `pi_lcd/`에서 실행한다. 테스트가 `server.py`를 직접 import하므로 해당 디렉터리를 `PYTHONPATH`에 넣는다.

```bash
cd integration/pi_lcd
PYTHONPATH=. python3 -m unittest discover -s tests -p "test_*.py"
```

## 9. 현재 개발 상태 및 버전
실제 하드웨어에서 ESP32 수신 → 상태 판정 → LCD 자동 전환까지 검증했고 회귀 테스트 13건이 통과한다. 남은 한계(열화상 죽은 픽셀, 호흡수 노이즈)는 [`docs/esp32_node/ESP32_LCD_INTEGRATION_NOTES.md`](../docs/esp32_node/ESP32_LCD_INTEGRATION_NOTES.md) 5절에 있다. 최상위 `display-test/`와 `display-test2/`는 이 작업의 이전 스냅샷이며 이 디렉터리가 대체한다.

## 10. 향후 파일 추가 및 관리 규칙
판정 규칙과 임계값은 한 번에 하나만 바꾸고 같은 조건에서 변경 전후를 비교한다. 텔레메트리 필드를 바꾸면 `devices/esp32_node/`와 [`docs/esp32_node/COMMUNICATION_PROTOCOL.md`](../docs/esp32_node/COMMUNICATION_PROTOCOL.md)를 같은 PR에서 함께 고친다. `.env`와 `secrets.h`, `node_modules/`는 커밋하지 않는다.

## 11. 주요 기여자와 원본 브랜치·커밋 추적 정보
담당: Seungha (`@yuseungha`) — Pi 수신·표시 서버, 통합 웹, 설치·실행 스크립트.
원본 ref `yuseungha/safenest-embedded-competition@0992a6d`(`main`에 PR #1로 병합), 원본 경로 `yuseungha/raspberry_pi_lcd/`와 `yuseungha/SafeNest_Web/`.
