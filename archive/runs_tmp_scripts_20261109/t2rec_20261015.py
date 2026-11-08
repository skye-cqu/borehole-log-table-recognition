# -*- coding: utf-8 -*-
"""验证 _recover_sep_pts:从表头竖笔锚点,沿阶段4 候选段贪心接续出该界折线。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
STEM = "钻孔柱状图1042"

def recover(stem, x_anchor, y_top, y_bot, tol=30.0, gap_max=160.0):
    cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
    frags = []
    for s in cj["lines"]:
        if s["direction"] != "vertical" or s["label"] != "high": continue
        p = np.asarray(s["points"], float)
        if len(p) < 2: continue
        p = p[np.argsort(p[:, 1])]
        if p[-1, 1] < y_top - 200 or p[0, 1] > y_bot + 200: continue
        frags.append((float(p[0, 1]), p))
    frags.sort(key=lambda t: t[0])
    xs, ys, cy, cx, used = [], [], float(y_top), float(x_anchor), set()
    while True:
        best, bestd = None, None
        for k, (yy, p) in enumerate(frags):
            if k in used or yy > cy + gap_max or yy < cy - 40: continue
            if p[-1, 1] < cy: continue
            xi = float(np.interp(cy, p[:, 1], p[:, 0])) if p[0, 1] <= cy <= p[-1, 1] else float(p[0, 0])
            d = abs(xi - cx)
            if d <= tol and (bestd is None or d < bestd): best, bestd = k, d
        if best is None: break
        used.add(best); p = frags[best][1]
        sel = p[p[:, 1] > cy]
        for x, y in sel: xs.append(float(x)); ys.append(float(y))
        if len(sel): cx, cy = float(sel[-1, 0]), float(sel[-1, 1])
        else: cy = float(p[-1, 1])
    return np.array(xs), np.array(ys)

g = cv2.imread(str(paths.RAW_DIR/f"{STEM}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
dark = (g < 150)
hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{STEM}_表头映射.json").read_text(encoding="utf-8"))
Y0, Y1 = hm["band"][0], 19745

for anchor in (709, 633):
    xs, ys = recover(STEM, anchor, Y0, Y1)
    if len(ys) == 0:
        print("锚 %d: 接不出" % anchor); continue
    span = ys[-1] - ys[0]
    hit = sum(1 for x, y in zip(xs, ys) if dark[int(y), max(0,int(x)-3):int(x)+4].any())
    print("锚=%-4d 段点=%-5d y=[%.0f,%.0f] 覆盖=%.3f  x=%.0f..%.0f  墨迹命中=%.3f" % (
        anchor, len(ys), ys[0], ys[-1], span/(Y1-Y0), xs.min(), xs.max(), hit/len(ys)))
    print("   剖面:", " ".join("y%d:x%.0f" % (yy, np.interp(yy, ys, xs))
                              for yy in range(int(ys[0]), int(ys[-1])+1, 2000)))
