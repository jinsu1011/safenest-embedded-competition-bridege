import json, statistics as st
from pathlib import Path
LOGS=Path(__file__).resolve().parents[1]/"logs"
F=LOGS/"kpi/2026-07-26_heartrate_ref_applewatch_run2_300s.jsonl"
recs=[json.loads(l) for l in open(F) if l.strip()]
t0=recs[0]["ts_monotonic_ms"]
for r in recs: r["t"]=(r["ts_monotonic_ms"]-t0)/1000.0
watch=[88,78,78,75,77,79,82,81,78,80]

def series(half):
    out=[]
    for i in range(1,11):
        tc=30*i
        w=[r["heart_rate_raw"] for r in recs if abs(r["t"]-tc)<=half and r.get("heart_raw_valid") and r.get("heart_rate_raw")]
        out.append(st.median(w) if w else None)
    return out

def pearson(x,y):
    mx,my=st.mean(x),st.mean(y)
    num=sum((a-mx)*(b-my) for a,b in zip(x,y))
    den=(sum((a-mx)**2 for a in x)*sum((b-my)**2 for b in y))**0.5
    return num/den if den else 0.0

print(f"{'win':>5} {'r':>6} {'MAE_raw':>8} {'MAE_보정':>9} {'<=5bpm':>7} {'<=3bpm':>7} {'offset':>7}")
for half in (5,15,30,45):
    m=series(half)
    e=[a-b for a,b in zip(m,watch)]
    off=st.median(e)
    ec=[x-off for x in e]
    r=pearson(m,watch)
    ar,ac=[abs(x) for x in e],[abs(x) for x in ec]
    print(f"{'±'+str(half):>5} {r:>+6.2f} {sum(ar)/10:>8.2f} {sum(ac)/10:>9.2f} "
          f"{sum(1 for x in ac if x<=5)}/10   {sum(1 for x in ac if x<=3)}/10   {off:>+7.1f}")

m15=series(15)
print("\n워치:", watch)
print("MR60(±15s):", [f"{x:.0f}" for x in m15])
print("보정후:", [f"{x-st.median([a-b for a,b in zip(m15,watch)]):.0f}" for x in m15])
print(f"\n생체신호 출력률: heart_valid={sum(1 for r in recs if r.get('heart_raw_valid'))/len(recs)*100:.1f}%  "
      f"breath_valid={sum(1 for r in recs if r.get('breath_raw_valid'))/len(recs)*100:.1f}%")
