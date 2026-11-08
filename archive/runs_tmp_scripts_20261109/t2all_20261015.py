# -*- coding: utf-8 -*-
"""1042 全部表头锚点竖界的逐行墨迹跟踪:检查互不交叉、间距合理。"""
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
ANCH = [137, 199, 259, 383, 469, 551, 633, 709, 913, 2227, 2771]
Y0, Y1, WIN, HW = 760, 19740, 24, 10

def track(x0, win=WIN):
    pred, pts = float(x0), []
    for y in range(Y0, Y1+1):
        a, b = max(0, y-HW), min(H, y+HW+1)
        lo, hi = int(max(0, pred-win)), int(min(W, pred+win+1))
        if hi-lo < 3: continue
        seg = dark[a:b, lo:hi].sum(axis=0)
        k = int(np.argmax(seg)); frac = seg[k]/float(b-a)
        if frac >= 0.75:
            x = float(lo+k); pts.append((y, x)); pred = x
    return np.array(pts)

tracks = {}
for x0 in ANCH:
    t = track(x0)
    tracks[x0] = t
    print("锚=%-5d 测量=%-6d y=[%d,%d] x=%.0f..%.0f 漂移=%+.0f" % (
        x0, len(t), t[0,0], t[-1,0], t[:,1].min(), t[:,1].max(), t[-1,1]-t[0,1]))

print("\n== 同 y 处各锚点 x 值(检查单调不交叉) ==")
for y in (1000, 3000, 5000, 7000, 9000, 11000, 13000, 15000, 17000, 19000):
    vals = []
    for x0 in ANCH:
        t = tracks[x0]
        if t[0,0] <= y <= t[-1,0]:
            k = np.argmin(np.abs(t[:,0]-y))
            vals.append((x0, float(t[k,1])))
    s = " ".join("%d:%.0f" % v for v in vals)
    mono = all(vals[i][1] < vals[i+1][1] for i in range(len(vals)-1))
    print("  y=%6d  %s  单调=%s" % (y, s, mono))
np.savez(str(R/"runs/tmp/t2_tracks_20261015.npz"), **{str(k): v for k, v in tracks.items()})
print("\n已存 runs/tmp/t2_tracks_20261015.npz")
