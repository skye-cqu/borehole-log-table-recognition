# -*- coding: utf-8 -*-
"""1042 全宽竖线普查:每 y 找所有近满高竖笔,与表头界址比对,求统一漂移 d(y)。

判据:表内所有列界近似平行(等距漂移)。若某界在 x_expected+d 处有墨,
则该界在该 y 真实存在;据此判定 _分割线.json 各线的可信区间。
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
dark = (g < 150)
# 表头界址(y=829 实测):地质|煤层 196.7, 煤层|深度 260.2, 深度|层厚 384.5,
# 层厚|采长 468.7, 采长|倾角 551.9, 倾角|真厚 632.7, 真厚|柱状 709, 柱状|岩性 913
HDR = [("地质|煤层", 196.7), ("煤层|深度", 260.2), ("深度|层厚", 384.5),
       ("层厚|采长", 468.7), ("采长|倾角", 551.9), ("倾角|真厚", 632.7),
       ("真厚|柱状", 709.0), ("柱状|岩性", 913.0)]
SPAN = 30   # 纵向窗口
print("y      d(y)  " + "  ".join("%s" % n for n, _ in HDR))
rows = []
for y in range(1000, min(H, 19900), 500):
    b0, b1 = y - SPAN//2, y + SPAN//2
    dens = (dark[b0:b1] < 1).sum(axis=0) / float(b1-b0)
    # 求使 8 条期望位置总墨量最大的统一漂移 d
    best, bd = -1.0, None
    for d in np.arange(-25, 175, 0.5):
        v = 0.0
        for _, x in HDR:
            xi = int(round(x + d))
            if 0 <= xi < W: v += dens[max(0, xi-4):xi+5].max()
        if v > best: best, bd = v, float(d)
    vals = []
    for nm, x in HDR:
        xi = int(round(x + bd))
        vals.append(dens[max(0, xi-4):xi+5].max() if 0 <= xi < W else -1)
    rows.append((y, bd, vals))
    print("%-6d %5.1f  " % (y, bd) + "  ".join("%.2f" % v for v in vals))
arr = np.array([r[1] for r in rows]); ys = np.array([r[0] for r in rows])
print("\nd(y) 线性拟合: d = %.2f + %.6f*(y-1000)" % (arr[0], np.polyfit(ys, arr, 1)[0]))
print("d 范围 [%.1f, %.1f]" % (arr.min(), arr.max()))
V = np.array([r[2] for r in rows])
print("\n各界在各 y 的墨量: 列均值/最小/低于0.6的y个数")
for k, (nm, x) in enumerate(HDR):
    col = V[:, k]
    bad = [int(rows[i][0]) for i in range(len(rows)) if col[i] < 0.6]
    print("  %-10s 均%.2f 最小%.2f 弱墨y=%s" % (nm, col.mean(), col.min(), bad[:12]))
