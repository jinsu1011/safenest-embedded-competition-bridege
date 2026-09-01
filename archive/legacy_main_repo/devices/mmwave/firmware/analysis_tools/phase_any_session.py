import json, statistics as st, sys
F=sys.argv[1]
r=[json.loads(l) for l in open(F) if l.strip()]
idx=[i for i,x in enumerate(r) if x.get("kind")=="cue" and (x.get("stage") in (None,"measurement"))]
if any(x.get("stage")=="measurement" for x in r if x.get("kind")=="cue"):
    idx=[i for i,x in enumerate(r) if x.get("kind")=="cue" and x.get("stage")=="measurement"]
w=[x for x in r[idx[0]:idx[-1]+1] if x.get("kind")!="cue"]
t=[x["ts_monotonic_ms"]/1000.0 for x in w]; p=[x["breath_phase"] for x in w]
fs=round(len(t)/(t[-1]-t[0]))
print(f"{len(w)}샘플 {t[-1]-t[0]:.0f}s @{fs}Hz")
def rate(seg,fs,lo=2.0,hi=13.0):
    mu=sum(seg)/len(seg); d=[x-mu for x in seg]; n=len(d); best=(0,0.0)
    for lag in range(int(fs*lo),int(fs*hi)):
        if n-lag<fs*4: break
        s=sum(d[i]*d[i+lag] for i in range(n-lag))/(n-lag)
        if s>best[1]: best=(lag,s)
    return 60.0/(best[0]/fs) if best[0] else None
print(f"전체 자기상관 -> {rate(p,fs):.2f} rpm")
W=int(fs*30); out=[rate(p[s:s+W],fs) for s in range(0,len(p)-W,fs)]
out=[v for v in out if v]
print(f"30초 창 슬라이딩: median={st.median(out):.2f} mean={st.mean(out):.2f} std={st.pstdev(out):.2f} n={len(out)}")
m=st.median(out)
print(f"  중앙값 기준 ±1rpm 일관성: {sum(1 for v in out if abs(v-m)<=1)/len(out)*100:.1f}%")
raw=[x["breath_rate_raw"] for x in w if x.get("breath_rate_raw")]
print(f"MR60 내장값: mean={st.mean(raw):.2f} median={st.median(raw):.2f}")
