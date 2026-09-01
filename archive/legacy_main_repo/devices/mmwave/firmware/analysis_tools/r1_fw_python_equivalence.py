"""R1: ESP 펌웨어 C++ breathStats() ↔ Python zc_rate() 동치성 검증.

schema 1.2 로그의 breath_phase 시계열을 main.cpp 와 같은 규칙으로 재구성해
breath_phase_std / breath_rate_filtered 를 재계산하고 ESP 가 실제로 출력한
값과 비교한다. 원본 로그는 읽기만 한다.

C++ 대응 (devices/mmwave/firmware/src/main.cpp):
  appendSample()  : 시간 기반 30s 링버퍼, 100ms 간격 게이팅
  windowReady()   : last-first >= 30000-200 ms
  windowStddev()  : 모집단 표준편차(pstdev)
  breathStats()   : 평균 중심화 + 히스테리시스 0.15*std 영교차,
                    rate = 60000*(crossings-1)/(lastCrossMs-firstCrossMs)
"""

import json
import math
import sys
from collections import deque

# include/mmwave_config.h 와 동일해야 한다
BREATH_WINDOW_MS = 30000
BREATH_WINDOW_CAPACITY = 640
TELEMETRY_INTERVAL_MS = 100
WINDOW_READY_TOLERANCE_MS = 200
HYST_FRACTION = 0.15
MIN_PHASE_STD = 0.2
MIN_CROSSINGS = 2

# ESP 는 Serial.print(value, 2) 로 출력한다 → 비교 허용오차
PRINT_QUANT = 0.005


def pstdev(values):
    n = len(values)
    if n == 0:
        return float("nan")
    mean = sum(values) / n
    return math.sqrt(sum((v - mean) ** 2 for v in values) / n)


def breath_stats(window):
    """main.cpp breathStats() 의 Python 재현. window = deque[(ts_ms, value)]"""
    ready = False
    if len(window) >= 2:
        ready = window[-1][0] - window[0][0] >= BREATH_WINDOW_MS - WINDOW_READY_TOLERANCE_MS
    if not ready:
        return {"ready": False, "stddev": None, "rate": None, "crossings": 0}

    values = [v for _, v in window]
    std = pstdev(values)
    if not math.isfinite(std) or std == 0.0:
        return {"ready": True, "stddev": std, "rate": None, "crossings": 0}

    mean = sum(values) / len(values)
    hyst = HYST_FRACTION * std
    state = 0
    crossings = 0
    first_ms = 0
    last_ms = 0
    for ts, value in window:
        centered = value - mean
        if state <= 0 and centered > hyst:
            state = 1
            if crossings == 0:
                first_ms = ts
            last_ms = ts
            crossings += 1
        elif state >= 0 and centered < -hyst:
            state = -1

    rate = None
    if crossings >= MIN_CROSSINGS and last_ms > first_ms:
        rate = 60000.0 * (crossings - 1) / (last_ms - first_ms)
    return {"ready": True, "stddev": std, "rate": rate, "crossings": crossings}


def load_packets(path):
    packets = []
    bad = 0
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                bad += 1
                continue
            if rec.get("schema_version") != "1.2":
                continue
            if rec.get("breath_phase") is None or rec.get("ts_monotonic_ms") is None:
                continue
            packets.append(rec)
    return packets, bad


def main(path):
    packets, bad_lines = load_packets(path)
    print(f"파일: {path}")
    print(f"schema 1.2 패킷 {len(packets)}개, 파싱 불가 {bad_lines}줄\n")

    window = deque()
    last_append_ms = None

    n_ready_cmp = 0
    ready_mismatch = 0
    std_diffs = []
    std_mismatch = 0
    rate_both = 0
    rate_diffs = []
    rate_mismatch = 0
    valid_flag_cmp = 0
    valid_flag_mismatch = 0
    # ESP 만 값 있음 / Python 만 값 있음
    only_esp_rate = 0
    only_py_rate = 0

    worst_std = (0.0, None)
    worst_rate = (0.0, None)

    for rec in packets:
        ts = rec["ts_monotonic_ms"]
        phase = rec["breath_phase"]

        # appendSample() 게이팅 재현
        if not window or ts - last_append_ms >= TELEMETRY_INTERVAL_MS:
            while window and ts - window[0][0] > BREATH_WINDOW_MS:
                window.popleft()
            if len(window) == BREATH_WINDOW_CAPACITY:
                window.popleft()
            window.append((ts, phase))
            last_append_ms = ts

        got = breath_stats(window)

        esp_ready = rec.get("breath_window_ready")
        esp_std = rec.get("breath_phase_std")
        esp_rate = rec.get("breath_rate_filtered")
        esp_valid = rec.get("breath_filtered_valid")

        if esp_ready is not None:
            if bool(esp_ready) != got["ready"]:
                ready_mismatch += 1

        if not got["ready"] or not esp_ready:
            continue
        n_ready_cmp += 1

        # --- breath_phase_std 비교 ---
        if esp_std is not None and got["stddev"] is not None:
            d = abs(got["stddev"] - esp_std)
            std_diffs.append(d)
            if d > PRINT_QUANT:
                std_mismatch += 1
            if d > worst_std[0]:
                worst_std = (d, rec["seq"])

        # --- breath_rate_filtered 비교 ---
        py_rate = got["rate"]
        py_gate_ok = (
            got["stddev"] is not None
            and got["stddev"] >= MIN_PHASE_STD
            and py_rate is not None
            and not rec.get("freeze_detected", False)
        )
        if esp_valid is not None:
            valid_flag_cmp += 1
            if bool(esp_valid) != py_gate_ok:
                valid_flag_mismatch += 1

        if esp_rate is not None and py_rate is not None:
            rate_both += 1
            d = abs(py_rate - esp_rate)
            rate_diffs.append(d)
            if d > PRINT_QUANT:
                rate_mismatch += 1
            if d > worst_rate[0]:
                worst_rate = (d, rec["seq"])
        elif esp_rate is not None and py_rate is None:
            only_esp_rate += 1
        elif esp_rate is None and py_rate is not None and py_gate_ok:
            only_py_rate += 1

    def pct(a, b):
        return f"{a / b * 100:.3f}%" if b else "n/a"

    print("=== window_ready ===")
    print(f"불일치 {ready_mismatch} / {len(packets)}  ({pct(ready_mismatch, len(packets))})")

    print("\n=== breath_phase_std ===")
    if std_diffs:
        std_diffs.sort()
        print(f"비교 {len(std_diffs)}개")
        print(f"불일치(>{PRINT_QUANT}) {std_mismatch}  ({pct(std_mismatch, len(std_diffs))})")
        print(f"평균차 {sum(std_diffs)/len(std_diffs):.6f}  중앙값 {std_diffs[len(std_diffs)//2]:.6f}")
        print(f"p99 {std_diffs[int(len(std_diffs)*0.99)]:.6f}  최대 {worst_std[0]:.6f} (seq={worst_std[1]})")

    print("\n=== breath_rate_filtered ===")
    if rate_diffs:
        rate_diffs.sort()
        print(f"양쪽 모두 값 있음 {rate_both}개")
        print(f"불일치(>{PRINT_QUANT} rpm) {rate_mismatch}  ({pct(rate_mismatch, rate_both)})")
        print(f"평균차 {sum(rate_diffs)/len(rate_diffs):.6f} rpm  중앙값 {rate_diffs[len(rate_diffs)//2]:.6f}")
        print(f"p99 {rate_diffs[int(len(rate_diffs)*0.99)]:.6f}  최대 {worst_rate[0]:.6f} rpm (seq={worst_rate[1]})")
    else:
        print("양쪽 모두 값이 있는 패킷 없음")
    print(f"ESP만 값 있음 {only_esp_rate}   Python만 값 있음 {only_py_rate}")

    print("\n=== breath_filtered_valid 게이트 판정 ===")
    print(f"비교 {valid_flag_cmp}개, 불일치 {valid_flag_mismatch}  ({pct(valid_flag_mismatch, valid_flag_cmp)})")
    print(f"\n(ready 상태에서 비교한 패킷 {n_ready_cmp}개)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1])
