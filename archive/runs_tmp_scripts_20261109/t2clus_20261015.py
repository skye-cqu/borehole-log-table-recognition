# -*- coding: utf-8 -*-
"""1042:定位 倾角/真厚 数字簇的精确 x 范围。
若参考表自带裁剪图,用模板匹配反推真值列界(最客观)。"""
import sys, json
import numpy as np, cv2
from pathlib import Path
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

ref = R/"runs/参考表_1015-1044_20261011/1015-1044/钻孔柱状图1042_llm_corrected.xlsx"
ws = load_workbook(ref).active
crop_path = ws.cell(row=2, column=21).value      # 真厚裁剪图
print("参考表 真厚裁剪图路径:", crop_path)
if crop_path:
    cp = Path(str(crop_path))
    for cand in (R/cp, R/"runs"/cp, cp):
        print("   试:", cand, "存在=", cand.exists())
        if cand.exists():
            im = cv2.imread(str(cand), cv2.IMREAD_GRAYSCALE)
            print("   裁剪图尺寸:", None if im is None else im.shape)
            break

g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ink = (g < 128).astype(np.uint8)

print()
print("== 逐行连通域(x∈[540,1000],只列像文字的块) ==")
for r in range(5, 16):
    yt, yb = ws.cell(row=r,column=2).value, ws.cell(row=r,column=3).value
    if not yt or not yb: continue
    yt, yb = int(yt), min(int(yb), g.shape[0])
    if yb-yt < 30: yb = min(yt+60, g.shape[0])
    if yb-yt < 30 or yt >= g.shape[0]: continue
    X0, X1 = 540, 1000
    sub = ink[yt:yb, X0:X1]
    h, w = sub.shape
    n, lab, st, _ = cv2.connectedComponentsWithStats(sub, 8)
    items = []
    for k in range(1, n):
        x, y, ww, hh, area = st[k]
        if hh >= 0.8*h: continue                       # 长竖线
        if hh < 0.12*h or hh > 0.75*h: continue        # 太扁/太高
        if area < 12 or ww > 70: continue
        items.append((X0+x, X0+x+ww, int(hh), int(area)))
    items.sort()
    # 按 x 间距聚合
    groups = []
    for it in items:
        if groups and it[0] - groups[-1][-1][1] <= 22:
            groups[-1].append(it)
        else:
            groups.append([it])
    gs = ["[%d,%d]" % (gg[0][0], gg[-1][1]) for gg in groups]
    print("  行%-3d y=[%d,%d] h=%-4d 倾角=%-6s 真厚=%-6s 簇:%s" % (
        r, yt, yb, h, ws.cell(row=r,column=10).value, ws.cell(row=r,column=11).value, " ".join(gs)))
