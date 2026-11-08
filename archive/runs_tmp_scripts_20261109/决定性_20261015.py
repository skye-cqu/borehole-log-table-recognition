# -*- coding: utf-8 -*-
"""决定性测量:
① 1042/1032/1023 的竖线"全表高覆盖率"(区分真列分隔线 vs 局部笔画/图案);
② 1023 数据区两列的实际内容(超高倍)。"""
import cv2, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R/"data"/"raw_images"; TR = R/"runs"/"table_reconstruct"; OUT = R/"runs"/"tmp"

def full_height_lines(gray, y0, y1, th=0.75, minsep=8):
    band = gray[int(y0):int(y1)]
    frac = (band < 150).mean(axis=0)
    idx = [i for i in range(3, len(frac)-3) if frac[i] >= th and frac[i] == frac[i-3:i+4].max()]
    out = []
    for i in idx:
        if out and i - out[-1][0] <= minsep:
            if frac[i] > frac[out[-1][0]]: out[-1] = (i, float(frac[i]))
        else: out.append((i, float(frac[i])))
    return out

for stem in ["钻孔柱状图1042", "钻孔柱状图1032", "钻孔柱状图1023", "钻孔柱状图1033"]:
    hm = json.load(open(TR/f"{stem}_表头映射.json", encoding="utf-8"))
    rd = json.load(open(TR/f"{stem}_行判定.json", encoding="utf-8"))
    g = cv2.imread(str(RAW/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    H = g.shape[0]
    rows = [r for r in rd["rows"] if min(p[1] for p in r["poly"]) >= hm["band"][1]]
    ys = [float(np.mean([p[1] for p in r["poly"]])) for r in rows]
    # 全表高覆盖率:从首行到末行
    y0, y1 = ys[0]+5, ys[-1]-5
    fh = full_height_lines(g, y0, y1, th=0.75)
    print(f"##### {stem} 表高 y[{y0:.0f},{y1:.0f}] 行数={len(rows)}")
    print("  全表高竖线(覆盖≥75%):", [x for x,_ in fh])
    print("  映射 sep_x_band      :", [round(v,1) for v in hm["sep_x_band"]])
    miss = [x for x,_ in fh if min(abs(x-s) for s in hm["sep_x_band"]) > 8]
    print("  >> 真线但映射没有    :", miss)
    print()

# 1023 数据区超高倍
g = cv2.imread(str(RAW/"钻孔柱状图1023.JPG"), cv2.IMREAD_GRAYSCALE)
c = g[1000:1500, 310:560]
col = cv2.cvtColor(c, cv2.COLOR_GRAY2BGR)
for x,lab in [(325.6,"sep2"),(450.6,"sep3"),(537.6,"sep4")]:
    xi=int(round(x))-310
    cv2.line(col,(xi,0),(xi,col.shape[0]),(0,200,0),1)
    cv2.putText(col,lab,(xi+2,20),cv2.FONT_HERSHEY_SIMPLEX,0.5,(0,140,0),1)
col = cv2.resize(col, None, fx=3.4, fy=3.4, interpolation=cv2.INTER_CUBIC)
cv2.imwrite(str(OUT/"z1023_data2.png"), col); print("z1023_data2.png", col.shape)

# 1042 表头 真厚 候选字块超高倍
c = g[0:0]  # noop
g2 = cv2.imread(str(RAW/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
c = g2[750:915, 630:840]
c = cv2.resize(c, None, fx=5.0, fy=5.0, interpolation=cv2.INTER_CUBIC)
cv2.imwrite(str(OUT/"z1042_zhj.png"), c); print("z1042_zhj.png", c.shape)
