# -*- coding: utf-8 -*-
"""决定性:
① 1042 x≈709 是否逐行持续存在的列分隔线(真列界) vs 局部图案;
② 1032 深度列数值左侧是否被扫描裁切(看墨迹是否贴图左缘 x=0)。"""
import cv2, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R/"data"/"raw_images"; TR = R/"runs"/"table_reconstruct"; OUT = R/"runs"/"tmp"

def rows_of(stem):
    hm = json.load(open(TR/f"{stem}_表头映射.json", encoding="utf-8"))
    rd = json.load(open(TR/f"{stem}_行判定.json", encoding="utf-8"))
    rows = [r for r in rd["rows"] if min(p[1] for p in r["poly"]) >= hm["band"][1]]
    ys = [float(np.mean([p[1] for p in r["poly"]])) for r in rows]
    return hm, ys

# ===== ① 1042 =====
hm, ys = rows_of("钻孔柱状图1042")
g = cv2.imread(str(RAW/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
print("##### 1042 逐行竖线持续率(x 候选)")
cands = [555, 633, 637, 709, 713, 753, 872, 912]
hit = {c: 0 for c in cands}
n = 0
for i in range(len(ys)-1):
    y0, y1 = int(ys[i])+6, int(ys[i+1])-6
    if y1 - y0 < 8: continue
    n += 1
    band = g[y0:y1]
    frac = (band < 150).mean(axis=0)
    for c in cands:
        w = frac[max(0,c-4):c+5]
        if w.size and w.max() >= 0.85: hit[c] += 1
print(f"  可比行数={n}")
for c in cands:
    print(f"    x≈{c:>4}: 覆盖 {hit[c]:>4}/{n} = {hit[c]/max(1,n):.0%}")

# ===== ② 1032 深度列左缘 =====
hm2, ys2 = rows_of("钻孔柱状图1032")
g2 = cv2.imread(str(RAW/"钻孔柱状图1032.JPG"), cv2.IMREAD_GRAYSCALE)
print("\n##### 1032 深度列[0,105] 逐行墨迹左缘(x<40 即疑似被裁)")
edge = 0
tot = 0
samples = []
for i in range(len(ys2)-1):
    y0, y1 = int(ys2[i])+8, int(ys2[i+1])-8
    if y1 - y0 < 12: continue
    band = g2[y0:y1, 0:105]
    colink = (band < 140).sum(axis=0)
    if colink.sum() < 20: continue        # 空格
    tot += 1
    xs = np.where(colink > 0)[0]
    lo = int(xs.min())
    if lo <= 40:
        edge += 1
        if len(samples) < 8: samples.append((i+2, lo, int(xs.max())))
print(f"  有墨行={tot}  墨迹左缘≤40px 的行={edge} ({edge/max(1,tot):.0%})")
print("  样例(行, 左缘x, 右缘x):", samples)
