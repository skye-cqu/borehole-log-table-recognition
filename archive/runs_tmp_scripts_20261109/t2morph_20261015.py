# -*- coding: utf-8 -*-
"""1042:用竖向形态学开运算找**长竖线**(抗倾斜:长线必然在局部开运算后存活)。
文字/岩性花纹会被消掉。这是"数据源神圣"允许的墨迹证据,不做几何外推。"""
import sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

g = cv2.imread(str(paths.RAW_DIR / "钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ink = (g < 128).astype(np.uint8)

X0, X1 = 500, 1150
Y0, Y1 = 730, 19950
reg = ink[Y0:Y1, X0:X1]
print("区域 x=[%d,%d] y=[%d,%d] shape=%s" % (X0, X1, Y0, Y1, reg.shape))

for KH in (120, 200, 300):
    k = cv2.getStructuringElement(cv2.MORPH_RECT, (1, KH))
    op = cv2.morphologyEx(reg, cv2.MORPH_OPEN, k)
    n, lab, stats, cent = cv2.connectedComponentsWithStats(op, 8)
    comps = []
    for i in range(1, n):
        x, y, w, h, a = stats[i]
        if h >= KH:                       # 存活下来的必然是长竖线
            comps.append((x + X0, x + w + X0, y + Y0, y + h + Y0, h, a))
    comps.sort(key=lambda c: c[0])
    print()
    print("== 竖核高 %d:找到 %d 条长竖线 ==" % (KH, len(comps)))
    for c in comps:
        print("   x=[%d,%d] y=[%d,%d] 高=%d 墨=%d" % c)

print()
print("== 表头带 [747,911] 内的竖线(高核 60) ==")
hb = ink[747:911, 500:1150]
k = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 60))
op = cv2.morphologyEx(hb, cv2.MORPH_OPEN, k)
colsum = op.sum(axis=0)
runs = []
inr = False
for i, v in enumerate(colsum):
    if v > 0 and not inr: s = i; inr = True
    elif v == 0 and inr: runs.append((s + 500, i + 500, int(colsum[s:i].max()))); inr = False
if inr: runs.append((s + 500, len(colsum) + 500, int(colsum[s:].max())))
for a, b, m in runs:
    print("   x=[%d,%d] 宽=%d 最大高度=%d" % (a, b, b - a, m))

print()
print("== 参考:sep_x_band 在 [500,1150] 内的界 ==")
sb = [70.0, 196.7, 260.2, 384.5, 468.7, 550.7, 553.0, 632.7, 912.0, 2228.2, 2771.2]
print("  ", [v for v in sb if 500 <= v <= 1150])
