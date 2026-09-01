# `devices/co2/`

## 1. 디렉터리 목적
CO2 센서의 드라이버, 어댑터, 배선·보정 자료와 기기 단독 테스트를 담당자가 한곳에서 관리한다.

## 2. 시스템에서 담당하는 기능
CO2 농도(ppm)를 읽어 유효성을 판정하고 `SensorReading` 계약에 맞춰 밀폐공간 위험 판정의 입력으로 넘긴다.

## 3. 포함해야 하는 파일 유형
CO2 드라이버·어댑터·mock, 센서 설정, 배선도와 보정 절차 문서, CO2만으로 통과 가능한 테스트를 포함한다.

## 4. 포함하면 안 되는 파일 유형
CO2 TFLite 모델·데이터셋·추론 코드(`ondevice_ai/`), 공용 인터페이스(`shared/contracts/`), 다른 기기 코드는 포함하지 않는다.

## 5. 주요 하위 구성
`src/co2_adapter.py`(실기기 어댑터), `src/mock_sensor.py`(하드웨어 없는 대체 구현)로 구성된다. 배선·보정 문서와 기기 테스트는 아직 없다.

## 6. 입력과 출력 인터페이스
입력은 CO2 센서 원판독값이며, 출력은 ppm 값과 `SensorState`로 표현한 결측·범위이탈 상태다. 결측을 0이나 정상값으로 바꾸지 않는다.

## 7. 다른 기능 영역과의 관계
`shared/contracts/base_sensor.py`를 구현하고, `ondevice_ai/src/inference/co2_interpreter.py`와 위험도 엔진이 이 어댑터의 출력을 소비한다.

## 8. 실행·학습·추론 또는 활용 방법
하드웨어 없이 확인할 때는 `src/mock_sensor.py`를 사용하고, 통합 동작은 `ondevice_ai/tests/test_sensor_adapters.py`가 검증한다.

## 9. 현재 개발 상태 및 버전
어댑터와 mock 단계다. 실기기 연결·보정과 기기 단독 테스트는 미완이며, CO2 INT8 모델(`ondevice_ai/models/co2/co2_occupancy_int8_v0.1.0.tflite`)은 별도로 존재한다.

## 10. 향후 파일 추가 및 관리 규칙
실기기 연결 시 `docs/`에 배선도와 보정 절차를, `tests/`에 기기 단독 테스트를 추가한다. 보정값 변경은 근거 측정 데이터와 함께 커밋한다.

## 11. 주요 기여자와 원본 브랜치·커밋 추적 정보
담당: Seungha (`@yuseungha`) — CO2 센서, 배선, 보정.
원본 ref `origin/Ondevice_AI` (`d97df3e`), 원본 경로 `src/sensors/co2/`. 2026-08-03 이동 커밋 `38274c0`에서 현재 경로로 옮겼다.
