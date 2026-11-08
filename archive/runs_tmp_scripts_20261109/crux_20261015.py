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

print("##### A) 1019 逐行对照(我方 v7 vs 参考表)")
w7 = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)["1019"]
h7 = [txt(w7.cell(row=1,column=c).value) for c in range(1, w7.max_column+1)]
wr = load_workbook(R/"runs"/"参考表_1015-1044_20261011"/"1015-1044"/"钻孔柱状图1019_llm_corrected.xlsx").active
hr = [txt(wr.cell(row=1,column=c).value) for c in range(1, wr.max_column+1)]
print("  v7 hdr:", h7)
print("  参考 hdr:", hr[:13])
print(f"  {'行':>3} | {'v7: ' + ' | '.join(h7):<70} | 参考(时代/层号/深/厚/采/倾/真厚)")
for i in range(2, 10):
    a = [txt(w7.cell(row=i,column=c).value) for c in range(1, w7.max_column+1)]
    b = [txt(wr.cell(row=i,column=c).value) for c in range(5, 12)]
    print(f"  {i:>3} | {' | '.join(x[:9] for x in a):<70} | {' | '.join(x[:9] for x in b)}")

print()
print("##### B) 1032 深度列左缘是否被扫描裁切 -> 裁片")
rd = json.load(open(TR/"钻孔柱状图1032_行判定.json", encoding="utf-8"))
hm = json.load(open(TR/"钻孔柱状图1032_表头映射.json", encoding="utf-8"))
rows = [r for r in rd["rows"] if min(p[1] for p in r["poly"]) >= hm["band"][1]]
g = cv2.imread(str(RAW/"钻孔柱状图1032.JPG"), cv2.IMREAD_GRAYSCALE)
print("  图像宽高:", g.shape[1], g.shape[0])
for idx in (0, 1, 2, 3):
    r = rows[idx]
    ys = [p[1] for p in r["poly"]]; y0, y1 = int(min(ys)), int(max(ys))
    c = g[y0:y1+1, 0:110]
    # 左缘墨迹:第一列像素是否已有墨
    ink = (c < 140)
    leftcol = ink[:, 0].mean()
    firstink = [int(np.argmax(ink[y])) if ink[y].any() else -1 for y in range(0, ink.shape[0], 4)]
    print(f"  行{idx+2} y[{y0},{y1}] 高={y1-y0+1} 左缘列墨率={leftcol:.2f} 各行首个墨像素x(抽样)={firstink[:14]}")
    c2 = cv2.resize(c, None, fx=3.0, fy=3.0, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(str(OUT/f"d1032_depth_r{idx+2}.png"), c2)
print("  ->", [f"d1032_depth_r{i+2}.png" for i in range(4)])
