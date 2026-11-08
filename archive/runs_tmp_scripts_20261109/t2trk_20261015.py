# -*- coding: utf-8 -*-
"""1042 真厚|柱状 列界(表头 x=709)逐行墨迹跟踪。只测量,不写产物。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
STEM = "钻孔柱状图1042"
g = cv2.imread(str(paths.RAW_DIR/f"{STEM}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
XA, XB = 560, 900
sub = (g[:, XA:XB] < 150)
cs = np.cumsum(np.vstack([np.zeros((1, sub.shape[1]), np.int64), sub.astype(np.int64)]), axis=0)
HW, Y0, Y1, WIN = 20, 745, 19745, 26
pred, pts, miss = 709.0, [], 0
for y in range(Y0, Y1 + 1):
    a, b = max(0, y-HW), min(H, y+HW+1)
    cs_row = cs[b] - cs[a]
    lo = int(max(0, pred - WIN - XA)); hi = int(min(XB - XA, pred + WIN + 1 - XA))
    if hi <= lo: continue
    seg = cs_row[lo:hi]
    k = int(np.argmax(seg)); frac = seg[k] / float(b - a)
    if frac >= 0.75:
        x = float(XA + lo + k); pts.append((y, x)); pred = x
    else:
        miss += 1
arr = np.array(pts)
print("测量点 =", len(arr), " 未测行 =", miss, " y=[%d,%d]" % (arr[0,0], arr[-1,0]))
print("x 范围 = %.0f .. %.0f  总漂移 = %+.0f" % (arr[:,1].min(), arr[:,1].max(), arr[-1,1]-arr[0,1]))
d = np.diff(arr[:,1])
print("|dx/dy| 最大 = %.2f  >2 的行数 = %d" % (np.abs(d).max(), int((np.abs(d) > 2).sum())))
print("\n剖面:")
for y in range(int(arr[0,0]), int(arr[-1,0])+1, 1000):
    k = np.argmin(np.abs(arr[:,0]-y))
    print("   y=%6d x=%.0f" % (arr[k,0], arr[k,1]))
np.save(str(R/"runs/tmp/t2_trk709_20261015.npy"), arr)
print("\n已存 runs/tmp/t2_trk709_20261015.npy")
