# -*- coding: utf-8 -*-
"""沿 709 折线逐 y 测墨迹命中(含段间桥接区间),证明该界处处有墨。"""
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
tr = np.load(str(R/"runs/tmp/t2_chain_709_20261015.npy"))   # [[x,y],...] 点序
tr = tr[np.argsort(tr[:,1])]
y0, y1 = int(tr[0,1]), int(tr[-1,1])
print("折线 y=[%d,%d] 点=%d" % (y0, y1, len(tr)))
yy = np.arange(y0, y1+1)
xx = np.interp(yy, tr[:,1], tr[:,0])
hit3 = np.array([dark[y, max(0,int(round(x))-3):int(round(x))+4].any() for y, x in zip(yy, xx)])
hit6 = np.array([dark[y, max(0,int(round(x))-6):int(round(x))+7].any() for y, x in zip(yy, xx)])
print("逐 y 墨迹命中: ±3px = %.4f   ±6px = %.4f" % (hit3.mean(), hit6.mean()))
# 连续未命中段
runs, s = [], None
for i, v in enumerate(hit6):
    if not v and s is None: s = i
    elif v and s is not None:
        runs.append((int(yy[s]), int(yy[i-1]), i-s)); s = None
if s is not None: runs.append((int(yy[s]), int(yy[-1]), len(hit6)-s))
runs.sort(key=lambda r: -r[2])
print("±6px 未命中连续段 top8 (y0,y1,len):", runs[:8])
print("未命中总长 = %d / %d" % (int((~hit6).sum()), len(hit6)))
# 相邻候选段端点跳变(桥接长度)分布
d = np.diff(tr[:,1]); dx = np.abs(np.diff(tr[:,0]))
big = [(int(tr[i,1]), int(tr[i+1,1]), round(float(dx[i]),1)) for i in range(len(d)) if d[i] > 8]
print("段间跳变(>8px) 共 %d 处, 最长 %d px" % (len(big), max([b[1]-b[0] for b in big]) if big else 0))
print("跳变 top6:", sorted(big, key=lambda b: -(b[1]-b[0]))[:6])
