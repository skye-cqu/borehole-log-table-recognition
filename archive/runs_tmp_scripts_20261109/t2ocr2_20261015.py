# -*- coding: utf-8 -*-
"""1042 决定性检验(12行,快):OCR 每段的 x 范围,与参考表 倾角/真厚 对照。"""
import sys
import numpy as np, cv2
from pathlib import Path
from openpyxl import load_workbook
from rapidocr_onnxruntime import RapidOCR
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ref = R/"runs/参考表_1015-1044_20261011/1015-1044/钻孔柱状图1042_llm_corrected.xlsx"
ws = load_workbook(ref).active
ocr = RapidOCR()
X0, X1 = 600, 980
print("%-4s %-12s %-6s %-6s | %s" % ("行","y带","参考倾角","参考真厚","OCR段(text@x范围)"))
for r in [2,5,6,7,8,9,10,11,13,14,16,19,21,23,26,29]:
    yt, yb = int(ws.cell(row=r,column=2).value), int(ws.cell(row=r,column=3).value)
    yb = min(yb, g.shape[0])
    if yb-yt < 30: yb = min(yt+60, g.shape[0])
    if yt >= g.shape[0]: continue
    res, _ = ocr(g[yt:yb, X0:X1])
    segs = []
    for it in (res or []):
        box, txt = it[0], it[1]
        xs = [p[0] for p in box]
        segs.append((int(min(xs))+X0, int(max(xs))+X0, txt))
    segs.sort()
    print("%-4d %-12s %-6s %-6s | %s" % (r, "[%d,%d]"%(yt,yb),
        ws.cell(row=r,column=10).value, ws.cell(row=r,column=11).value,
        "  ".join("%s@[%d,%d]" % (t,a,b) for a,b,t in segs)))
