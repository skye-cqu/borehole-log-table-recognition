# -*- coding: utf-8 -*-
"""1019/1032/1042/1023 表头带字墨块 x 区间 -> 与映射列归属对照(客观)。"""
import json
import cv2
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R/"data"/"raw_images"; TR = R/"runs"/"table_reconstruct"

def glyphs(gray, y0, y1, minw=8, thr=0.04):
    band = gray[int(y0):int(y1)]
    colink = (band < 140).mean(axis=0)
    isg = colink > thr
    runs = []; s = None
    for i, v in enumerate(isg):
        if v and s is None: s = i
        elif not v and s is not None:
            if i - s >= minw: runs.append((s, i))
            s = None
    if s is not None and len(isg)-s >= minw: runs.append((s, len(isg)))
    return runs

def label_of(x, seps, keep):
    for c in keep:
        a, b = c["x_in_band"]
        if a <= x < b: return c["name"]
    for c in keep: pass
    return "?"

for stem in ["钻孔柱状图1019", "钻孔柱状图1032", "钻孔柱状图1042", "钻孔柱状图1023"]:
    hm = json.load(open(TR/f"{stem}_表头映射.json", encoding="utf-8"))
    g = cv2.imread(str(RAW/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    b0, b1 = hm["band"]
    gs = glyphs(g, b0+8, b1-8)
    # 合并相邻近字块(同一竖排标签的多个字)
    merged = []
    for a, b in gs:
        if merged and a - merged[-1][1] <= 26: merged[-1] = (merged[-1][0], b)
        else: merged.append((a, b))
    print(f"##### {stem}")
    print("  映射列:", [(c["name"], round(c["x_in_band"][0]), round(c["x_in_band"][1])) for c in hm["keep"]])
    for a, b in merged:
        c = (a+b)//2
        print(f"    字块 x[{a:>4},{b:>4}] 中心{c:>4} -> {label_of(c, hm['sep_x_band'], hm['keep'])}")
    print()
