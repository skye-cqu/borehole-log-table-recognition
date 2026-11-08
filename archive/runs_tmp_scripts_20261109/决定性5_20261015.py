# -*- coding: utf-8 -*-
"""决定性裁片:
① 1042 数据区 x[560,960] 多行 —— [633,709] 是否真是"真厚"数据列;
② 1032 数据区 x[0,220] 多行 —— 深度列左缘是否被扫描裁切(数字是否从 x=0 起就被切断)。"""
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

# ① 1042 数据区
hm, ys = rows_of("钻孔柱状图1042")
g = cv2.imread(str(RAW/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
y0, y1 = int(ys[1]), int(ys[8])
c = g[y0:y1, 540:960]
col = cv2.cvtColor(c, cv2.COLOR_GRAY2BGR)
for x,lab,cl in [(553,"s5",(0,200,0)),(633,"s7",(0,200,0)),(709,"709",(0,0,255)),(912,"s8",(0,200,0))]:
    xi = x-540
    if 0 <= xi < col.shape[1]:
        cv2.line(col,(xi,0),(xi,col.shape[0]),cl,1)
        cv2.putText(col,lab,(xi+2,20),cv2.FONT_HERSHEY_SIMPLEX,0.55,cl,1)
c2 = cv2.resize(col, None, fx=2.6, fy=2.6, interpolation=cv2.INTER_CUBIC)
cv2.imwrite(str(OUT/"d1042_data_wide.png"), c2); print("d1042_data_wide.png", c2.shape, "y", y0, y1)

# ② 1032 数据区
hm2, ys2 = rows_of("钻孔柱状图1032")
g2 = cv2.imread(str(RAW/"钻孔柱状图1032.JPG"), cv2.IMREAD_GRAYSCALE)
y0, y1 = int(ys2[1]), int(ys2[10])
c = g2[y0:y1, 0:230]
col = cv2.cvtColor(c, cv2.COLOR_GRAY2BGR)
for x,lab in [(105,"105"),(192,"192")]:
    if 0 <= x < col.shape[1]:
        cv2.line(col,(x,0),(x,col.shape[0]),(0,200,0),1)
        cv2.putText(col,lab,(x+2,20),cv2.FONT_HERSHEY_SIMPLEX,0.55,(0,140,0),1)
c2 = cv2.resize(col, None, fx=2.6, fy=2.6, interpolation=cv2.INTER_CUBIC)
cv2.imwrite(str(OUT/"d1032_left_wide.png"), c2); print("d1032_left_wide.png", c2.shape, "y", y0, y1)
