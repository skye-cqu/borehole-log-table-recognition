# -*- coding: utf-8 -*-
"""1042 决定性判定:[632.7,912.0] 是 1 列还是 2 列?
判据:逐行带统计 x 的纵向墨量,找**贯穿整行带高度**的竖线(真列界),
      再看数字字形簇落在哪两条线之间。"""
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

print("逐行带:x∈[600,960] 内贯穿 >=85% 带高的竖线,以及数字簇范围")
print("%-4s %-13s %-8s %-26s %s" % ("行","y带","参考真厚","贯穿竖线 x(>=85%带高)","数字簇 x范围"))
for r in range(2, 26):
    yt, yb = ws.cell(row=r,column=2).value, ws.cell(row=r,column=3).value
    if not yt or not yb: continue
    yt, yb = int(yt), min(int(yb), g.shape[0])
    if yb-yt < 30: yb = min(yt+60, g.shape[0])
    if yb-yt < 30 or yt >= g.shape[0]: continue
    sub = ink[yt:yb, 600:960]
    h = sub.shape[0]
    cs = sub.sum(axis=0)
    lines = []
    i = 0
    while i < len(cs):
        if cs[i] >= 0.85*h:
            j = i
            while j < len(cs) and cs[j] >= 0.85*h: j += 1
            lines.append(600 + (i+j-1)//2); i = j
        else: i += 1
    # 数字簇:在 [632,912] 内找墨,排除竖线列
    nummask = np.ones(360, bool)
    for L in lines: nummask[max(0,L-600-4):L-600+5] = False
    cols = cs.copy(); cols[~nummask] = 0
    nz = np.where(cols > 0)[0]
    if len(nz):
        # 只取 632..912 之间
        nz = nz[(nz+600 >= 630) & (nz+600 <= 915)]
    rng = "[%d,%d]" % (600+nz.min(), 600+nz.max()) if len(nz) else "-"
    tt = ws.cell(row=r,column=11).value
    print("%-4d %-13s %-8s %-26s %s" % (r, "[%d,%d]"%(yt,yb), tt,
          ",".join(str(v) for v in lines), rng))
