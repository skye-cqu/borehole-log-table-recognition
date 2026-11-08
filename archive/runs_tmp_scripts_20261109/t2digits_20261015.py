# -*- coding: utf-8 -*-
"""1042:逐行分离"长竖线"与"数字簇",定位 真厚 列的真实左右界。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ink = (g < 128).astype(np.uint8)
ref = R/"runs/参考表_1015-1044_20261011/1015-1044/钻孔柱状图1042_llm_corrected.xlsx"
ws = load_workbook(ref).active

print("== 分割线.json 的 11 条线 ==")
d = json.loads((R/"runs/table_reconstruct/钻孔柱状图1042_分割线.json").read_text(encoding="utf-8"))
for i, L in enumerate(d["lines"]):
    pts = L.get("pts") or []
    if not pts: print("  [%d] 无 pts" % i); continue
    a = np.array(pts, float)
    print("  [%2d] kind=%-6s side=%-5s src=%-14s n=%-4d x=[%.0f,%.0f] y=[%.0f,%.0f]" % (
        i, L.get("kind"), str(L.get("side")), str(L.get("src")), len(a),
        a[:,0].min(), a[:,0].max(), a[:,1].min(), a[:,1].max()))

print()
print("== 逐行:长竖线 vs 数字簇连通域 ==")
print("%-4s %-13s %-7s %-24s %s" % ("行","y带","参考真厚","长竖线x(>=0.8带高)","数字簇bbox"))
for r in range(2, 30):
    yt, yb = ws.cell(row=r,column=2).value, ws.cell(row=r,column=3).value
    if not yt or not yb: continue
    yt, yb = int(yt), min(int(yb), g.shape[0])
    if yb-yt < 30: yb = min(yt+60, g.shape[0])
    if yb-yt < 30 or yt >= g.shape[0]: continue
    X0, X1 = 560, 960
    sub = ink[yt:yb, X0:X1]
    h, w = sub.shape
    # 竖线:列向覆盖率
    cov = sub.sum(axis=0) / float(h)
    lines = []
    i2 = 0
    while i2 < w:
        if cov[i2] >= 0.8:
            j = i2
            while j < w and cov[j] >= 0.8: j += 1
            lines.append(X0 + (i2+j-1)//2); i2 = j
        else: i2 += 1
    # 连通域:排除高度接近带高的(线)
    n, lab, st, _ = cv2.connectedComponentsWithStats(sub, 8)
    boxes = []
    for k in range(1, n):
        x, y, ww, hh, area = st[k]
        if hh >= 0.8*h and ww <= 8: continue          # 竖线
        if hh <= 0.55*h and hh >= 0.15*h and area >= 8 and ww <= 45:
            boxes.append((X0+x, X0+x+ww, area))
    boxes.sort()
    bbox = "-"
    if boxes:
        bbox = "[%d,%d] n=%d" % (boxes[0][0], boxes[-1][1], len(boxes))
    print("%-4d %-13s %-7s %-24s %s" % (r, "[%d,%d]"%(yt,yb), ws.cell(row=r,column=11).value,
          ",".join(str(v) for v in lines), bbox))
