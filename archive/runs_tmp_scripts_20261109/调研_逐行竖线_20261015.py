# -*- coding: utf-8 -*-
"""逐行带实测竖线 x,与表头映射 sep_pts 对照(客观:只在行带内量竖墨)。"""
import cv2, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R / "data" / "raw_images"; TR = R / "runs" / "table_reconstruct"

def vlines(gray, y0, y1, th=0.55, minsep=10):
    band = gray[int(y0):int(y1)]
    if band.shape[0] < 6: return []
    frac = (band < 150).mean(axis=0)
    idx = [i for i in range(2, len(frac)-2) if frac[i] >= th and frac[i] == frac[max(0,i-3):i+4].max()]
    out = []
    for i in idx:
        if out and i - out[-1][0] <= minsep:
            if frac[i] > frac[out[-1][0]]: out[-1] = (i, float(frac[i]))
        else: out.append((i, float(frac[i])))
    return out

for stem in ["钻孔柱状图1032", "钻孔柱状图1042"]:
    hm = json.load(open(TR / f"{stem}_表头映射.json", encoding="utf-8"))
    rd = json.load(open(TR / f"{stem}_行判定.json", encoding="utf-8"))
    b0, b1 = hm["band"]
    seps = hm["sep_pts"]
    rows = [r for r in rd["rows"] if min(p[1] for p in r["poly"]) >= b0]
    ys = [float(np.mean([p[1] for p in r["poly"]])) for r in rows]
    print(f"##### {stem} 行数={len(rows)} 表头带={hm['band']}")
    print("映射 sep(表头带内 x):", [round(v,1) for v in hm["sep_x_band"]])
    print(f"{'行':>4} {'y0':>7} {'y1':>7} | 实测竖线 x (暗占比) | 映射@ymid")
    for i in range(min(len(ys)-1, 14)):
        y0, y1 = ys[i]+4, ys[i+1]-4
        vl = vlines(RAW and cv2.imread(str(RAW/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE), y0, y1)
        ym = (ys[i]+ys[i+1])/2
        mx = [round(float(np.interp(ym, p["ys"], p["xs"])),1) for p in seps]
        print(f"{i+2:>4} {y0:>7.0f} {y1:>7.0f} | " + " ".join(f"{x}({f:.2f})" for x,f in vl))
        print(f"{'':>4} {'':>7} {'':>7} | 映射: {mx}")
    print()
