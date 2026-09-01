import json, statistics as st
from pathlib import Path
LOGS=Path(__file__).resolve().parents[1]/"logs"
F=LOGS/"kpi/2026-07-26_heartrate_ref_applewatch_run2_300s.jsonl"
recs=[json.loads(l) for l in open(F) if l.strip()]
t0=recs[0]["ts_monotonic_ms"]
for r in recs: r["t"]=(r["ts_monotonic_ms"]-t0)/1000.0
watch=[88,78,78,75,77,79,82,81,78,80]
print(f"{'win':>5} {'N':>3} {'MAE':>6} {'bias':>6} {'max':>6} {'<=5bpm':>7} {'<=10bpm':>8}")
for half in (5,10,15,30,45):
    errs=[]
    for i,w in enumerate(watch,1):
        tc=30*i
        win=[r["heart_rate_raw"] for r in recs if abs(r["t"]-tc)<=half and r.get("heart_raw_valid") and r.get("heart_rate_raw")]
        if win: errs.append(st.median(win)-w)
    a=[abs(e) for e in errs]
    print(f"{'±'+str(half):>5} {len(errs):>3} {sum(a)/len(a):>6.2f} {sum(errs)/len(errs):>+6.2f} {max(a):>6.1f} "
          f"{sum(1 for x in a if x<=5)}/{len(a):<5} {sum(1 for x in a if x<=10)}/{len(a):<6}")
