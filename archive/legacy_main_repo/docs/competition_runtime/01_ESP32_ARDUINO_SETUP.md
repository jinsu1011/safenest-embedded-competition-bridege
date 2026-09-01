# ESP32를 Arduino IDE에 연결하는 방법

## 1. 준비물

- ESP32 개발보드(ESP32-WROOM/ESP32 Dev Module 계열)
- 데이터 통신이 가능한 USB 케이블
- Arduino IDE 2.x
- 2.4 GHz Wi-Fi 네트워크

충전 전용 USB 케이블은 전원만 공급하고 포트가 나타나지 않으므로 반드시 데이터 케이블을 사용합니다.

## 2. Arduino IDE 설치

1. Arduino 공식 사이트에서 운영체제에 맞는 Arduino IDE 2.x를 설치합니다.
2. Arduino IDE를 실행합니다.
3. `File > Preferences`(한글 UI에서는 `파일 > 환경설정`)를 엽니다.
4. `Additional Boards Manager URLs`에 다음 주소를 추가합니다.

```text
https://espressif.github.io/arduino-esp32/package_esp32_index.json
```

기존 주소가 있으면 줄바꿈 또는 쉼표로 구분해 추가합니다.

## 3. ESP32 보드 패키지 설치

1. 왼쪽의 `Boards Manager`를 엽니다.
2. `esp32`를 검색합니다.
3. 제작사가 `Espressif Systems`인 `esp32` 패키지를 설치합니다.
4. 설치 후 `Tools > Board > esp32 > ESP32 Dev Module`을 선택합니다.

보드에 `DOIT ESP32 DEVKIT V1` 등의 이름이 명확히 인쇄되어 있으면 해당 보드를 선택해도 됩니다. 확실하지 않으면 이 프로젝트는 `ESP32 Dev Module`로 시작합니다.

## 4. USB 드라이버와 포트 확인

ESP32를 USB로 연결한 후 `Tools > Port`에 `COM3`, `COM4` 같은 포트가 나타나는지 확인합니다.

포트가 없으면 보드의 USB-UART 칩을 확인해 드라이버를 설치합니다.

- `CP2102/CP210x`: Silicon Labs CP210x VCP 드라이버
- `CH340/CH341`: WCH CH340 드라이버

Windows 장치 관리자에서 `포트(COM & LPT)` 또는 `기타 장치`를 보면 칩과 오류 상태를 확인할 수 있습니다. 드라이버 설치 후 USB를 다시 연결하고 Arduino IDE를 재실행합니다.

## 5. 필요한 Arduino 라이브러리

`Sketch > Include Library > Manage Libraries`에서 다음을 설치합니다.

- `Sensirion I2C SCD4x` — SCD40/SCD41 CO₂ 센서
- `Seeed Arduino mmWave` — Seeed MR60BHA2 호흡·심박 센서

다음 라이브러리는 ESP32 보드 패키지에 포함되므로 별도로 설치하지 않습니다.

- `WiFi`
- `Wire`
- `SPI`

`Seeed_Arduino_mmWave.h: No such file or directory`가 나오면 Seeed mmWave 라이브러리가 설치되지 않았거나 라이브러리 폴더명이 잘못된 것입니다. Library Manager에서 설치할 수 없다면 Seeed Studio의 해당 라이브러리 ZIP을 받아 `Sketch > Include Library > Add .ZIP Library`로 추가합니다.

## 6. 프로젝트와 Wi-Fi 설정

1. `esp32_sensor_node/esp32_sensor_node.ino`를 엽니다.
2. 같은 폴더의 `secrets.example.h`를 복사해 파일명을 `secrets.h`로 변경합니다.
3. 다음 값을 환경에 맞게 수정합니다.

```cpp
#pragma once
constexpr char WIFI_SSID[] = "YOUR_2_4_GHZ_WIFI_SSID";
constexpr char WIFI_PASSWORD[] = "실제_와이파이_비밀번호";
constexpr char RPI_HOST[] = "192.168.0.50";
constexpr uint16_t RPI_PORT = 9000;
```

Raspberry Pi에서 `hostname -I`로 IP를 확인합니다. `RPI_HOST`에는 `http://`를 붙이지 않고 IP만 입력합니다. ESP32는 2.4 GHz Wi-Fi를 사용해야 합니다.

## 7. 권장 보드 설정

`Tools` 메뉴에서 다음을 기준으로 설정합니다.

- Board: `ESP32 Dev Module`
- Upload Speed: `921600`에서 실패하면 `115200`
- CPU Frequency: `240MHz (WiFi/BT)`
- Flash Frequency: `80MHz`
- Partition Scheme: `Default 4MB with spiffs` 또는 기본값
- Port: 연결된 ESP32의 COM 포트

## 8. 컴파일과 업로드

1. 체크 표시 `Verify`로 먼저 컴파일합니다.
2. 화살표 `Upload`를 누릅니다.
3. `Connecting...`에서 멈추면 ESP32의 `BOOT` 버튼을 누른 채 기다리다가 업로드가 시작되면 놓습니다.
4. 업로드 후 `Tools > Serial Monitor`를 열고 속도를 `115200 baud`로 설정합니다.

정상적인 경우 Wi-Fi 접속과 Raspberry Pi 연결 로그가 표시됩니다.

```text
[network] Raspberry Pi connected
[health] ... thermal_frames=... crc_errors=0 range_errors=0
```

Raspberry Pi 수신 서버를 먼저 실행하지 않았다면 연결 재시도 로그가 나오는 것이 정상입니다.

## 9. 업로드 실패 점검

- 포트가 없음: 데이터 USB 케이블과 CP210x/CH340 드라이버 확인
- 포트 사용 중: Serial Monitor 또는 다른 시리얼 프로그램 종료
- `Failed to connect`: BOOT 버튼 사용, 업로드 속도를 115200으로 낮춤
- Wi-Fi 연결 실패: 2.4 GHz SSID·비밀번호 확인
- Raspberry Pi 연결 실패: 두 장치가 같은 네트워크인지, `RPI_HOST`가 현재 IP인지, 9000 포트 서버가 실행 중인지 확인

