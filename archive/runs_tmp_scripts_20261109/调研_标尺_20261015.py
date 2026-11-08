# -*- coding: utf-8 -*-
"""列区间标尺图:把表头带裁出来,画上真实竖墨峰(红)与表头映射 sep(绿),带 x 刻度。"""
import cv2, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R / "data" / "raw_images"; TR = R / "runs" / "table_reconstruct"; OUT = R / "runs" / "tmp"

def peaks(dark, th=0.55, minsep=8):
    idx = [i for i in range(2, len(dark)-2) if dark[i] >= th and dark[i] == dark[max(0,i-3):i+4].max()]
    out = []
    for i in idx:
        if out and i - out[-1][0] <= minsep:
            if dark[i] > dark[out[-1][0]]: out[-1] = (i, dark[i])
        else: out.append((i, dark[i]))
    return out

for stem in ["钻孔柱状图1032", "钻孔柱状图1042", "钻孔柱状图1019"]:
    img = cv2.imread(str(RAW / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    hm = json.load(open(TR / f"{stem}_表头映射.json", encoding="utf-8"))
    b0, b1 = hm["band"]
    H, W = img.shape
    y0, y1 = max(0, b0-30), min(H, b1+120)
    crop = img[y0:y1].copy()
    dark = (img[int(b0+(b1-b0)*0.25):int(b0+(b1-b0)*0.75)] < 150).mean(axis=0)
    pk = peaks(dark)
    col = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    for x, f in pk:                                   # 真竖墨峰=红
        cv2.line(col, (x, 0), (x, col.shape[0]), (0, 0, 255), 2)
    for i, x in enumerate(hm["sep_x_band"]):          # 映射 sep=绿
        x = int(round(x))
        cv2.line(col, (x, 0), (x, col.shape[0]), (0, 200, 0), 2)
        cv2.putText(col, f"s{i}", (x+3, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 160, 0), 2)
    for x in range(0, W, 200):                        # 刻度=蓝
        cv2.line(col, (x, 0), (x, 14), (255, 0, 0), 2)
        cv2.putText(col, str(x), (x+2, 46), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
    sc = 1600.0 / W
    col = cv2.resize(col, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(OUT / f"标尺_{stem}_表头.png"), col)
    print(stem, "->", col.shape, "真峰", [x for x,_ in pk], "映射", [round(v,1) for v in hm["sep_x_band"]])
