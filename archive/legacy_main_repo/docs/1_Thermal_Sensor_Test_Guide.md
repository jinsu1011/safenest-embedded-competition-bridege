# 열화상 센서 단독 테스트 및 시각화 매뉴얼 (UDP 방식)

본 문서는 통합 TCP 서버와 별개로, 오로지 열화상 센서(Thermal-90 모듈)의 하드웨어 성능 검증 및 캘리브레이션을 위한 **독립형 UDP 스트리밍 테스트 가이드**입니다.

이 가이드에 해당하는 코드들은 `devices/thermal/thermal_sensor_test` 디렉토리에 위치해 있습니다.

---

## 1. 디렉토리 구성 (thermal_sensor_test)
- `udp_sender_esp32.ino`: 환경 센서들을 제외하고, 순수하게 열화상 프레임만 UDP(포트 5005)로 전송하는 ESP32 아두이노 코드입니다.
- `udp_receiver_rpi.py`: 라즈베리파이에서 포트 5005번으로 들어오는 10,080 바이트의 UDP 패킷을 수신하여 OpenCV로 시각화하는 파이썬 테스트 스크립트입니다. (FPN 노이즈 및 드리프트 보정 기능 탑재)
- `thermal_calibration.npz`: 캘리브레이션을 진행했을 때 생성 및 로드되는 픽셀 보정 데이터 파일입니다.

---

## 2. 테스트 환경 세팅 및 실행

1. **송신부 (ESP32) 업로드**
   - 아두이노 IDE를 열고 `udp_sender_esp32.ino`를 로드합니다.
   - 코드 상단의 Wi-Fi SSID, Password 및 수신할 라즈베리파이의 IP 주소를 본인 환경에 맞게 수정한 후 ESP32에 업로드합니다.

2. **수신부 (라즈베리파이) 원격 접속 및 실행**
   - PC의 VS Code에서 SSH를 통해 라즈베리파이에 원격 접속합니다.
   - 프로젝트 Conda 가상환경(`safenest`)을 활성화합니다.
     ```bash
     source ~/miniconda3/etc/profile.d/conda.sh
     conda activate safenest
     ```
   - 디스플레이 출력을 라즈베리파이 모니터로 강제 연결하고 코드를 실행합니다.
     ```bash
     export DISPLAY=:0
     python udp_receiver_rpi.py
     ```

---

## 3. 열화상 캘리브레이션 (조작법)

영상 창이 띄워진 상태에서 다음 키보드 단축키를 눌러 조작할 수 있습니다.
- `c` 키 (Calibration): 센서를 균일한 온도의 표면(벽 등)에 비춘 상태에서 누르면 32프레임을 수집하여 화면의 얼룩(FPN 노이즈)을 제거하는 오프셋 맵을 생성합니다.
- `s` 키 (Save): 생성된 오프셋 맵을 `thermal_calibration.npz` 파일로 저장합니다. 이후 실행 시 자동 적용됩니다.
- `r` 키 (Reset): 캘리브레이션을 모두 해제하고 순수 RAW 화면으로 돌아갑니다.
- `q` 키 (Quit): 안전하게 테스트를 종료합니다.
