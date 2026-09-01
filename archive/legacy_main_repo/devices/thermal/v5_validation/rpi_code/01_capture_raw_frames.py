import socket
import struct
import numpy as np
import time
import os

HOST = '0.0.0.0'
PORT = 9000
EXPECTED_PAYLOAD_SIZE = 9936
FRAME_SHAPE = (62, 80)
MAGIC = b'SNST'

def main():
    save_dir = "captured_data"
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"[{time.strftime('%H:%M:%S')}] TCP Server listening on {HOST}:{PORT}...")
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(1)
    
    frame_count = 0
    buffer = b""
    
    print("Waiting for connection...")
    conn, addr = server_socket.accept()
    print(f"[{time.strftime('%H:%M:%S')}] Connected by {addr}")
    start_time = time.time()
    
    try:
        while frame_count < 20:
            data = conn.recv(16384)
            if not data:
                print("Connection closed by client. Waiting for reconnection...")
                conn.close()
                conn, addr = server_socket.accept()
                print(f"[{time.strftime('%H:%M:%S')}] Reconnected by {addr}")
                buffer = b""
                start_time = time.time() # Reset FPS timer
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
                    
                # Parse 16-byte header
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
                
                # Parse thermal data
                width, height, frame_seq, uptime_ms, min_raw, max_raw = struct.unpack('>HHIIHH', payload[:16])
                pixel_bytes = payload[16:]
                
                raw_pixels = np.frombuffer(pixel_bytes, dtype='>u2')
                if len(raw_pixels) != 4960:
                    continue
                
                temperatures = raw_pixels.astype(np.float32) / 100.0
                frame_2d = temperatures.reshape(FRAME_SHAPE)
                
                t_min = np.min(frame_2d)
                t_max = np.max(frame_2d)
                t_mean = np.mean(frame_2d)
                invalid_count = np.sum((frame_2d < -20) | (frame_2d > 300) | np.isnan(frame_2d) | np.isinf(frame_2d))
                
                frame_count += 1
                fps = frame_count / (time.time() - start_time)
                
                print(f"✅ Frame {frame_count:02d} | Shape: {frame_2d.shape} | Min: {t_min:.1f}°C | Max: {t_max:.1f}°C | Mean: {t_mean:.1f}°C | Invalid: {invalid_count} | FPS: {fps:.1f}")
                
                np.save(os.path.join(save_dir, f"frame_{frame_count:03d}.npy"), frame_2d)
                
        print(f"\n[Validation Complete] 20 frames captured successfully.")
        print(f"Data saved to '{save_dir}' directory.")
                
    except KeyboardInterrupt:
        print("\nStopped by user.")
    finally:
        conn.close()
        server_socket.close()

if __name__ == "__main__":
    main()
