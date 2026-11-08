# -*- coding: utf-8 -*-
"""数据区放大裁片:画上表头映射列界(绿)+行界(红),看数据到底落在哪一列。"""
import cv2, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R / "data" / "raw_images"; TR = R / "runs" / "table_reconstruct"; OUT = R / "runs" / "tmp"

def load(stem):
    hm = json.load(open(TR / f"{stem}_表头映射.json", encoding="utf-8"))
    rd = json.load(open(TR / f"{stem}_行判定.json", encoding="utf-8"))
    return hm, rd

for stem, x0, x1, ny in [("钻孔柱状图1032", 0, 760, 12), ("钻孔柱状图1042", 0, 1000, 10)]:
    hm, rd = load(stem)
    img = cv2.imread(str(RAW / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    b0, b1 = hm["band"]
    rows = [r for r in rd["rows"] if min(p[1] for p in r["poly"]) >= b0]
    ys = [int(min(p[1] for p in r["poly"])) for r in rows[:ny+1]]
    y0, y1 = b0 - 20, min(img.shape[0], ys[-1] + 20)
    crop = img[y0:y1, x0:x1].copy()
    col = cv2.cvtColor(crop, cv2.COLOR_GRAY2BGR)
    for i, x in enumerate(hm["sep_x_band"]):
        x = int(round(x)) - x0
        if 0 <= x < col.shape[1]:
            cv2.line(col, (x, 0), (x, col.shape[0]), (0, 200, 0), 2)
            cv2.putText(col, f"s{i}", (x+3, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 160, 0), 2)
    for y in ys:
        cv2.line(col, (0, y - y0), (col.shape[1], y - y0), (0, 0, 255), 2)
    sc = 2.0 if col.shape[1] < 1000 else 1.5
    col = cv2.resize(col, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
    # 竖排输出,便于一次看完
    cv2.imwrite(str(OUT / f"数据区_{stem}.png"), col)
    print(stem, "->", col.shape, "行界y", ys)
