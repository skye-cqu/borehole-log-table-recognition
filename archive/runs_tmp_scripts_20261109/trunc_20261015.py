# -*- coding: utf-8 -*-
import json, re
import cv2
import numpy as np
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R/"data"/"raw_images"; TR = R/"runs"/"table_reconstruct"; OUT = R/"runs"/"tmp"

def txt(v):
    if v is None: return ""
    if isinstance(v,str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)

print("##### 1) 参考表 1032 深度/层厚(前 22 行)")
wr = load_workbook(R/"runs"/"参考表_1015-1044_20261011"/"1015-1044"/"钻孔柱状图1032_llm_corrected.xlsx").active
hr = [txt(wr.cell(row=1,column=c).value) for c in range(1, wr.max_column+1)]
print("  hdr:", hr[:14])
for i in range(2, 24):
    print("   ", i, [txt(wr.cell(row=i,column=c).value) for c in (5,6,7,8,9,10,11)])

print()
print("##### 2) 1032 行带裁片:深度格(x 0..105) 是否数字被左缘切掉")
rd = json.load(open(TR/"钻孔柱状图1032_行判定.json", encoding="utf-8"))
hm = json.load(open(TR/"钻孔柱状图1032_表头映射.json", encoding="utf-8"))
rows = [r for r in rd["rows"] if min(p[1] for p in r["poly"]) >= hm["band"][1]]
g = cv2.imread(str(RAW/"钻孔柱状图1032.JPG"), cv2.IMREAD_GRAYSCALE)
w7 = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)["1032"]
targets = []
for idx, r in enumerate(rows):
    d = txt(w7.cell(row=idx+2, column=1).value)
    if d in ("15","62","0","45","60","50","20","2.8","2.2","14.39"):
        targets.append((idx, r, d))
print("  命中目标行:", [(i, d) for i,_,d in targets][:14])
tiles = []
for idx, r, d in targets[:8]:
    ys = [p[1] for p in r["poly"]]; y0, y1 = int(min(ys)), int(max(ys))
    pad = 6
    c = g[max(0,y0-pad):y1+pad, 0:112]
    c = cv2.copyMakeBorder(c, 3,3,3,3, cv2.BORDER_CONSTANT, value=255)
    c = cv2.resize(c, None, fx=2.2, fy=2.2, interpolation=cv2.INTER_CUBIC)
    c = cv2.cvtColor(c, cv2.COLOR_GRAY2BGR)
    cv2.putText(c, f"r{idx+2} v7={d}", (6, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0,0,220), 2)
    cv2.line(c, (3, 0), (3, c.shape[0]), (220,0,0), 2)
    tiles.append(c)
h = max(t.shape[0] for t in tiles); wtot = sum(t.shape[1] for t in tiles) + 8*len(tiles)
canvas = np.full((h+10, wtot, 3), 255, np.uint8)
x = 0
for t in tiles:
    canvas[5:5+t.shape[0], x:x+t.shape[1]] = t; x += t.shape[1]+8
cv2.imwrite(str(OUT/"d1032_depth_trunc.png"), canvas)
print("  -> d1032_depth_trunc.png", canvas.shape, "(蓝线=图像左缘 x=0)")
