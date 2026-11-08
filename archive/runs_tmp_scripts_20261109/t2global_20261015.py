# -*- coding: utf-8 -*-
"""1042 决定性测量:跨全部行带聚类竖线,得到全局列界集合。"""
import sys, json
import numpy as np, cv2
from pathlib import Path
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ink = (g < 128).astype(np.uint8)
H, W = g.shape
ref = R/"runs/参考表_1015-1044_20261011/1015-1044/钻孔柱状图1042_llm_corrected.xlsx"
ws = load_workbook(ref).active

X0, X1 = 400, 1100
allx = []
nbands = 0
for r in range(2, ws.max_row+1):
    yt, yb = ws.cell(row=r,column=2).value, ws.cell(row=r,column=3).value
    if not yt or not yb: continue
    yt, yb = int(yt), min(int(yb), H)
    if yb-yt < 45 or yt >= H: continue
    # 内缩避开横线
    a, b = yt+6, yb-6
    if b-a < 30: continue
    sub = ink[a:b, X0:X1]
    cov = sub.sum(axis=0) / float(b-a)
    nbands += 1
    i = 0
    while i < len(cov):
        if cov[i] >= 0.85:
            j = i
            while j < len(cov) and cov[j] >= 0.85: j += 1
            allx.append((X0 + (i+j-1)//2, r, j-i))
            i = j
        else:
            i += 1
print("扫描 %d 个行带, 命中竖线 %d 次" % (nbands, len(allx)))

allx.sort()
groups = []
for x, r, w in allx:
    if groups and x - groups[-1][-1][0] <= 12:
        groups[-1].append((x, r, w))
    else:
        groups.append([(x, r, w)])
print()
print("== 跨行带聚类后的全局竖线 ==")
print("序号  x范围        中位x  命中行带数  覆盖%   宽中位")
for gi, grp in enumerate(groups):
    xs = [t[0] for t in grp]
    wd = [t[2] for t in grp]
    rows_hit = len(set(t[1] for t in grp))
    print("%-5d [%4d,%4d]  %-6.0f %-11d %-7.0f %.0f" % (
        gi, min(xs), max(xs), float(np.median(xs)), rows_hit,
        100.0*rows_hit/nbands, float(np.median(wd))))

print()
print("== 柱状花纹列的实际 x 范围(逐行带找花纹/砖块) ==")
for r in (5, 6, 8, 10, 13, 16):
    yt, yb = ws.cell(row=r,column=2).value, ws.cell(row=r,column=3).value
    if not yt or not yb: continue
    yt, yb = int(yt), min(int(yb), H)
    if yb-yt < 45: continue
    sub = ink[yt+6:yb-6, 560:1000]
    cov = sub.sum(axis=0) / float(sub.shape[0])
    nz = np.where(cov > 0.05)[0]
    print("  行%-3d 参考真厚=%-6s 柱状=%-6s 墨迹x=[%d,%d]" % (
        r, ws.cell(row=r,column=11).value, ws.cell(row=r,column=12).value,
        560+nz.min() if len(nz) else -1, 560+nz.max() if len(nz) else -1))
