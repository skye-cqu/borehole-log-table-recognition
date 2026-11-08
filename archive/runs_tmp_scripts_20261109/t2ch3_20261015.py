# -*- coding: utf-8 -*-
"""1042 x∈[600,1000] 区真实墨迹竖链普查(逐行峰值 + 链链接)。

不做任何假设,只报告客观墨迹。
"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
STEM = "钻孔柱状图1042"
X0, X1, WIN, TH = 600, 1000, 26, 0.55
g = cv2.imread(str(paths.RAW_DIR/f"{STEM}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
dark = (g < 150)
# 每个 y 在窗口内找局部暗峰
chains = []
for y in range(700, H):
    row = g[y, X0:X1]
    d = (row < 150).astype(np.float32)
    if d.sum() < 2: continue
    # 平滑
    k = np.ones(5, np.float32)/5
    s = np.convolve(d, k, mode="same")
    peaks = []
    for i in range(3, len(s)-3):
        if s[i] >= 0.55 and s[i] >= s[i-3] and s[i] >= s[i+3]:
            peaks.append(X0+i)
    # 去重(相邻<6px)
    ded = []
    for p in peaks:
        if ded and p-ded[-1] < 6: continue
        ded.append(p)
    for p in ded:
        hit = None
        for c in chains:
            if c["y1"] >= y-4 and abs(c["x"] - p) <= WIN:
                hit = c; break
        if hit:
            hit["x"] = 0.5*hit["x"] + 0.5*p; hit["y1"] = y; hit["n"] += 1
        else:
            chains.append({"x": float(p), "y0": y, "y1": y, "n": 1})
big = [c for c in chains if c["n"] >= 250 and c["y1"]-c["y0"] >= 250]
big.sort(key=lambda c: -c["n"])
print("长竖链 (n>=250 且跨度>=250):", len(big))
for c in big:
    print("  x=%7.1f  y=[%6d,%6d] 跨度=%6d n=%6d 密度=%.2f" % (
        c["x"], c["y0"], c["y1"], c["y1"]-c["y0"], c["n"], c["n"]/max(1,(c["y1"]-c["y0"]))))
