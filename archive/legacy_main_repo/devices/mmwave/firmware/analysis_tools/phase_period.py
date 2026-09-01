import json, statistics as st, sys
F=sys.argv[1]; TGT=float(sys.argv[2])
r=[json.loads(l) for l in open(F) if l.strip()]
idx=[i for i,x in enumerate(r) if x.get("kind")=="cue" and x.get("stage")=="measurement"]
w=[x for x in r[idx[0]:idx[-1]+1] if x.get("kind")!="cue"]
t=[x["ts_monotonic_ms"]/1000.0 for x in w]
p=[x["breath_phase"] for x in w]
fs=len(t)/(t[-1]-t[0])
print(f"샘플레이트 {fs:.2f}Hz, {len(p)}샘플, {t[-1]-t[0]:.1f}s")
# 이동평균 제거(디트렌드) 후 영교차
win=int(fs*8)
det=[]
for i in range(len(p)):
    a,b=max(0,i-win//2),min(len(p),i+win//2)
    det.append(p[i]-sum(p[a:b])/(b-a))
cross=[]
for i in range(1,len(det)):
    if det[i-1]<0<=det[i]: cross.append(t[i])
if len(cross)>2:
    per=[cross[i+1]-cross[i] for i in range(len(cross)-1)]
    per=[x for x in per if x>0.8]
    print(f"영교차 주기: median={st.median(per):.3f}s  mean={st.mean(per):.3f}s  n={len(per)}")
    print(f"  -> 실제 호흡수 = {60/st.median(per):.2f} rpm")
# 자기상관
import math
n=len(det); mu=st.mean(det)
d=[x-mu for x in det]
best=(0,0)
for lag in range(int(fs*1.5), int(fs*8)):
    s=sum(d[i]*d[i+lag] for i in range(n-lag))/(n-lag)
    if s>best[1]: best=(lag,s)
print(f"자기상관 최대 lag={best[0]/fs:.3f}s -> {60/(best[0]/fs):.2f} rpm")
print(f"\n메트로놈 목표: {TGT:.0f} rpm ({60/TGT:.2f}s 주기)")
