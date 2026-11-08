# -*- coding: utf-8 -*-
"""1042 抗漂移测量:在 [540,1060] 区间沿 y 逐段找竖线墨峰。
方法:每个 y 取 +-4px 横带,统计该带内每列 x 的墨量(纵向连通性),
     找峰。真竖线会在相邻 y 之间**平滑连续**;噪声不会。
固定 x 窗口会因原图倾斜漏检,所以这里逐 y 输出峰位。"""
import sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

p = paths.RAW_DIR/"钻孔柱状图1042.JPG"
g = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
print("图像:", g.shape)
ink = (g < 128).astype(np.uint8)

X0, X1 = 540, 1060
YS = list(range(780, 19800, 300))
print()
print("y      峰位(x)  峰高   [该横带内墨柱最高处]")
prev = None
peaks_all = []
for y in YS:
    band = ink[max(0,y-4):y+5, X0:X1]
    col = band.sum(axis=0).astype(float)          # 每列墨点数(最大9)
    # 平滑
    k = np.ones(5)/5.0
    cs = np.convolve(col, k, mode="same")
    # 找峰(局部极大且够高)
    idx = []
    for i in range(3, len(cs)-3):
        if cs[i] >= 4.0 and cs[i] == cs[max(0,i-6):i+7].max():
            idx.append(i)
    xs = [X0+i for i in idx]
    hs = [round(float(cs[i]),1) for i in idx]
    peaks_all.append((y, xs))
    print("%-7d %s" % (y, " ".join("%d(%.1f)" % (a,b) for a,b in zip(xs,hs))))

print()
print("== 连续性检验:把每个峰按最近邻跨 y 串联 ==")
tracks = []   # [ {y: x} ]
for y, xs in peaks_all:
    for x in xs:
        best, bd = None, 12
        for t in tracks:
            lx = t[-1][1]
            if abs(lx - x) < bd:
                best, bd = t, abs(lx - x)
        if best is not None:
            best.append((y, x))
        else:
            tracks.append([(y, x)])
tracks = [t for t in tracks if len(t) >= 5]
tracks.sort(key=lambda t: -len(t))
print("跨 y 连续(>=5段)的轨迹:")
for t in tracks[:14]:
    xs = [x for _, x in t]
    print("  段数=%-3d y=[%d,%d] x=[%d,%d] 平均x=%.1f" % (
        len(t), t[0][0], t[-1][0], min(xs), max(xs), sum(xs)/len(xs)))
