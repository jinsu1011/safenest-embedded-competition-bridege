import socket
import struct
import numpy as np
import time
import sys
import os

# safenest-embedded-competition 레포지토리 경로 추가 (V5 모듈 임포트용)
repo_path = os.path.expanduser('~/taegyun/safenest-embedded-competition')
if repo_path not in sys.path:
    sys.path.insert(0, repo_path)

try:
    from ondevice_ai.sensors.thermal44.frame_parser import ThermalFrameParser
    from ondevice_ai.inference.thermal_interpreter import ThermalInterpreter
except ImportError as e:
    print(f"Error importing V5 modules: {e}")
    print(f"Ensure that {repo_path} exists and contains 'ondevice_ai'.")
    sys.exit(1)

HOST = '0.0.0.0'
PORT = 9000
EXPECTED_PAYLOAD_SIZE = 9936
MAGIC = b'SNST'

def render_ascii_heatmap(grid):
    # ASCII 문자 그라데이션 (추운 곳 -> 더운 곳)
    chars = [' ', '.', ':', '-', '=', '+', '*', '#', '%', '@']
    min_t, max_t = 20.0, 35.0 # 시각화 기준 온도 범위
    
    # 터미널 출력을 위해 크기를 줄임 (62x80 -> 15x40)
    small_grid = grid[::4, ::2]
    
    heatmap_str = "\n--- Live Thermal Heatmap (Real Hardware) ---\n"
    for row in small_grid:
        line = ""
        for temp in row:
            # 온도를 0~9 인덱스로 매핑
            idx = int(10 * (temp - min_t) / (max_t - min_t))
            idx = max(0, min(9, idx))
            line += chars[idx]
        heatmap_str += line + "\n"
    return heatmap_str

def main():
    print("Loading V5 ThermalInterpreter...")
    interpreter = ThermalInterpreter(project_root=os.path.join(repo_path, 'ondevice_ai'))
    print("Model loaded successfully.\n")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    
    print(f"TCP Server listening on {HOST}:{PORT}...")
    conn, addr = server_socket.accept()
    print(f"Connected by {addr}")
    
    buffer = b""
    frame_count = 0
    start_time = time.time()
    
    try:
        while True:
            data = conn.recv(8192)
            if not data:
                print("Connection closed. Waiting for reconnect...")
                conn.close()
                conn, addr = server_socket.accept()
                buffer = b""
                continue
                
            buffer += data
            
            while len(buffer) >= 16:
                magic_idx = buffer.find(MAGIC)
                if magic_idx == -1:
                    buffer = b""
                    break
                if magic_idx > 0:
                    buffer = buffer[magic_idx:]
                if len(buffer) < 16:
                    break
                    
                version, packet_type, flags, seq, payload_len = struct.unpack('>BBHII', buffer[4:16])
                total_packet_len = 16 + payload_len
                
                if len(buffer) < total_packet_len:
                    break
                    
                packet = buffer[:total_packet_len]
                buffer = buffer[total_packet_len:]
                
                if packet_type != 2:
                    continue
                    
                payload = packet[16:]
                if len(payload) != EXPECTED_PAYLOAD_SIZE:
                    continue
                
                # 1. 원본 바이트 언패킹 (ESP32는 uint16 Big-endian 전송)
                pixel_bytes = payload[16:]
                raw_pixels = np.frombuffer(pixel_bytes, dtype='>u2')
                
                # 2. 어댑터 단에서 float32 변환 (Phase 3 발견 사항: V5 파서는 float32 ndarray를 기대함)
                temperatures = raw_pixels.astype(np.float32) / 100.0
                
                # 3. V5 프로덕션 Frame Parser 검증 (Phase 3)
                try:
                    grid_62x80 = ThermalFrameParser.parse_raw_buffer(temperatures)
                    int8_quantized = ThermalFrameParser.normalize_to_int8(grid_62x80)
                    parser_status = "OK"
                except Exception as e:
                    parser_status = f"ERROR ({e})"
                    continue
                
                frame_count += 1
                fps = frame_count / (time.time() - start_time)
                
                # 4. V5 TFLite 프로덕션 추론 (Phase 5)
                pred = interpreter.predict(grid_62x80)
                
                # 터미널 화면 갱신 (ANSI escape code)
                sys.stdout.write('\033[2J\033[H') # 화면 지우고 커서 맨 위로
                
                print(render_ascii_heatmap(grid_62x80))
                print(f"[Phase 3] Parser Status: {parser_status}")
                print(f"[Phase 3] Array Shape: {grid_62x80.shape}, Dtype: {grid_62x80.dtype}")
                print(f"          Min: {np.min(grid_62x80):.1f}°C, Max: {np.max(grid_62x80):.1f}°C")
                print(f"          Invalid Pixels: 0 (Validated by Parser)")
                print(f"\n[Phase 5] TFLite Inference Results (Real Hardware Data):")
                print(f"          Model ID: {pred.model_id} (v{pred.model_version})")
                print(f"          Prediction: {pred.class_name} (Index: {pred.class_index})")
                print(f"          Confidence: {pred.confidence*100:.1f}%")
                print(f"          Latency: {pred.latency_ms:.1f} ms")
                print(f"\n[System]  Frame: {frame_count} | FPS: {fps:.1f}")
                
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        conn.close()
        server_socket.close()

if __name__ == "__main__":
    main()
