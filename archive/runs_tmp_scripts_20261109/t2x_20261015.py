# -*- coding: utf-8 -*-
"""决定性判据:真列界必与每条横线相交;文字笔画不与横线相交。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

stem = "钻孔柱状图1042"
g = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
cj = json.loads((paths.CANDIDATE_COORD_DIR/f"{stem}.json").read_text(encoding="utf-8"))
hl = sorted({round(s["midy"]) for s in cj["lines"]
             if s["direction"] == "horizontal" and s["label"] == "high"})
hl = [y for y in hl if 700 <= y <= 19800]
# 去重:相邻 <=3px 合并
merged = []
for y in hl:
    if merged and y - merged[-1] <= 3: continue
    merged.append(y)
print("横线(high, 去重后) = %d 条, y范围 [%d,%d]" % (len(merged), merged[0], merged[-1]))

def cross_rate(pts, xmax=1400):
    """对每条横线,取该 y 处折线 x,检查该处是否有墨(±3px 窗内暗像素)"""
    pts = sorted(pts, key=lambda p: p[0])
    ys = np.array([p[0] for p in pts], float); xs = np.array([p[1] for p in pts], float)
    if ys[-1] - ys[0] < 300: return None
    hit = tot = 0
    for y in merged:
        if not (ys[0] + 5 <= y <= ys[-1] - 5): continue
        x = float(np.interp(y, ys, xs))
        if x > xmax: continue
        xi = int(round(x))
        if xi < 4 or xi > W - 5: continue
        tot += 1
        win = g[max(0,y-3):y+4, xi-3:xi+4]
        if win.size and win.min() < 140: hit += 1
    return (hit/float(tot), hit, tot) if tot >= 20 else None

chains = json.loads((R/"runs/tmp/t2chains_20261015.json").read_text(encoding="utf-8"))
print()
print("== 真实墨迹链 与横线相交率 ==")
print("链  y范围            x顶→x底      相交/横线   比率   定性")
rowsout = []
for n, c in enumerate(chains):
    r = cross_rate(c["pts"])
    if not r: continue
    ratio, hit, tot = r
    ys = [p[0] for p in c["pts"]]; xs = [p[1] for p in c["pts"]]
    kind = "真列界" if ratio >= 0.85 else ("部分" if ratio >= 0.5 else "非列界(文字/图案)")
    rowsout.append((ratio, n, ys[0], ys[-1], xs[0], xs[-1], hit, tot, kind))
for ratio, n, y0, y1, x0, x1, hit, tot, kind in sorted(rowsout, reverse=True):
    print("%-3d %-7.0f..%-7.0f %-5.0f→%-5.0f  %-5d/%-5d %.2f  %s" % (n, y0, y1, x0, x1, hit, tot, ratio, kind))

print()
print("== 对照组:已采用 sep_pts 各线 ==")
sp = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_分割线.json").read_text(encoding="utf-8"))
for i, ln in enumerate(sp["lines"]):
    r = cross_rate([(p[1], p[0]) for p in ln["pts"]])
    if not r:
        print("  [%d] %-14s 跨度不足" % (i, str(ln.get("name"))[:13])); continue
    ratio, hit, tot = r
    print("  [%d] %-14s 相交 %d/%d = %.2f" % (i, str(ln.get("name"))[:13], hit, tot, ratio))

print()
print("== 定点检验 x=137 (y=1000..4000) 是否有竖线 ==")
for y in range(1000, 4200, 400):
    row = g[y-1:y+2, 120:160].min(axis=0)
    dk = [120+i for i, v in enumerate(row) if v < 150]
    print("   y=%-5d 暗像素x: %s" % (y, dk if dk else "无"))
