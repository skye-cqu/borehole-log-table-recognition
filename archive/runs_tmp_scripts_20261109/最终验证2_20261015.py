# -*- coding: utf-8 -*-
import cv2, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R/"data"/"raw_images"; TR = R/"runs"/"table_reconstruct"

hm = json.load(open(TR/"钻孔柱状图1042_表头映射.json", encoding="utf-8"))
rd = json.load(open(TR/"钻孔柱状图1042_行判定.json", encoding="utf-8"))
g = cv2.imread(str(RAW/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
rows = [r for r in rd["rows"] if min(p[1] for p in r["poly"]) >= hm["band"][1]]
ys = [float(np.mean([p[1] for p in r["poly"]])) for r in rows]
print("##### 1042 逐行竖线覆盖(窗口±8px, 阈值0.55)")
cands = [551, 553, 633, 709, 753, 872, 912]
hit = {c:0 for c in cands}; n=0
for i in range(len(ys)-1):
    y0,y1 = int(ys[i])+6, int(ys[i+1])-6
    if y1-y0 < 8: continue
    n += 1
    frac = (g[y0:y1] < 150).mean(axis=0)
    for c in cands:
        w = frac[max(0,c-8):c+9]
        if w.size and w.max() >= 0.55: hit[c] += 1
for c in cands: print(f"    x≈{c:>4}: {hit[c]:>4}/{n} = {hit[c]/max(1,n):>3.0%}")

print("\n##### 1042 表头带 x[540,720] 超高倍")
c = g[750:915, 540:730]
c = cv2.resize(c, None, fx=5.0, fy=5.0, interpolation=cv2.INTER_CUBIC)
cv2.imwrite(str(R/"runs"/"tmp"/"z1042_band540.png"), c); print("  -> z1042_band540.png", c.shape)

print("\n##### 1032 左缘:逐行 x<105 区域墨迹左边界")
hm2 = json.load(open(TR/"钻孔柱状图1032_表头映射.json", encoding="utf-8"))
rd2 = json.load(open(TR/"钻孔柱状图1032_行判定.json", encoding="utf-8"))
g2 = cv2.imread(str(RAW/"钻孔柱状图1032.JPG"), cv2.IMREAD_GRAYSCALE)
rows2 = [r for r in rd2["rows"] if min(p[1] for p in r["poly"]) >= hm2["band"][1]]
ys2 = [float(np.mean([p[1] for p in r["poly"]])) for r in rows2]
lo = []
for i in range(len(ys2)-1):
    y0,y1 = int(ys2[i])+8, int(ys2[i+1])-8
    if y1-y0 < 12: continue
    band = g2[y0:y1, 0:100]
    colink = (band < 140).sum(axis=0)
    if colink.sum() < 20: lo.append((i+2, None)); continue
    lo.append((i+2, int(np.where(colink>0)[0].min())))
nz = [x for _,x in lo if x is not None]
print(f"  有墨行={len(nz)}  左缘=0 的行={sum(1 for x in nz if x==0)}  左缘<=3 的={sum(1 for x in nz if x<=3)}  最小={min(nz)} 中位={int(np.median(nz))}")
print("  前 12 行左缘:", lo[:12])
