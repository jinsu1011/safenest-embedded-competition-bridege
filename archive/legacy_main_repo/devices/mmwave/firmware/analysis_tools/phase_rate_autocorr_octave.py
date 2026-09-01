import json, statistics as st, sys
def load(F):
    r=[json.loads(l) for l in open(F) if l.strip()]
    cu=[i for i,x in enumerate(r) if x.get("kind")=="cue"]
    if any(r[i].get("stage")=="measurement" for i in cu):
        cu=[i for i in cu if r[i].get("stage")=="measurement"]
    w=[x for x in r[cu[0]:cu[-1]+1] if x.get("kind")!="cue"]
    return w
LO,HI=1.4,7.5           # 8~43 rpm
def rate_v2(seg, fs, ratio=0.85):
    mu=sum(seg)/len(seg); d=[x-mu for x in seg]; n=len(d)
    ac={}
    for lag in range(int(fs*LO), int(fs*HI)):
        if n-lag < fs*3: break
        ac[lag]=sum(d[i]*d[i+lag] for i in range(n-lag))/(n-lag)
    if not ac: return None
    peak=max(ac.values())
    if peak<=0: return None
    lags=sorted(ac)
    for k,lag in enumerate(lags):
        if ac[lag] < ratio*peak: continue
        prev=ac[lags[k-1]] if k>0 else -1e9
        nxt=ac[lags[k+1]] if k+1<len(lags) else -1e9
        if ac[lag]>=prev and ac[lag]>=nxt:      # 국소 최대
            return 60.0/(lag/fs)
    return 60.0/(max(ac,key=ac.get)/fs)
for F,TGT in [(sys.argv[1],float(sys.argv[2])),(sys.argv[3],float(sys.argv[4]))]:
    w=load(F); t=[x["ts_monotonic_ms"]/1000 for x in w]; p=[x["breath_phase"] for x in w]
    fs=round(len(t)/(t[-1]-t[0]))
    print(f"\n### 목표 {TGT:.0f} rpm   ({len(w)}샘플)")
    print(f"{'창':>5} {'mean':>6} {'std':>5} {'bias':>6} {'±1rpm':>7} {'±2rpm':>7}")
    for ws in (20,30,45):
        W=int(fs*ws)
        out=[v for v in (rate_v2(p[s:s+W],fs) for s in range(0,len(p)-W,fs)) if v]
        a=[abs(v-TGT) for v in out]
        print(f"{ws:>4}s {st.mean(out):>6.2f} {st.pstdev(out):>5.2f} {st.mean(out)-TGT:>+6.2f} "
              f"{sum(1 for x in a if x<=1)/len(a)*100:>6.1f}% {sum(1 for x in a if x<=2)/len(a)*100:>6.1f}%")
