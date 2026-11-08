# -*- coding: utf-8 -*-
"""客观量尺:在原图表头带内直接找竖线墨峰,与表头映射的 sep_x_band / sep_pts 对照。"""
import cv2, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R / "data" / "raw_images"
TR = R / "runs" / "table_reconstruct"

def peaks(dark, th=0.6, minsep=8):
    idx = [i for i in range(2, len(dark)-2)
           if dark[i] >= th and dark[i] == dark[max(0,i-3):i+4].max()]
    out = []
    for i in idx:
        if out and i - out[-1][0] <= minsep:
            if dark[i] > dark[out[-1][0]]:
                out[-1] = (i, dark[i])
        else:
            out.append((i, dark[i]))
    return out

for stem in ["钻孔柱状图1032", "钻孔柱状图1042", "钻孔柱状图1019", "钻孔柱状图1033"]:
    img = cv2.imread(str(RAW / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    hm = json.load(open(TR / f"{stem}_表头映射.json", encoding="utf-8"))
    b0, b1 = hm["band"]
    H, W = img.shape
    print(f"##### {stem} img={W}x{H} band={hm['band']}")
    # 表头带:避开上下横框,取中间 60%
    m0 = int(b0 + (b1-b0)*0.25); m1 = int(b0 + (b1-b0)*0.75)
    band = img[m0:m1, :]
    dark = (band < 150).mean(axis=0)
    pk = peaks(dark)
    print("  原图竖墨峰(x, 暗占比):", [(x, round(f,2)) for x,f in pk])
    print("  hm.sep_x_band        :", [round(v,1) for v in hm["sep_x_band"]])
    # sep_pts 在 y=m0/m1 处的 x
    ymid = (m0+m1)/2
    pts = hm.get("sep_pts")
    if pts:
        xs = [round(float(np.interp(ymid, p["ys"], p["xs"])),1) for p in pts]
        print("  hm.sep_pts@ymid      :", xs)
    print("  keep:", [(c["name"], round(c["x_in_band"][0],1), round(c["x_in_band"][1],1)) for c in hm["keep"]])
    print("  drop:", [(c["name"], round(c["x_in_band"][0],1), round(c["x_in_band"][1],1)) for c in hm["drop_columns"]])
    print()
