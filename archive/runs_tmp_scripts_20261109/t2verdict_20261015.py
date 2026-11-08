# -*- coding: utf-8 -*-
"""1042:判定 x≈709 是"列界"还是"真字的笔画"。
判据:真列界必须**纵向贯通整个表高**;笔画只在字高内。
"""
import sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ink = (g < 128).astype(np.uint8)
H, W = g.shape
print("图 %dx%d" % (W, H))

def prof(x, y0, y1):
    col = ink[y0:y1, x]
    n = int(col.sum())
    best = cur = 0
    for v in col:
        cur = cur+1 if v else 0
        best = max(best, cur)
    return n, best, y1-y0

print()
print("== 表头带 y=[747,911] 全 x 的纵向覆盖率(>=40%) ==")
for x in range(60, 1000):
    n, best, tot = prof(x, 747, 911)
    if n >= 0.40*tot:
        print("   x=%-5d 暗=%-4d/%-4d (%.0f%%) 最长连续=%d" % (x, n, tot, 100.0*n/tot, best))

print()
print("== 整表高 y=[750,19750] 覆盖率(>=25%) 的 x∈[560,1000] ==")
for x in range(560, 1000):
    n, best, tot = prof(x, 750, 19750)
    if n >= 0.25*tot:
        print("   x=%-5d 暗=%-5d/%-5d (%.0f%%) 最长连续=%d" % (x, n, tot, 100.0*n/tot, best))
