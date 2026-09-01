import json
from pathlib import Path
B=Path(__file__).resolve().parents[1]/"logs"
files=[("빈공간 6분(무인)", f"{B}/baseline/2026-07-25_empty_gate_v1_360s.jsonl"),
       ("인체 90cm 6분(07-25)", f"{B}/baseline/2026-07-25_occupied_d09_v1_360s.jsonl"),
       ("인체 90cm 5분(07-26 2차)", f"{B}/kpi/2026-07-26_heartrate_ref_applewatch_run2_300s.jsonl")]
def pos(v): return v is not None and v > 0
print(f"{'세션':<26} {'schema':>6} {'n':>5} {'재실%':>7} {'심박신호%':>9} {'호흡신호%':>9}")
rows={}
for name,f in files:
    r=[json.loads(l) for l in open(f) if l.strip()]
    n=len(r); sc=r[0].get("schema_version")
    pres=sum(1 for x in r if x.get("human_detected_stable", x.get("human_detected_raw")))/n*100
    hv=sum(1 for x in r if pos(x.get("heart_rate_raw")))/n*100
    bv=sum(1 for x in r if pos(x.get("breath_rate_raw")))/n*100
    rows[name]=(hv,bv)
    print(f"{name:<26} {sc:>6} {n:>5} {pres:>7.1f} {hv:>9.1f} {bv:>9.1f}")
e=rows["빈공간 6분(무인)"]; o=rows["인체 90cm 6분(07-25)"]
print(f"\n판별력(무인 대비): 심박신호 {e[0]:.1f}% -> {o[0]:.1f}%   호흡신호 {e[1]:.1f}% -> {o[1]:.1f}%")
