# SCD40 실기기 배선 및 촬영 기준

## 확정 하드웨어

| 항목 | 값 |
|---|---|
| 센서 | SCD40 CO₂ 센서 모듈 |
| 수집 보드 | ESP-WROOM-32 개발보드 |
| I2C 주소 | `0x62` |
| 전원 | ESP32 `3.3V` |
| SDA | ESP32 GPIO21 (`D21`) |
| SCL | ESP32 GPIO22 (`D22`) |
| GND | ESP32 GND와 공통 접지 |
| 풀업 | SCD40 모듈 내장 풀업 사용, 외부 SDA/SCL 풀업 없음 |
| 전송 | ESP32 `192.168.1.16` → Raspberry Pi 5 `192.168.1.44:9000` TCP |
| Pi 서비스 | `sandi@192.168.1.44`, `~/safenest_lcd_remote`, `/usr/bin/python3` |

## 배선 절차

1. ESP32와 외부 전원을 모두 끈다.
2. SCD40 `VDD`를 ESP32 `3.3V`에 연결한다.
3. SCD40 `GND`를 ESP32 `GND`에 연결한다.
4. SCD40 `SDA`를 ESP32 GPIO21에 연결한다.
5. SCD40 `SCL`을 ESP32 GPIO22에 연결한다.
6. SDA/SCL에 외부 풀업 저항을 추가하지 않는다.
7. 배선 단락과 핀 라벨을 확인한 후 ESP32 전원을 넣는다.

## 사진 증거

원본 사진은 사용자의 명시적 동의를 받아 저장소 증거로 사용한다. 실제 파일명과 저장 위치는 다음과 같다.

| 원본 파일명 | 확인된 내용 | CO2 저장소 파일명 | 사용 여부 |
|---|---|---|---|
| `KakaoTalk_20260812_164022975.jpg` | SCD40 모듈과 `SDA/SCL/VDD/GND` 핀 라벨 | `devices/co2/docs/images/2026-08-12_scd40_module_and_pin_labels.jpg` | 포함 |
| `KakaoTalk_20260812_164022975_02.jpg` | HC-SR501 PIR 센서 | 해당 없음 | PIR 브랜치에서 사용 |
| `KakaoTalk_20260812_164022975_04.jpg` | ESP-WROOM-32 보드와 핀 라벨 | `devices/co2/docs/images/2026-08-12_esp32_board_and_wiring.jpg` | 포함 |
| `KakaoTalk_20260812_164022975_01.jpg` | 별도 Seeed Studio 보드 | 해당 없음 | CO2 증거에서 제외 |
| `KakaoTalk_20260812_164022975_03.jpg` | ESP32·센서·브레드보드 전체 배선 | `devices/co2/docs/images/2026-08-12_full_sensor_bench.jpg` | 포함 |
| `KakaoTalk_20260812_173536675.jpg` | SCD40 모듈이 배선에서 분리된 상태 | `devices/co2/docs/images/2026-08-12_scd40_disconnected.jpg` | 포함 |

사진에는 다음이 식별되어야 한다.

- SCD40 모듈의 `SDA`, `SCL`, `VDD`, `GND` 인쇄
- ESP-WROOM-32 보드명과 GPIO21/GPIO22 연결
- 3.3V 전원과 공통 GND
- 센서부터 ESP32까지의 전체 배선

원본 파일은 `C:\Users\small\OneDrive\문서\01_카카오톡 받은 파일\`에서 존재와 파일 크기를 확인했다. 원본 파일 복사는 별도 단계에서 수행하며 이미지 재인코딩이나 편집을 하지 않는다. 복사 전후 SHA-256이 일치해야 한다.

## 주의사항

- SCD40은 5V가 아니라 이번 실측 구성에서 확인된 3.3V로 사용한다.
- 측정 중 센서 흡입구를 손으로 막거나 입김의 수분이 직접 맺히게 하지 않는다.
- 로그의 CO₂ 결측을 `0 ppm`으로 기록하지 않는다. `valid=false`와 비정상 `SensorState`를 함께 기록한다.
