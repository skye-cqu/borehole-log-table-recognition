# -*- coding: utf-8 -*-
"""1042 x~709 候选链的连续性:y 覆盖、缺口、与墨迹折线的一致性。"""
import json, sys
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
STEM = "钻孔柱状图1042"
cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{STEM}.json").read_text(encoding="utf-8"))
H = 20644
segs = []
for s in cj["lines"]:
    if s["direction"] != "vertical" or s["label"] != "high": continue
    pts = s["points"]; mx = float(np.mean([p[0] for p in pts]))
    if abs(mx - 709) > 45: continue
    ys = [p[1] for p in pts]
    segs.append((float(min(ys)), float(max(ys)), mx, s.get("final_score"), s.get("id")))
segs.sort()
print("段数 =", len(segs))
# 贪心链:按 y 升序,若与当前链尾重叠或缺口 < 60 则续链
chains, cur = [], None
for a, b, mx, sc, i in segs:
    if cur is None: cur = {"y0": a, "y1": b, "xs": [(mx, a, b)], "ids": [i], "score": [sc]}
    elif a <= cur["y1"] + 60:
        cur["y1"] = max(cur["y1"], b); cur["xs"].append((mx, a, b)); cur["ids"].append(i); cur["score"].append(sc)
    else:
        chains.append(cur); cur = {"y0": a, "y1": b, "xs": [(mx, a, b)], "ids": [i], "score": [sc]}
if cur: chains.append(cur)
chains.sort(key=lambda c: -(c["y1"]-c["y0"]))
print("\n按缺口<60px 链出的链(跨度降序):")
for c in chains[:8]:
    span = c["y1"]-c["y0"]
    xs = [x for x, _, _ in c["xs"]]
    print("  y=[%6.0f,%6.0f] 跨度=%6.0f 段=%-4d x=%.0f..%.0f 覆盖=%.3f" % (
        c["y0"], c["y1"], span, len(c["xs"]), min(xs), max(xs), span/H))
# 最大链的逐段 x(y) 剖面
c = chains[0]
print("\n最大链 x(y) 剖面:")
for y in range(int(c["y0"]), int(c["y1"])+1, 1500):
    cand = [(x, a, b) for x, a, b in c["xs"] if a <= y <= b]
    if cand:
        print("   y=%6d x=%.1f (段内 %d)" % (y, np.mean([x for x,_,_ in cand]), len(cand)))
# 与墨迹折线对照
p = R/"runs/tmp/t2_709poly_20261015.npy"
if p.exists():
    arr = np.load(str(p))
    print("\n墨迹折线: 采样=%d y=[%d,%d]" % (len(arr), arr[0,0], arr[-1,0]))
    for y in range(int(c["y0"]), int(c["y1"])+1, 1500):
        k = np.argmin(np.abs(arr[:,0]-y))
        print("   y=%6d 墨迹x=%.1f" % (arr[k,0], arr[k,1]))
