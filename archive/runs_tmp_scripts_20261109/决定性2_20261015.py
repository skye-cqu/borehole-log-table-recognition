# -*- coding: utf-8 -*-
"""① 1023 表头高度/行线实测;② 1042 分割线.json 里有没有 x≈709 的列线。"""
import cv2, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R/"data"/"raw_images"; TR = R/"runs"/"table_reconstruct"; OUT = R/"runs"/"tmp"

# --- 1023 横线 ---
g = cv2.imread(str(RAW/"钻孔柱状图1023.JPG"), cv2.IMREAD_GRAYSCALE)
print("1023 shape:", g.shape)
sub = g[400:1500, 150:2500]
dark = (sub < 140).mean(axis=1)
lines = [i+400 for i in range(3, len(dark)-3)
         if dark[i] > 0.6 and dark[i] == dark[i-3:i+4].max()]
merged = []
for y in lines:
    if merged and y - merged[-1] <= 6: continue
    merged.append(y)
print("1023 y400-1500 横线:", merged)

# --- 1042 分割线.json ---
d = json.load(open(TR/"钻孔柱状图1042_分割线.json", encoding="utf-8"))
print("\n1042 分割线.json lines:", len(d["lines"]))
for ln in d["lines"]:
    pts = ln.get("pts") or []
    if not pts: continue
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    kind = ln.get("kind"); idx = ln.get("index")
    print(f"  kind={kind} index={idx} n={len(pts)} x=[{min(xs):.0f},{max(xs):.0f}] xmed={np.median(xs):.0f} y=[{min(ys):.0f},{max(ys):.0f}]")
