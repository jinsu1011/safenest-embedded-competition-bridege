import json, statistics as st, sys
F=sys.argv[1]; TGT=float(sys.argv[2])
r=[json.loads(l) for l in open(F) if l.strip()]
idx=[i for i,x in enumerate(r) if x.get("kind")=="cue" and x.get("stage")=="measurement"]
w=[x for x in r[idx[0]:idx[-1]+1] if x.get("kind")!="cue"]
t=[x["ts_monotonic_ms"]/1000.0 for x in w]
p=[x["breath_phase"] for x in w]
fs=round(len(t)/(t[-1]-t[0]))

def rate_from_phase(seg, fs):
    mu=sum(seg)/len(seg); d=[x-mu for x in seg]; n=len(d)
    best=(0,0.0)
    for lag in range(int(fs*2.0), int(fs*7.5)):   # 8~30rpm
        if n-lag < fs*4: break
        s=sum(d[i]*d[i+lag] for i in range(n-lag))/(n-lag)
        if s>best[1]: best=(lag,s)
    return 60.0/(best[0]/fs) if best[0] else None

print(f"{'창':>5} {'n':>4} {'mean':>6} {'std':>5} {'bias':>6} {'±1rpm':>7} {'±2rpm':>7} {'±3rpm':>7}")
for winsec in (20,30,45,60):
    W=int(fs*winsec); out=[]
    for s in range(0, len(p)-W, fs):     # 1초 간격
        v=rate_from_phase(p[s:s+W], fs)
        if v: out.append(v)
    if not out: continue
    a=[abs(v-TGT) for v in out]
    print(f"{winsec:>4}s {len(out):>4} {st.mean(out):>6.2f} {st.pstdev(out):>5.2f} {st.mean(out)-TGT:>+6.2f} "
          f"{sum(1 for x in a if x<=1)/len(a)*100:>6.1f}% {sum(1 for x in a if x<=2)/len(a)*100:>6.1f}% {sum(1 for x in a if x<=3)/len(a)*100:>6.1f}%")
print(f"\n[비교] MR60 내장 breath_rate_raw: mean=18.03 bias=+3.03 ±2rpm=13.9%")
