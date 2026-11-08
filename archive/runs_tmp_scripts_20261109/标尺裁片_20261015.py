# -*- coding: utf-8 -*-
"""列界标尺裁片:在任意区域画上 表头映射sep(绿) + 实测竖墨峰(红),带 x 刻度。
用法: python 标尺裁片.py <stem> <x0> <x1> <y0> <y1> <scale> <out.png> [--nomap|--nomeas]
"""
import sys
import cv2, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R / "data" / "raw_images"; TR = R / "runs" / "table_reconstruct"

def peaks(gray, y0, y1, th=0.55, minsep=8):
    band = gray[int(y0):int(y1)]
    if band.shape[0] < 4: return []
    frac = (band < 150).mean(axis=0)
    idx = [i for i in range(2, len(frac)-2) if frac[i] >= th and frac[i] == frac[max(0,i-3):i+4].max()]
    out = []
    for i in idx:
        if out and i - out[-1][0] <= minsep:
            if frac[i] > frac[out[-1][0]]: out[-1] = (i, float(frac[i]))
        else: out.append((i, float(frac[i])))
    return out

stem, x0, x1, y0, y1, sc, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), float(sys.argv[6]), sys.argv[7]
flags = sys.argv[8:]
gray = cv2.imread(str(RAW / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
hm = json.load(open(TR / f"{stem}_表头映射.json", encoding="utf-8"))
crop = gray[y0:y1, x0:x1]
col = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
if "--nomeas" not in flags:
    for x, f in peaks(gray, y0, y1):
        if x0 <= x < x1:
            cv2.line(col, (x-x0, 0), (x-x0, col.shape[0]), (0,0,255), 1)
if "--nomap" not in flags:
    for i, x in enumerate(hm["sep_x_band"]):
        xi = int(round(x))
        if x0 <= xi < x1:
            cv2.line(col, (xi-x0, 0), (xi-x0, col.shape[0]), (0,200,0), 1)
            cv2.putText(col, f"s{i}", (xi-x0+2, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,150,0), 2)
for x in range(int(np.ceil(x0/50.0))*50, x1, 50):
    cv2.line(col, (x-x0, 0), (x-x0, 8), (255,0,0), 1)
    cv2.putText(col, str(x), (x-x0+2, col.shape[0]-6), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255,0,0), 1)
if sc != 1.0:
    col = cv2.resize(col, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
cv2.imwrite(str(R / "runs" / "tmp" / out), col)
print(out, col.shape, "实测峰:", [x for x,_ in peaks(gray, y0, y1)])
