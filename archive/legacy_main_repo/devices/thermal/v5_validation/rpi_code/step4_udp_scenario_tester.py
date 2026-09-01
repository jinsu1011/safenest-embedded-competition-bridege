import socket
import numpy as np
import time
import sys
import os

# safenest-embedded-competition 레포지토리 경로 추가
repo_path = os.path.expanduser('~/taegyun/safenest-embedded-competition')
ondevice_ai_path = os.path.join(repo_path, 'ondevice_ai')
if ondevice_ai_path not in sys.path:
    sys.path.insert(0, ondevice_ai_path)

try:
    from sensors.thermal44.thermal44_driver import Thermal44Sensor
    from sensors.base_sensor import SensorState
except ImportError as e:
    print(f"Error importing V5 modules: {e}")
    sys.exit(1)

# ==========================================
# 1. 캘리브레이션 로직 (UDP Receiver에서 이식)
# ==========================================
class ThermalCalibrator:
    def __init__(self, npz_path="thermal_calibration.npz"):
        self.is_calibrated = False
        self.offset_map = None
        self.offset_mean = 0.0
        self.die_temp_baseline = 0
        self.drift_coeff = -1.02
        
        if os.path.exists(npz_path):
            data = np.load(npz_path)
            self.offset_map = data['offset_map']
            self.offset_mean = data['offset_mean']
            self.die_temp_baseline = data['die_temp_baseline']
            self.is_calibrated = True
            print(f"[Calibrator] Loaded calibration data from {npz_path}")
        else:
            print(f"[Calibrator] WARNING: {npz_path} not found! Uncalibrated data will be used.")

    def correct(self, raw_matrix, die_temp):
        if not self.is_calibrated:
            return raw_matrix
        dt = float(die_temp) - float(self.die_temp_baseline)
        drift_correction = self.drift_coeff * dt
        return raw_matrix - self.offset_map + self.offset_mean - drift_correction

# ==========================================
# 2. UDP 통신용 V5 Provider 래퍼 (Thermal44UdpSensor)
# ==========================================
class Thermal44UdpSensor(Thermal44Sensor):
    def __init__(self, project_root, udp_port=5005, npz_path="thermal_calibration.npz"):
        # 부모 클래스(Thermal44Sensor) 초기화 (TFLite 모델 로드 포함)
        super().__init__(project_root=project_root, timeout_sec=2.0)
        self.udp_port = udp_port
        self.sock = None
        self.calibrator = ThermalCalibrator(npz_path)
        self.packet_buffer = bytearray()

    def connect(self) -> bool:
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.bind(("0.0.0.0", self.udp_port))
            self.sock.settimeout(self.timeout_sec)
            self.connected = True
            self.current_state = SensorState.WARMING_UP
            print(f"[SensorProvider] UDP Socket bound to 0.0.0.0:{self.udp_port}")
            return True
        except Exception as e:
            print(f"[SensorProvider] Failed to connect UDP: {e}")
            self.connected = False
            return False

    def read_frame(self) -> np.ndarray:
        # 10080 bytes가 모일 때까지 수신 (Chunked 패킷 병합)
        try:
            while len(self.packet_buffer) < 10080:
                data, _ = self.sock.recvfrom(65535)
                self.packet_buffer.extend(data)
                
            frame_data = self.packet_buffer[:10080]
            self.packet_buffer = self.packet_buffer[10080:]
            
            raw_array = np.frombuffer(frame_data, dtype=np.uint16)
            die_temp = raw_array[2]
            pixel_data = raw_array[80:]
            
            # float64로 연산 후 TFLite 인터프리터를 위해 float32로 변환
            thermal_matrix = pixel_data.reshape((62, 80)).astype(np.float64)
            corrected_matrix = self.calibrator.correct(thermal_matrix, die_temp)
            return corrected_matrix.astype(np.float32)
        except socket.timeout:
            return None  # 타임아웃 발생 시 V5 드라이버 정책에 따라 None 반환 (이후 NOT_CONNECTED 처리됨)
        except Exception as e:
            print(f"Error reading UDP: {e}")
            return None

    def close(self) -> None:
        if self.sock:
            self.sock.close()
        self.connected = False
        self.current_state = SensorState.SHUTDOWN
        print("[SensorProvider] UDP Socket closed.")

# ==========================================
# 3. 안전 시나리오 테스트 (Step 4 실행부)
# ==========================================
def render_ascii_heatmap(grid):
    chars = [' ', '.', ':', '-', '=', '+', '*', '#', '%', '@']
    min_t, max_t = 20.0, 35.0
    small_grid = grid[::4, ::2]
    heatmap_str = ""
    for row in small_grid:
        line = ""
        for temp in row:
            idx = int(10 * (temp - min_t) / (max_t - min_t))
            idx = max(0, min(9, idx))
            line += chars[idx]
        heatmap_str += line + "\n"
    return heatmap_str

def main():
    print("\n--- Step 4: UDP SensorProvider & Safety Scenario Test ---\n")
    
    # 1. Provider 초기화 및 연결 테스트
    sensor = Thermal44UdpSensor(
        project_root=os.path.join(repo_path, 'ondevice_ai'),
        udp_port=5005,
        npz_path="thermal_calibration.npz"
    )
    
    if not sensor.connect():
        print("Failed to initialize SensorProvider. Exiting.")
        sys.exit(1)
        
    print("\n[Scenario Test Ready] Please perform scenarios A~F in front of the sensor.\n")
    print("Press Ctrl+C to stop.")
    time.sleep(2)
    
    try:
        while True:
            # 2. V5 Provider 규격 통신 (내부적으로 read_frame -> TFLite Inference 수행)
            result = sensor.read()
            
            sys.stdout.write('\033[2J\033[H') # 화면 지우기
            print("--- Thermal-44 UDP Live Validation (Step 4) ---")
            
            if result.valid:
                # 정상적으로 추론이 성공한 경우
                metadata = result.metadata or {}
                # 시각화를 위해 방금 파싱된 프레임을 꺼내옴 (해킹이지만 테스트를 위해 허용)
                # (driver_read()에서 프레임이 변수로 저장되진 않지만, UDP 패킷 수신 성공을 뜻함)
                # 시각화 코드는 생략하거나, 마지막 온도를 출력
                print(f"\n✅ Status: {result.state} (Score: {result.score})")
                print(f"   Confidence : {result.confidence * 100:.1f}%")
                print(f"   Latency    : {result.latency_ms:.1f} ms")
                print(f"   Provider   : {result.sensor_id} [UDP 5005]")
                
                if result.state == "NOT_HUMAN":
                    print("\n[안전 시나리오 A 판정] 빈 장면 - PASS")
                elif result.state == "HUMAN_NORMAL":
                    print("\n[안전 시나리오 B, C 판정] 서 있거나 앉아 있음 - PASS")
                elif result.state == "HUMAN_FALL":
                    print("\n[안전 시나리오 D 판정] 바닥에 누워 있음 (위험) - TRIGGERED!")
            else:
                # 타임아웃, 포맷 에러, NaN 등 장애 발생 시 (Fail-Closed 검증)
                print(f"\n❌ Error State: {result.state}")
                print(f"   Error Msg: {result.error}")
                print(f"   Latency  : {result.latency_ms:.1f} ms")
                
            time.sleep(0.05)
            
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
    finally:
        # 3. Provider 종료 테스트
        sensor.close()

if __name__ == "__main__":
    main()
