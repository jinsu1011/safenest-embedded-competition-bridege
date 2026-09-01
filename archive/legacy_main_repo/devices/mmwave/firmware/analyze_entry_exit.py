#!/usr/bin/env python3
"""Analyse an entry/exit KPI trial log.

For each entry beep: detection latency = first sensor sample with
human_detected_raw == True whose host_monotonic_ns > beep_host_ns.

For each exit beep: release latency = host time of the first sensor sample
that begins a run of >= min_consec consecutive human_detected_raw == False,
minus beep_host_ns.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


def load(path: Path):
    sensor, beeps = [], []
    for line in path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        if item.get("kind") == "sensor":
            sensor.append(item)
        elif item.get("kind") == "beep":
            beeps.append(item)
    sensor.sort(key=lambda r: r["host_monotonic_ns"])
    beeps.sort(key=lambda r: r["host_monotonic_ns"])
    return sensor, beeps


def detect_entry_latency(sensor, beep_ns, max_wait_s):
    for r in sensor:
        if r["host_monotonic_ns"] < beep_ns:
            continue
        gap = (r["host_monotonic_ns"] - beep_ns) / 1e9
        if gap > max_wait_s:
            return None
        if r.get("human_detected_raw") is True:
            return gap
    return None


def detect_exit_latency(sensor, beep_ns, min_consec, max_wait_s):
    consec = 0
    consec_start_ns = None
    for r in sensor:
        if r["host_monotonic_ns"] < beep_ns:
            continue
        gap = (r["host_monotonic_ns"] - beep_ns) / 1e9
        if gap > max_wait_s:
            return None
        if r.get("human_detected_raw") is False:
            if consec == 0:
                consec_start_ns = r["host_monotonic_ns"]
            consec += 1
            if consec >= min_consec:
                return (consec_start_ns - beep_ns) / 1e9
        else:
            consec = 0
            consec_start_ns = None
    return None


def stats(name, values, kpi_threshold):
    if not values:
        print(f"{name}: 데이터 없음")
        return
    pass_count = sum(1 for v in values if v <= kpi_threshold)
    print(f"\n== {name} (n={len(values)}) ==")
    print(f"  평균 {statistics.fmean(values):.3f}s · 중앙값 {statistics.median(values):.3f}s "
          f"· std {statistics.stdev(values) if len(values) > 1 else 0:.3f}s")
    print(f"  최소 {min(values):.3f}s · 최대 {max(values):.3f}s")
    print(f"  KPI ≤ {kpi_threshold:.1f}s 통과 {pass_count}/{len(values)} "
          f"({pass_count/len(values)*100:.1f}%)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--kpi", type=float, default=2.0)
    parser.add_argument("--min-consec-no", type=int, default=5,
                        help="exit이 유효하려면 연속 NO 샘플이 몇 개여야 하는가")
    parser.add_argument("--max-wait", type=float, default=15.0,
                        help="beep 이후 얼마까지 결과를 기다릴지")
    parser.add_argument("--walk-baseline", type=float, default=0.8,
                        help="사람 걷기+반응 소요를 뺀 순수 센서 지연도 함께 출력")
    args = parser.parse_args()

    sensor, beeps = load(args.input)
    print(f"센서 샘플 {len(sensor)}개 · 비프 이벤트 {len(beeps)}개")

    entry_latencies, exit_latencies = [], []
    per_trial = []
    for b in beeps:
        if b["event"] == "enter":
            lat = detect_entry_latency(sensor, b["host_monotonic_ns"], args.max_wait)
            if lat is not None:
                entry_latencies.append(lat)
            per_trial.append(("enter", b["trial"], lat))
        else:
            lat = detect_exit_latency(sensor, b["host_monotonic_ns"],
                                       args.min_consec_no, args.max_wait)
            if lat is not None:
                exit_latencies.append(lat)
            per_trial.append(("exit", b["trial"], lat))

    print("\n각 시행 결과:")
    for kind, trial, lat in per_trial:
        s = f"{lat:.3f}s" if lat is not None else "NO_DETECT"
        print(f"  회 {trial:2d} {kind:5s}: {s}")

    stats("감지 지연 (센서 YES까지 · 걷기+반응 포함)", entry_latencies, args.kpi)
    stats("해제 지연 (센서 NO 연속 유지까지)", exit_latencies, args.kpi)

    if entry_latencies:
        adj = [max(0.0, v - args.walk_baseline) for v in entry_latencies]
        stats(f"감지 지연 순수 (걷기+반응 {args.walk_baseline:.1f}s 차감)",
              adj, args.kpi)
    if exit_latencies:
        adj = [max(0.0, v - args.walk_baseline) for v in exit_latencies]
        stats(f"해제 지연 순수 (걷기+반응 {args.walk_baseline:.1f}s 차감)",
              adj, args.kpi)


if __name__ == "__main__":
    main()
