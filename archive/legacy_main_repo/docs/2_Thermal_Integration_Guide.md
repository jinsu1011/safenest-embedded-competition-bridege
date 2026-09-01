# 열화상 센서 통합 TCP 매뉴얼 (ESP32 & Raspberry Pi)

본 문서는 다른 센서(mmWave, CO2, PIR)와 열화상 카메라가 완전히 통합되어 1개의 단일 프로토콜로 작동하는 **TCP 기반 SafeNest 스트리밍 가이드**입니다.

이 가이드에 해당하는 코드들은 `devices/thermal/thermal_integration` 디렉토리에 위치해 있습니다.

---

## 1. 디렉토리 구성 (thermal_integration)
- `esp32_sensor_node.ino`: 팀에서 최종적으로 하나로 병합한 센서 통합 ESP32 아두이노 코드입니다. 열화상 카메라 제어부 및 TCP 패킷(SNST 헤더) 조립 로직이 포함되어 있습니다.
- `tcp_thermal_receiver_rpi.py`: 라즈베리파이에서 포트 9000번 TCP 서버를 열고 대기하며, `SNST` 규격의 헤더를 파싱하여 열화상(Type 2) 패킷이 들어올 때만 화면에 시각화하는 전용 파이썬 수신부입니다.

---

## 2. 통합 프로토콜 규격 (SNST Protocol v1)

모든 데이터는 TCP 포트 9000을 통해 전송되며, 패킷 앞단에 16바이트의 고정 헤더(Big-Endian)가 붙습니다.
- `[0:4]` Magic Word: "SNST"
- `[4]` Version: 1
- `[5]` Type: 1 (환경 센서 JSON 텔레메트리), 2 (열화상 데이터)
- `[6:8]` Flags: 예약됨
- `[8:12]` Sequence: 패킷 순서 번호
- `[12:16]` Payload Length: 뒤따라오는 데이터 길이

**열화상 (Type 2) 상세 구조:**
- 16 바이트 메타데이터: 가로 폭(80), 세로 높이(62), 업타임, 최소/최대 온도
- 9,920 바이트 픽셀 데이터: 4,960개의 해상도 픽셀 (uint16)

---

## 3. 실행 가이드

이전 UDP 방식과는 달리, **수신부(TCP Server)를 먼저 켜두어야 송신부(TCP Client)가 접속**할 수 있습니다.

1. **수신부 (라즈베리파이) 대기**
   - 라즈베리파이 터미널에서 다음 명령을 통해 TCP 9000번 포트를 엽니다.
     ```bash
     export DISPLAY=:0
     python tcp_thermal_receiver_rpi.py
     ```
   - 콘솔에 `[Main] TCP Server listening on port 9000...` 메시지가 뜨면 접속 대기 상태가 됩니다.

2. **송신부 (ESP32) 접속**
   - `esp32_sensor_node.ino` 코드 내의 RPI_HOST 변수를 수신부 라즈베리파이의 IP 주소로 수정한 뒤 업로드합니다.
   - 전원이 켜지면 ESP32가 Wi-Fi에 접속한 후 자동으로 포트 9000번에 TCP 연결을 시도하며 데이터를 스트리밍합니다.
   - 라즈베리파이 화면에 열화상 영상이 팝업되는 것을 확인할 수 있습니다.
