import json, statistics as st, sys
def load(F):
    r=[json.loads(l) for l in open(F) if l.strip()]
    cu=[i for i,x in enumerate(r) if x.get("kind")=="cue"]
    if any(r[i].get("stage")=="measurement" for i in cu):
        cu=[i for i in cu if r[i].get("stage")=="measurement"]
    return [x for x in r[cu[0]:cu[-1]+1] if x.get("kind")!="cue"]
def zc_rate(seg, fs, hyst_frac=0.15):
    mu=sum(seg)/len(seg); d=[x-mu for x in seg]
    amp=st.pstdev(d)
    if amp==0: return None
    h=hyst_frac*amp; state=0; cross=[]
    for i,v in enumerate(d):
        if state<=0 and v>h: state=1; cross.append(i)
        elif state>=0 and v<-h: state=-1
    if len(cross)<2: return None
    return 60.0*(len(cross)-1)/((cross[-1]-cross[0])/fs)
for F,TGT in [(sys.argv[1],float(sys.argv[2])),(sys.argv[3],float(sys.argv[4]))]:
    w=load(F); t=[x["ts_monotonic_ms"]/1000 for x in w]; p=[x["breath_phase"] for x in w]
    fs=round(len(t)/(t[-1]-t[0]))
    print(f"\n### 목표 {TGT:.0f} rpm | breath_phase std={st.pstdev(p):.4f} "
          f"| 호흡유효 {sum(1 for x in w if x.get('breath_raw_valid'))/len(w)*100:.1f}%")
    print(f"{'창':>5} {'mean':>6} {'std':>5} {'bias':>6} {'±1rpm':>7} {'±2rpm':>7} {'±3rpm':>7}")
    for ws in (20,30,45):
        W=int(fs*ws)
        out=[v for v in (zc_rate(p[s:s+W],fs) for s in range(0,len(p)-W,fs)) if v]
        a=[abs(v-TGT) for v in out]
        print(f"{ws:>4}s {st.mean(out):>6.2f} {st.pstdev(out):>5.2f} {st.mean(out)-TGT:>+6.2f} "
              f"{sum(1 for x in a if x<=1)/len(a)*100:>6.1f}% {sum(1 for x in a if x<=2)/len(a)*100:>6.1f}% "
              f"{sum(1 for x in a if x<=3)/len(a)*100:>6.1f}%")
