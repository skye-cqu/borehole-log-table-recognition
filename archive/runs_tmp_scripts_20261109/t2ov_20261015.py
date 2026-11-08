# -*- coding: utf-8 -*-
"""把接出的 709 界折线叠加到原图上(左:全图缩略;右:逐段放大条)。"""
import sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
STEM = "钻孔柱状图1042"
g = cv2.imread(str(paths.RAW_DIR/f"{STEM}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
img = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
tr = np.load(str(R/"runs/tmp/t2_chain_709_20261015.npy"))
tr = tr[np.argsort(tr[:,1])]
# 画成连续折线(逐 y 插值)
yy = np.arange(int(tr[0,1]), int(tr[-1,1])+1)
xx = np.interp(yy, tr[:,1], tr[:,0])
for y, x in zip(yy, xx):
    cv2.circle(img, (int(round(x)), int(y)), 6, (0,0,255), -1)
# 也画 633 界(绿)
tr2 = np.load(str(R/"runs/tmp/t2_chain_633_20261015.npy"))
tr2 = tr2[np.argsort(tr2[:,1])]
yy2 = np.arange(int(tr2[0,1]), int(tr2[-1,1])+1)
xx2 = np.interp(yy2, tr2[:,1], tr2[:,0])
for y, x in zip(yy2, xx2):
    cv2.circle(img, (int(round(x)), int(y)), 5, (0,180,0), -1)
# 裁 x 440..980 后缩放
sub = img[:, 440:980]
sc = 700.0 / sub.shape[1]
small = cv2.resize(sub, (700, int(sub.shape[0]*sc)), interpolation=cv2.INTER_AREA)
cv2.imwrite(str(R/"runs/tmp/t2_chainover_20261015.png"), small)
print("saved", small.shape)
# 局部条:4 个 y 窗口 × 3x
strips = []
for y0 in (800, 5000, 10000, 15000, 19000):
    y1 = min(H, y0+900)
    s = img[y0:y1, 560:960]
    s = cv2.resize(s, (s.shape[1]*2, s.shape[0]*2), interpolation=cv2.INTER_NEAREST)
    cv2.putText(s, "y=%d..%d" % (y0, y1), (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,0,0), 2)
    strips.append(s)
comp = np.hstack(strips)
cv2.imwrite(str(R/"runs/tmp/t2_chainstrips_20261015.png"), comp)
print("saved strips", comp.shape)
