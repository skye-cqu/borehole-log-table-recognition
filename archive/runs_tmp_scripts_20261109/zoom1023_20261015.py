# -*- coding: utf-8 -*-
import cv2, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R/"data"/"raw_images"; OUT = R/"runs"/"tmp"
# 1023 表头两格超高倍
g = cv2.imread(str(RAW/"钻孔柱状图1023.JPG"), cv2.IMREAD_GRAYSCALE)
for tag,(x0,x1) in {"A_326_451":(320,458), "B_451_538":(445,545)}.items():
    c = g[555:740, x0:x1]
    c = cv2.resize(c, None, fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(str(OUT/f"z1023_{tag}.png"), c); print(f"z1023_{tag}.png", c.shape)
# 1023 数据区同两格(前4行)超高倍
c = g[735:1120, 320:545]
c = cv2.resize(c, None, fx=3.2, fy=3.2, interpolation=cv2.INTER_CUBIC)
cv2.imwrite(str(OUT/"z1023_data.png"), c); print("z1023_data.png", c.shape)
