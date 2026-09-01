import socket
import numpy as np
import time
import sys
import os
import random

# V5 Modules Path Setup
repo_path = os.path.expanduser('~/taegyun/safenest-embedded-competition')
ondevice_ai_path = os.path.join(repo_path, 'ondevice_ai')
if ondevice_ai_path not in sys.path:
    sys.path.insert(0, ondevice_ai_path)

try:
    from sensors.base_sensor import SensorState
    from step4_udp_scenario_tester import Thermal44UdpSensor
except ImportError as e:
    print(f"Error importing modules. Ensure step4_udp_scenario_tester.py is in the same directory.")
    print(f"Details: {e}")
    sys.exit(1)

def run_fault_injection_test(sensor):
    print("\n===========================================")
    print(" [Part 1] Fault Injection & Fail-Closed Test ")
    print("===========================================")
    
    # 1. read() before connect()
    print("\n[Test 1] read() before connect()")
    res = sensor.read()
    print(f"  -> State: {res.state}, Valid: {res.valid} (Expected: NOT_CONNECTED/False)")
    
    sensor.connect()
    print("\n[Test 2] Normal read() after connect()")
    res = sensor.read()
    print(f"  -> State: {res.state}, Valid: {res.valid} (Expected: WARMING_UP or NORMAL)")

    print("\n[Test 3] Inject NaN / Inf Data")
    # 강제로 NaN 주입을 위해 잠시 read_frame() 메서드를 후킹(Monkey Patching)합니다.
    original_read_frame = sensor.read_frame
    
    def mock_nan_frame():
        frame = np.zeros((62, 80), dtype=np.float32)
        frame[30, 40] = np.nan
        return frame
        
    sensor.read_frame = mock_nan_frame
    res = sensor.read()
    print(f"  -> State: {res.state}, Valid: {res.valid} (Expected: NAN_OR_INF/False)")
    
    print("\n[Test 4] Inject Invalid Format (Wrong Shape)")
    def mock_invalid_shape():
        return np.zeros((10, 10), dtype=np.float32)
        
    sensor.read_frame = mock_invalid_shape
    res = sensor.read()
    print(f"  -> State: {res.state}, Valid: {res.valid} (Expected: INVALID_FORMAT/False)")
    
    # Restore original method
    sensor.read_frame = original_read_frame

    print("\n[Test 5] Physical Disconnect & Reconnect Test")
    print(">>> ⚠️ [USER ACTION REQUIRED] ⚠️ <<<")
    print("지금 XIAO-ESP32C6의 전원 선(또는 센서 선)을 뽑아주세요!")
    print("타임아웃(NOT_CONNECTED)이 감지될 때까지 기다립니다...")
    
    disconnected = False
    for i in range(10):
        res = sensor.read()
        if res.state in ["NOT_CONNECTED", "WARMING_UP"]:
            print(f"  -> ✅ Disconnect Detected! (State: {res.state})")
            disconnected = True
            break
        time.sleep(1)
        
    if not disconnected:
        print("  -> 단선이 감지되지 않았습니다. 테스트를 계속 진행합니다.")

    print("\n>>> ⚠️ [USER ACTION REQUIRED] ⚠️ <<<")
    print("XIAO-ESP32C6의 전원을 다시 꽂아주세요! 10초 내에 복구되는지 확인합니다...")
    
    reconnected = False
    for i in range(15):
        res = sensor.read()
        if res.valid:
            print(f"  -> ✅ Reconnect Successful! (State: {res.state}, Score: {res.score})")
            reconnected = True
            break
        print(f"     ... Waiting for data (Current state: {res.state})")
        time.sleep(1)

    print("\n[Test 6] close() call")
    sensor.close()
    res = sensor.read()
    print(f"  -> State: {res.state}, Valid: {res.valid} (Expected: NOT_CONNECTED/False)")
    
    return reconnected

def run_performance_benchmark(sensor):
    print("\n===========================================")
    print(" [Part 2] Performance Benchmark (30 Seconds) ")
    print("===========================================")
    
    if not sensor.connect():
        print("Failed to reconnect for benchmark.")
        return

    print("Benchmarking... Please wait 30 seconds.")
    start_time = time.time()
    latencies = []
    valid_count = 0
    total_count = 0
    
    while time.time() - start_time < 30.0:
        res = sensor.read()
        total_count += 1
        
        if res.valid:
            valid_count += 1
            latencies.append(res.latency_ms)
            
        # 과도한 CPU 점유 방지를 위해 아주 짧은 딜레이
        time.sleep(0.01)
        
    sensor.close()
    
    elapsed = time.time() - start_time
    fps = total_count / elapsed
    
    print("\n--- 📊 Benchmark Results ---")
    print(f"Total Time      : {elapsed:.2f} seconds")
    print(f"Total Iterations: {total_count}")
    print(f"Valid Frames    : {valid_count} ({valid_count/total_count*100:.1f}%)")
    print(f"Measured FPS    : {fps:.1f} Hz (Iterations/sec)")
    
    if latencies:
        latencies = np.array(latencies)
        print("\n--- ⏱️ Latency (E2E: Network + Inference) ---")
        print(f"Mean Latency    : {np.mean(latencies):.2f} ms")
        print(f"Min Latency     : {np.min(latencies):.2f} ms")
        print(f"p50 (Median)    : {np.percentile(latencies, 50):.2f} ms")
        print(f"p95 (95th %ile) : {np.percentile(latencies, 95):.2f} ms")
        print(f"Max Latency     : {np.max(latencies):.2f} ms")
    else:
        print("\nNo valid frames received during benchmark!")

def main():
    sensor = Thermal44UdpSensor(
        project_root=ondevice_ai_path,
        udp_port=5005,
        npz_path="thermal_calibration.npz"
    )
    
    try:
        reconnected = run_fault_injection_test(sensor)
        
        if reconnected:
            run_performance_benchmark(sensor)
        else:
            print("\n[!] Reconnection failed. Skipping benchmark.")
    except KeyboardInterrupt:
        print("\nBenchmark aborted by user.")
    finally:
        sensor.close()

if __name__ == "__main__":
    main()
