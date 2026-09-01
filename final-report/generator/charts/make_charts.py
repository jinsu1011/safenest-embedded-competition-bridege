# -*- coding: utf-8 -*-
"""SafeNest 보고서 삽입용 실측 차트 생성. 원시 증거 파일에서만 값을 읽는다."""
import csv, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

# 출력은 저장소 상대 경로. 입력(원본 증거 패키지)은 저장소에 포함되지 않으므로
# SAFENEST_EVIDENCE 환경변수로 위치를 알려주어야 한다.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT  = os.path.join(ROOT, "previews")
IN   = os.environ.get("SAFENEST_EVIDENCE")
if not IN or not os.path.isdir(IN):
    raise SystemExit(
        "원본 증거 패키지 경로가 필요하다. 예:\n"
        "  SAFENEST_EVIDENCE=~/Desktop/SafeNest_Final_Report_Input python3 make_charts.py\n"
        "차트 PNG 3종은 previews/ 에 이미 생성되어 있으므로 보고서 빌드에는 필요 없다."
    )

for cand in ["AppleGothic", "Apple SD Gothic Neo", "NanumGothic"]:
    try:
        font_manager.findfont(cand, fallback_to_default=False)
        plt.rcParams["font.family"] = cand
        break
    except Exception:
        continue
plt.rcParams["axes.unicode_minus"] = False

NAVY, BLUE, RED, AMBER, GREY = "#1B2A41", "#2E6FB7", "#C0392B", "#E08A1E", "#6B7280"

# ---------- CO2 ----------
path = IN + "/03_Evidence/CO2_Data/2026-08-12_breath-rise-recovery_6min.csv"
t, ppm, gaps = [], [], []
with open(path, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
t0 = float(rows[0]["host_unix_s"])
for r in rows:
    ts = float(r["host_unix_s"]) - t0
    ok = (r["valid"].strip().lower() == "true") and r["co2_ppm"].strip() not in ("", "null", "None")
    if ok:
        t.append(ts); ppm.append(float(r["co2_ppm"]))
    else:
        t.append(ts); ppm.append(float("nan")); gaps.append(ts)

fig, ax = plt.subplots(figsize=(9.6, 3.9), dpi=230)
for g in gaps:
    ax.axvline(g, color=RED, alpha=0.20, lw=1.1, zorder=1)
ax.plot(t, ppm, color=BLUE, lw=2.2, zorder=3, label="CO₂ (ppm), valid=true")
ax.plot([], [], color=RED, alpha=0.5, lw=1.4, label="결측·무효 표본 %d개 (선을 잇지 않음)" % len(gaps))

vals = [(x, y) for x, y in zip(t, ppm) if y == y]
xmax, ymax = max(vals, key=lambda p: p[1])
xend, yend = vals[-1]
ax.annotate("최고 %d ppm" % ymax, xy=(xmax, ymax), xytext=(xmax + 45, ymax - 60),
            fontsize=11, color=NAVY, arrowprops=dict(arrowstyle="->", color=NAVY, lw=1.2))
ax.annotate("종료 %d ppm" % yend, xy=(xend, yend), xytext=(xend - 115, yend + 150),
            fontsize=11, color=NAVY, arrowprops=dict(arrowstyle="->", color=NAVY, lw=1.2))
ax.axhline(1500, color=AMBER, ls="--", lw=1.4, zorder=2)
ax.text(4, 1520, "1,500 ppm (실내공기질 관리법 시행규칙 별표2 기계환기 기준)",
        fontsize=9.5, color=AMBER, va="bottom")
ax.set_title("SCD40 실측: 호기 주입 상승·복귀 6분 세션 (2026-08-12, 표본 360개, 약 1초 주기)",
             fontsize=12.5, color=NAVY, pad=11)
ax.set_xlabel("세션 경과 시간 (초)", fontsize=11, color=NAVY)
ax.set_ylabel("CO₂ 농도 (ppm)", fontsize=11, color=NAVY)
ax.legend(fontsize=10, loc="upper left", frameon=False)
ax.grid(alpha=0.18, ls=":")
for s in ("top", "right"): ax.spines[s].set_visible(False)
ax.tick_params(labelsize=10, colors=GREY)
fig.tight_layout()
fig.savefig(OUT + "/chart_co2.png", bbox_inches="tight", facecolor="white")
plt.close(fig)
print("chart_co2.png  gaps=%d  max=%d  end=%d  n=%d" % (len(gaps), ymax, yend, len(rows)))

# ---------- mmWave ----------
bm = {}
with open(IN + "/03_Evidence/Test_Results/benchmark_summary.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        bm[r["dataset_id"]] = r

dist = [("0.6 m", "distance_0_6m"), ("0.9 m", "distance_0_9m"),
        ("1.2 m", "distance_1_2m"), ("1.5 m", "distance_1_5m")]
dv = [float(bm[k]["presence_detection_rate"]) for _, k in dist]
paced = [("12 rpm", "paced_12rpm"), ("15 rpm", "paced_15rpm"), ("20 rpm", "paced_20rpm")]
pv = [float(bm[k]["respiration_mae_rpm"]) for _, k in paced]

fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 3.5), dpi=230)
c1 = [BLUE, BLUE, RED, AMBER]
b = a1.bar([d[0] for d in dist], dv, color=c1, width=0.6)
for r, v in zip(b, dv):
    a1.text(r.get_x() + r.get_width()/2, v + 0.02, "%.3f" % v, ha="center", fontsize=11, color=NAVY)
a1.text(3, 0.42, "lock loss\n유효 창 0", ha="center", fontsize=10, color=RED)
a1.set_ylim(0, 1.18); a1.set_ylabel("재실 검출률", fontsize=11, color=NAVY)
a1.set_title("거리별 재실 검출률", fontsize=12, color=NAVY)

b2 = a2.bar([p[0] for p in paced], pv, color=[BLUE, BLUE, AMBER], width=0.5)
for r, v in zip(b2, pv):
    a2.text(r.get_x() + r.get_width()/2, v + 0.015, "%.3f" % v, ha="center", fontsize=11, color=NAVY)
a2.set_ylim(0, 0.70); a2.set_ylabel("호흡수 MAE (rpm)", fontsize=11, color=NAVY)
a2.set_title("페이스 호흡 구간 호흡수 오차", fontsize=12, color=NAVY)

for ax in (a1, a2):
    ax.grid(axis="y", alpha=0.18, ls=":")
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.tick_params(labelsize=10.5, colors=GREY)
fig.suptitle("mmWave 실측 로그 리플레이 정량 결과 (benchmark_summary.csv, 2026-08-08)",
             fontsize=12.5, color=NAVY, y=1.03)
fig.tight_layout()
fig.savefig(OUT + "/chart_mmwave.png", bbox_inches="tight", facecolor="white")
plt.close(fig)
print("chart_mmwave.png", dv, pv)

# ---------- 재해자 구성 도넛 ----------
fig, ax = plt.subplots(figsize=(3.4, 3.0), dpi=230)
w, d = 136, 202          # 사망 / 그 외 재해자 (고용노동부 보도자료 2024)
wedges, _ = ax.pie([w, d], startangle=90, counterclock=False,
                   colors=[RED, "#C9D2DC"], wedgeprops=dict(width=0.40, edgecolor="white", linewidth=2))
ax.text(0, 0.16, "재해자 338명 중", ha="center", va="center", fontsize=10.5, color=GREY)
ax.text(0, -0.16, "136명 사망", ha="center", va="center", fontsize=15.5, color=RED, fontweight="bold")
ax.legend(wedges, ["사망 136명", "그 외 재해자 202명"], loc="lower center",
          bbox_to_anchor=(0.5, -0.16), ncol=1, frameon=False, fontsize=10)
ax.set_aspect("equal")
fig.tight_layout()
fig.savefig(OUT + "/chart_victims.png", bbox_inches="tight", facecolor="white")
plt.close(fig)
print("chart_victims.png")
