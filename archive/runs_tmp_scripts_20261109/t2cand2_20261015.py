# -*- coding: utf-8 -*-
"""1042 决定性:表头带内所有竖笔的精确 y 跨度 + 阶段4候选里是否有 真厚|柱状 界。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ink = (g < 140).astype(np.uint8)
H, W = g.shape

print("== 表头区 y∈[700,975] 内每 x 的墨迹 y-runs(只列最长run>=60) ==")
for x in range(540, 1000):
    col = ink[700:975, x]
    runs = []
    s = None
    for i, v in enumerate(col):
        if v and s is None: s = i
        elif not v and s is not None:
            runs.append((700+s, 700+i)); s = None
    if s is not None: runs.append((700+s, 975))
    if not runs: continue
    long_runs = [r for r in runs if r[1]-r[0] >= 60]
    if long_runs:
        print("   x=%-5d %s" % (x, " ".join("[%d,%d](%d)" % (a,b,b-a) for a,b in long_runs)))

print()
print("== 阶段4 候选(正确键 points):表头区竖线 ==")
d = json.loads((paths.CANDIDATE_COORD_DIR/"钻孔柱状图1042.json").read_text(encoding="utf-8"))
vs = [s for s in d["lines"] if s.get("direction") == "vertical"]
print("竖线候选:", len(vs))
hits = []
for s in vs:
    pts = np.array(s.get("points") or [], float)
    if len(pts) < 2: continue
    top = pts[pts[:,1] < 1150]
    if len(top) == 0: continue
    xm = float(np.median(top[:,0]))
    if 540 <= xm <= 1000:
        hits.append((xm, s.get("id"), s.get("label"), len(pts),
                     float(pts[:,0].min()), float(pts[:,0].max()),
                     float(pts[:,1].min()), float(pts[:,1].max()),
                     float(s.get("length") or 0), float(s.get("final_score") or 0)))
hits.sort()
print("表头区(x∈[540,1000])竖线候选 %d 条:" % len(hits))
for xm, i, lb, n, x0, x1, y0, y1, ln, fs in hits:
    print("   x中位=%-6.0f id=%-8s label=%-9s n=%-4d x=[%.0f,%.0f] y=[%.0f,%.0f] len=%.0f score=%.2f" % (
        xm, i, lb, n, x0, x1, y0, y1, ln, fs))

print()
print("== 阶段4 全部竖线候选按 x 中位分箱(表头 y<1200) ==")
allx = []
for s in vs:
    pts = np.array(s.get("points") or [], float)
    if len(pts) < 2: continue
    top = pts[pts[:,1] < 1200]
    if len(top) == 0: continue
    allx.append(float(np.median(top[:,0])))
allx = np.array(sorted(allx))
if len(allx):
    print("   总数=%d  x范围=[%.0f,%.0f]" % (len(allx), allx.min(), allx.max()))
    hist, edges = np.histogram(allx, bins=np.arange(500, 1050, 10))
    for h, e in zip(hist, edges):
        if h: print("      x=[%d,%d) : %s" % (e, e+10, "#"*min(h,60) + (" %d"%h if h>60 else "")))
