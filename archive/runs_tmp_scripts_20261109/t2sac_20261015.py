# -*- coding: utf-8 -*-
"""以阶段4候选段(神圣源)统计每 x 的竖向墨迹总长,判定缺失列界 137/709。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

stem = "钻孔柱状图1042"
cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{stem}.json").read_text(encoding="utf-8"))
print("候选段总数 =", len(cj["lines"]))
lab = {}
for s in cj["lines"]:
    lab[(s["direction"], s["label"])] = lab.get((s["direction"], s["label"]), 0) + 1
print("分类统计:", lab)

H = 20644
# 竖向候选:direction=vertical,label=high,统计每 x 的覆盖 y 长度
def cover(bins, xlo, xhi, tol=6, label="high"):
    tot = np.zeros(xhi - xlo)
    n = np.zeros(xhi - xlo, dtype=int)
    for s in cj["lines"]:
        if s["direction"] != "vertical" or s["label"] != label:
            continue
        pts = s["points"]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        xm = float(np.mean(xs))
        if not (xlo - tol <= xm < xhi + tol):
            continue
        ln = max(ys) - min(ys)
        i0 = max(0, int(xm) - tol - xlo); i1 = min(xhi - xlo, int(xm) + tol + 1 - xlo)
        tot[i0:i1] += ln
        n[i0:i1] += 1
    return tot, n

for (xlo, xhi, title) in [(100, 300, "左区 100..300 (检验 137)"),
                          (580, 800, "中区 580..800 (检验 709)"),
                          (600, 1000, "右区 600..1000")]:
    tot, n = cover(None, xlo, xhi)
    print("\n== %s ==" % title)
    print("   x     覆盖y总长  段数")
    order = np.argsort(-tot)
    shown = 0
    used = set()
    for k in order:
        x = xlo + k
        if tot[k] <= 0: break
        if any(abs(x - u) <= 12 for u in used): continue
        used.add(x); shown += 1
        print("   %-6d %-10d %d" % (x, int(tot[k]), n[k]))
        if shown >= 14: break
    print("   覆盖率最高处: %d px (图高 %d)" % (int(tot.max()), H))
