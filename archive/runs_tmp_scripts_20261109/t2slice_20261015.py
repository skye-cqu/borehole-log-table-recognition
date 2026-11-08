# -*- coding: utf-8 -*-
"""1042 体区竖线普查:每个 y 在 ±HW 竖窗内的暗比峰值 → 真实竖线 x。

只报告客观墨迹,不做归属假设。
"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
STEM = "钻孔柱状图1042"
g = cv2.imread(str(paths.RAW_DIR/f"{STEM}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
dark = (g < 150).astype(np.float32)
X0, X1, HW = 420, 1120, 14
print("竖窗高度 = %d px; 暗比 = 窗内暗像素占比" % (2*HW+1))
for y in (1500, 3000, 6000, 9000, 12000, 15000, 18000, 19500):
    a, b = y-HW, y+HW+1
    frac = dark[a:b, X0:X1].mean(axis=0)
    pk = []
    i = 0
    while i < len(frac):
        if frac[i] >= 0.55:
            j = i
            while j < len(frac) and frac[j] >= 0.55: j += 1
            if j - i <= 8:
                k = i + int(np.argmax(frac[i:j]))
                pk.append((X0+k, frac[k]))
            i = j
        else: i += 1
    print("y=%6d: " % y + "  ".join("%d(%.2f)" % (x, f) for x, f in pk))
print()
# 上半/下半中位位置:对每条 x 做纵向连续性打分
print("== 纵向连续竖线(x 固定, y 全域暗比) ==")
for x in (469, 551, 633, 667, 680, 693, 709, 745, 760, 913, 962, 987, 1040):
    col = dark[:, max(0,x-2):x+3].max(axis=1)
    print("  x=%4d 全域暗比=%.3f  y>1000 暗比=%.3f" % (x, col.mean(), col[1000:].mean()))
