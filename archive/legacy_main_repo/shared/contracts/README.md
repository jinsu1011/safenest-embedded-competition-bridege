# `shared/contracts/`

## 1. 디렉터리 목적
기기 구현과 온디바이스 AI가 공유하는 센서 데이터 계약과 상태 정의를 보관한다.

## 2. 시스템에서 담당하는 기능
센서 판독의 형태, 건강 상태(`SensorHealth`), 오류 상태(`SensorState`) 전이 규칙을 정의해 결측·타임아웃·범위이탈이 정상값으로 둔갑하지 않도록 강제한다.

## 3. 포함해야 하는 파일 유형
추상 기반 클래스, dataclass 계약, 상태 enum과 그 계약의 불변식을 검증하는 정의만 포함한다.

## 4. 포함하면 안 되는 파일 유형
기기별 실구현, I/O 코드, 모델 로딩, 위험도 규칙, 설정 파일은 포함하지 않는다.

## 5. 주요 하위 구성
`base_sensor.py` 하나이며 `SensorState`, `SensorHealth`, `BaseSensor` 계약을 정의한다.

## 6. 입력과 출력 인터페이스
입력은 각 기기 어댑터가 제공하는 원판독값이며, 출력은 상태가 명시된 정규화 판독값이다. 결측은 `None`과 `SensorState`로 표현하고 0이나 마지막 정상값으로 대체하지 않는다.

## 7. 다른 기능 영역과의 관계
`devices/co2|pir|mmwave|thermal/src/`의 어댑터가 구현하고, `ondevice_ai/src/inference/`와 `ondevice_ai/src/risk/`가 소비한다.

**알려진 계층 역전:** 현재 `base_sensor.py`가 `ondevice_ai.src.inference.inference_result.InferenceResult`를 import한다. 공용 계약이 상위 패키지에 의존하는 구조이므로, `InferenceResult`를 이 디렉터리로 올리거나 계약에서 분리하는 정리가 필요하다. 구조 이동 범위를 넘는 코드 변경이라 이번 재편에서는 손대지 않고 기록만 남긴다.

## 8. 실행·학습·추론 또는 활용 방법
```python
from shared.contracts.base_sensor import BaseSensor, SensorState, SensorHealth
```
저장소 루트를 기준으로 import하며, 새 기기 어댑터는 `BaseSensor`를 상속해 추상 메서드를 모두 구현한다.

## 9. 현재 개발 상태 및 버전
V4 계약 기준으로 안정 상태이며 4개 기기 어댑터가 모두 이 계약을 구현한다. `ondevice_ai/tests/test_sensor_adapters.py`가 계약 준수를 검증한다.

## 10. 향후 파일 추가 및 관리 규칙
계약 변경은 하위 호환을 우선 검토하고, 변경 시 4개 기기 어댑터·mock·테스트를 같은 PR에서 함께 갱신한다. 한 기기만 필요한 필드를 계약에 추가하지 않는다.

## 11. 주요 기여자와 원본 브랜치·커밋 추적 정보
담당: Junwoo (`@sheepmeat`), Jinsu (`@jinsu1011`) 공동.
원본 ref `origin/Ondevice_AI` (`d97df3e`), 원본 경로 `src/sensors/base_sensor.py`. 이동 커밋 `38274c0`, import 경로 수정 커밋 `3313f4b`.
