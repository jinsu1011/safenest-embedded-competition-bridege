# `devices/thermal/`

## 1. 디렉터리 목적
Thermal-44 열화상 센서의 드라이버, 프레임 파서, 배선·보정 자료와 기기 단독 테스트를 담당자가 한곳에서 관리한다.

현재 명칭 경계는 다음과 같다. `Thermal-44`는 기존 team runtime의 `thermal44` sensor ID, mock/parser, historical v0.1.0 inference 경로를 가리키며 실제 장치 연결 검증은 완료되지 않았다. `Thermal-90`은 PR #22의 XIAO ESP32-C6 + SNTR UDP V2 pre-T-C raw capture/pilot 대상이다. 두 명칭 사이의 shape, dtype, unit, orientation, header, FPS, invalid-pixel 계약 호환성은 증명되지 않았고 `FINAL_THERMAL_HARDWARE_SELECTION = NOT_YET_FROZEN`이다.

## 2. 시스템에서 담당하는 기능
열화상 센서에서 프레임을 읽고 파싱해 낙상 추론이 소비할 수 있는 정규화된 온도 배열로 제공한다.

## 3. 포함해야 하는 파일 유형
Thermal 드라이버·프레임 파서·mock, 센서 설정, 배선·시야각·설치 높이 문서, Thermal만으로 통과 가능한 테스트를 포함한다.

## 4. 포함하면 안 되는 파일 유형
Thermal TFLite 모델·학습 스크립트·전처리(`ondevice_ai/models/thermal/`, `ondevice_ai/src/training/`), 공용 인터페이스(`shared/contracts/`), 다른 기기 코드는 포함하지 않는다.

## 5. 주요 하위 구성
`src/thermal44_driver.py`(장치 드라이버), `src/frame_parser.py`(프레임 파싱), `src/mock_sensor.py`(하드웨어 없는 대체 구현)로 구성된다. 배선 문서와 기기 테스트는 아직 없다.

Thermal-90의 현재 pre-T-C raw 수집 송신기는
`xiao_esp32c6_thermal90_udp_capture/`에 있다. 이 구현은 10,080-byte
little-endian 논리 frame을 SNTR UDP V2 chunk 9개로 전송하며 frame ID,
chunk index/count, offset/length, 전체 frame CRC32를 포함한다. 기존
`thermal_sensor_test/`와 `v5_validation/` 송신기는 과거 검증 재현용이며 새
계약형 수집에는 사용하지 않는다.

SNTR `transport_frame_id`는 UDP 논리 프레임 식별자다. Thermal header word 0은 `SENSOR_HEADER_WORD0_OBSERVED / SEMANTICS_UNVERIFIED`이며 검증된 sensor acquisition counter가 아니다. 펌웨어는 sender-side ready drop, send failure, attempted/emitted frame과 uptime을 별도 status packet으로 내보내지만, Pi에 status가 도달하지 않은 세션에서는 end-to-end acquisition completeness를 주장할 수 없다.

## 6. 입력과 출력 인터페이스
입력은 Thermal-44의 원시 프레임 바이트열이며, 출력은 파싱된 온도 배열과 `SensorState` 기반 결측·형식오류 상태다. 결측 픽셀을 임의 보간하지 않는다.

## 7. 다른 기능 영역과의 관계
`shared/contracts/base_sensor.py`를 구현하고, `ondevice_ai/src/inference/thermal_interpreter.py`가 이 출력을 INT8 낙상 모델 입력으로 사용한다. 학습·전처리는 `ondevice_ai/src/training/`에 있다.

## 8. 실행·학습·추론 또는 활용 방법
하드웨어 없이 확인할 때는 `src/mock_sensor.py`를 사용하고, 추론 검증은 `ondevice_ai/tests/test_thermal_interpreter.py`, 성능 측정은 `ondevice_ai/benchmarks/benchmark_thermal.py`를 사용한다.

## 9. 현재 개발 상태 및 버전
드라이버·파서·mock 단계다. Thermal 낙상 INT8 모델 `ondevice_ai/models/thermal/thermal_fall_int8_v0.1.0.tflite`가 존재하며 실기기 연결 검증은 미완이다.

XIAO ESP32-C6 SNTR UDP V2 firmware는 compile-only 검증 상태다. 실제 보드
업로드, Raspberry Pi 수신, Thermal-90 물리 단위·방향·FPS 검증은 T-C에서
수행해야 한다.

## 10. 향후 파일 추가 및 관리 규칙
실기기 연결 시 `docs/`에 배선도·시야각·설치 높이 기준을, `tests/`에 기기 단독 테스트를 추가한다. 프레임 포맷 변경은 파서·해석기·테스트를 함께 갱신한다.

## 11. 주요 기여자와 원본 브랜치·커밋 추적 정보
담당: Taegyun (`@rla1729`) — Thermal 센서. (handle은 2026-08-03 저장소 collaborator 목록으로 확인)
원본 ref `origin/Ondevice_AI` (`d97df3e`), 원본 경로 `src/sensors/thermal/`. 2026-08-03 이동 커밋 `38274c0`에서 현재 경로로 옮겼다.
