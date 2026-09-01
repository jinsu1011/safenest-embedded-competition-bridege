import json, os, statistics as st, subprocess, sys, time

path = sys.argv[1]
deadline = time.time() + float(sys.argv[2])
alerted = False
while time.time() < deadline:
    time.sleep(10)
    if not os.path.exists(path):
        continue
    try:
        lines = open(path).read().strip().split("\n")[-100:]
        recs = [json.loads(l) for l in lines if l.strip()]
    except Exception:
        continue
    if len(recs) < 50:
        continue
    d = [r["distance_cm_raw"] for r in recs if r.get("distance_cm_raw") is not None]
    if not d:
        continue
    frozen = st.pstdev(d) == 0.0
    hv = sum(1 for r in recs if r.get("heart_raw_valid"))
    if frozen and hv == 0:
        if not alerted:
            subprocess.Popen(["afplay", "/System/Library/Sounds/Sosumi.aiff"])
            subprocess.Popen(["say", "-v", "Yuna", "센서 고착입니다. 몸을 살짝 움직여 주세요."])
            alerted = True
    else:
        if alerted:
            subprocess.Popen(["afplay", "/System/Library/Sounds/Ping.aiff"])
            subprocess.Popen(["say", "-v", "Yuna", "복구되었습니다."])
        alerted = False
