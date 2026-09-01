import json, statistics as st
from pathlib import Path
LOGS=Path(__file__).resolve().parents[1]/"logs"
F=LOGS/"kpi/2026-07-26_heartrate_ref_applewatch_run2_300s.jsonl"
recs=[json.loads(l) for l in open(F) if l.strip()]
t0=recs[0]["ts_monotonic_ms"]
for r in recs: r["t"]=(r["ts_monotonic_ms"]-t0)/1000.0
for lo in range(0,300,30):
    w=[r for r in recs if lo<=r["t"]<lo+30]
    d=[r["distance_cm_raw"] for r in w if r.get("distance_cm_raw")]
    hv=sum(1 for r in w if r.get("heart_raw_valid"))/len(w)*100
    print(f"{lo:>3}-{lo+30:>3}s dist_med={st.median(d):7.2f} std={st.pstdev(d):6.2f} heart_valid={hv:5.1f}%")
