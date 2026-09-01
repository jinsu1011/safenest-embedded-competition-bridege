import json, statistics as st
from pathlib import Path
LOGS=Path(__file__).resolve().parents[1]/"logs"
F=LOGS/"kpi/2026-07-26_heartrate_ref_applewatch_300s.jsonl"
recs=[json.loads(l) for l in open(F) if l.strip()]
t0=recs[0]["ts_monotonic_ms"]
for r in recs: r["t"]=(r["ts_monotonic_ms"]-t0)/1000.0
watch=[86,81,74,79,80,77,75,77,76,77]
pres=sum(1 for r in recs if r.get("human_detected_stable"))/len(recs)*100
hv=sum(1 for r in recs if r.get("heart_raw_valid"))/len(recs)*100
print(f"samples={len(recs)} dur={recs[-1]['t']:.1f}s presence={pres:.1f}% heart_valid={hv:.1f}%")
print(f"dist_median={st.median([r['distance_cm_raw'] for r in recs if r.get('distance_cm_raw')]):.2f}cm")
print(f"\n{'#':>2} {'t(s)':>5} {'watch':>5} {'MR60':>6} {'err':>6} {'n':>4}")
errs=[]
for i,w in enumerate(watch,1):
    tc=30*i
    win=[r["heart_rate_raw"] for r in recs if abs(r["t"]-tc)<=5 and r.get("heart_raw_valid") and r.get("heart_rate_raw")]
    if not win:
        print(f"{i:>2} {tc:>5} {w:>5} {'--':>6} {'--':>6} {0:>4}"); continue
    m=st.median(win); e=m-w; errs.append(e)
    print(f"{i:>2} {tc:>5} {w:>5} {m:>6.1f} {e:>+6.1f} {len(win):>4}")
a=[abs(e) for e in errs]
print(f"\nN={len(errs)}  MAE={sum(a)/len(a):.2f}bpm  bias={sum(errs)/len(errs):+.2f}bpm  max|err|={max(a):.1f}bpm")
for th in (3,5,10):
    print(f"  |err|<={th}bpm : {sum(1 for x in a if x<=th)}/{len(a)} ({sum(1 for x in a if x<=th)/len(a)*100:.0f}%)")
allhr=[r["heart_rate_raw"] for r in recs if r.get("heart_raw_valid") and r.get("heart_rate_raw")]
print(f"\nMR60 전체: median={st.median(allhr):.1f} mean={st.mean(allhr):.1f} std={st.pstdev(allhr):.2f} min={min(allhr):.0f} max={max(allhr):.0f}")
print(f"워치 전체: median={st.median(watch):.1f} mean={st.mean(watch):.1f} std={st.pstdev(watch):.2f}")
