# `devices/pir/`

## 1. 디렉터리 목적
PIR 동작 감지 센서의 드라이버, 어댑터, 배선 자료와 기기 단독 테스트를 담당자가 한곳에서 관리한다.

## 2. 시스템에서 담당하는 기능
GPIO 기반 동작 감지 이벤트를 읽어 `SensorReading` 계약에 맞춘 이진 신호로 제공하고, mmWave 재실 판정을 보조한다.

## 3. 포함해야 하는 파일 유형
PIR 드라이버·어댑터·mock, GPIO 핀맵과 배선 문서, PIR만으로 통과 가능한 테스트를 포함한다.

## 4. 포함하면 안 되는 파일 유형
위험도 융합 로직(`ondevice_ai/src/risk/`), 공용 인터페이스(`shared/contracts/`), 하우징 CAD(`hardware/3d_models/`), 다른 기기 코드는 포함하지 않는다.

## 5. 주요 하위 구성
`src/pir_adapter.py`(실기기 어댑터), `src/mock_sensor.py`(하드웨어 없는 대체 구현)로 구성된다. 배선 문서와 기기 테스트는 아직 없다.

## 6. 입력과 출력 인터페이스
입력은 PIR 모듈의 GPIO 디지털 신호이며, 출력은 동작 감지 여부와 `SensorState` 기반 결측·미연결 상태다.

## 7. 다른 기능 영역과의 관계
`shared/contracts/base_sensor.py`를 구현하고, `ondevice_ai/src/risk/`의 융합 규칙이 이 신호를 mmWave 재실 판정의 보조 근거로 사용한다. 하우징 배치는 `hardware/3d_models/`와 일치해야 한다.

## 8. 실행·학습·추론 또는 활용 방법
하드웨어 없이 확인할 때는 `src/mock_sensor.py`를 사용하고, 통합 동작은 `ondevice_ai/tests/test_sensor_adapters.py`가 검증한다.

## 9. 현재 개발 상태 및 버전
어댑터와 mock 단계다. PIR 전용 모델은 없으며 규칙 기반으로만 융합에 참여한다.

## 10. 향후 파일 추가 및 관리 규칙
실기기 연결 시 `docs/`에 GPIO 핀맵과 설치 각도·감도 기준을, `tests/`에 기기 단독 테스트를 추가한다. 감도·홀드타임 변경은 오탐 측정 근거와 함께 커밋한다.

## 11. 주요 기여자와 원본 브랜치·커밋 추적 정보
담당: Yuna (`@yuname121`) — PIR, 하우징, UX.
원본 ref `origin/Ondevice_AI` (`d97df3e`), 원본 경로 `src/sensors/pir/`. 2026-08-03 이동 커밋 `38274c0`에서 현재 경로로 옮겼다.
