# -*- coding: utf-8 -*-
import cv2, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R/"data"/"raw_images"; TR = R/"runs"/"table_reconstruct"; OUT = R/"runs"/"tmp"

def crop_ann(stem, x0, x1, y0, y1, sc, out, seps=None, extra=None):
    g = cv2.imread(str(RAW/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    c = g[y0:y1, x0:x1]
    col = cv2.cvtColor(c, cv2.COLOR_GRAY2BGR)
    for x in (seps or []):
        xi = int(round(x))
        if x0 <= xi < x1:
            cv2.line(col, (xi-x0,0),(xi-x0,col.shape[0]),(0,200,0),1)
            cv2.putText(col, str(xi), (xi-x0+2, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,140,0), 1)
    for x in (extra or []):
        xi = int(round(x))
        if x0 <= xi < x1:
            cv2.line(col, (xi-x0,0),(xi-x0,col.shape[0]),(0,0,255),1)
            cv2.putText(col, str(xi), (xi-x0+2, col.shape[0]-4), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,0,255), 1)
    if sc != 1.0: col = cv2.resize(col, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(str(OUT/out), col); print(out, col.shape)

# 1023 表头:层厚/深度两格(映射 sep 325.6 / 450.6 / 537.6)
crop_ann("钻孔柱状图1023", 300, 570, 550, 740, 3.2, "v_1023_hdr2.png", seps=[325.6, 450.6, 537.6])
# 1023 数据前三行
crop_ann("钻孔柱状图1023", 300, 570, 740, 1100, 3.2, "v_1023_data.png", seps=[325.6, 450.6, 537.6])
# 1042 表头 x600-960:是否有 真厚 列(sep 632.7, 912;真墨 633,709,913)
crop_ann("钻孔柱状图1042", 600, 960, 735, 925, 3.0, "v_1042_hdr2.png", seps=[632.7, 912.0], extra=[709])
# 1042 数据同区间
crop_ann("钻孔柱状图1042", 600, 960, 1050, 1420, 3.0, "v_1042_data2.png", seps=[632.7, 912.0], extra=[709])
