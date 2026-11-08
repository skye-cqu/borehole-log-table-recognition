# -*- coding: utf-8 -*-
"""两参数扇形真值拟合(只用原图墨迹,不用 _分割线.json):
x_true(y,a) = a + f(y) + g(y)*(a-551.9);每 y 最小化 8 条表头界址到细行程集的距离。
再把种子链 709 与真值比对,判定该链是否就是 真厚|柱状 界。"""
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
A = np.array([196.7, 260.2, 384.5, 468.7, 551.9, 632.7, 709.0, 913.0])
REF = 551.9

def thin_runs(y, x0=90, x1=1210, wmax=5):
    row = dark[y, x0:x1]; out = []; s = None
    for i, v in enumerate(row):
        if v and s is None: s = i
        elif not v and s is not None:
            if i - s <= wmax: out.append(x0 + (s + i - 1) / 2.0)
            s = None
    if s is not None and len(row) - s <= wmax: out.append(x0 + (s + len(row) - 1) / 2.0)
    return np.array(out)

def fit_fan(y):
    rr = thin_runs(y)
    if len(rr) < 5: return None
    best, bs = None, 1e9
    for f in np.arange(-40, 200, 2.0):
        for gg in np.arange(-0.10, 0.42, 0.01):
            exp = A + f + gg * (A - REF)
            dist = np.abs(rr[None, :] - exp[:, None]).min(axis=1)
            if dist.max() > 20: continue
            if dist.mean() < bs: best, bs = (f, gg), dist.mean()
    return best

ys = list(range(900, 19700, 100))
rows = []
for y in ys:
    r = fit_fan(y)
    if r: rows.append((y, r[0], r[1]))
arr = np.array(rows)
print("可拟合 y = %d / %d" % (len(arr), len(ys)))
print("f(y): y=1000 %.0f  y=6000 %.0f  y=10000 %.0f  y=15000 %.0f  y=19000 %.0f" % tuple(
    np.interp(t, arr[:,0], arr[:,1]) for t in (1000,6000,10000,15000,19000)))
print("g(y): y=1000 %.2f  y=6000 %.2f  y=10000 %.2f  y=15000 %.2f  y=19000 %.2f" % tuple(
    np.interp(t, arr[:,0], arr[:,2]) for t in (1000,6000,10000,15000,19000)))
# 预测 709 真值
pred709 = 709.0 + arr[:,1] + arr[:,2]*(709.0-REF)
np.save(str(R/"runs/tmp/t2_fan709_20261015.npy"), np.vstack([arr[:,0], pred709]).T)
# 种子链比对
tr = np.load(str(R/"runs/tmp/t2_chain_709_20261015.npy")); tr = tr[np.argsort(tr[:,1])]
ty, tx = tr[:,1], tr[:,0]
m = (ty >= arr[0,0]) & (ty <= arr[-1,0])
pv = np.interp(ty[m], arr[:,0], pred709)
dev = tx[m] - pv
print("\n种子链 709 vs 扇形真值: n=%d 中位|差|=%.1f px  P90=%.1f  最大=%.1f  >8px占比=%.2f" % (
    m.sum(), np.median(np.abs(dev)), np.percentile(np.abs(dev),90), np.abs(dev).max(), (np.abs(dev)>8).mean()))
print("逐段:")
for t in range(1000, 19700, 1500):
    k = int(np.argmin(np.abs(ty-t)))
    if not m[k]: continue
    print("   y=%-6d 链=%6.0f  真值=%6.0f  差=%+5.0f" % (t, tx[k], np.interp(ty[k],arr[:,0],pred709), tx[k]-np.interp(ty[k],arr[:,0],pred709)))
# 对照:633 链(已知真界)作为方法自检
tr2 = np.load(str(R/"runs/tmp/t2_chain_633_20261015.npy")); tr2 = tr2[np.argsort(tr2[:,1])]
pred633 = 632.7 + arr[:,1] + arr[:,2]*(632.7-REF)
m2 = (tr2[:,1] >= arr[0,0]) & (tr2[:,1] <= arr[-1,0])
dev2 = tr2[m2,0] - np.interp(tr2[m2,1], arr[:,0], pred633)
print("\n自检 种子链 633 vs 扇形真值: n=%d 中位|差|=%.1f  P90=%.1f 最大=%.1f" % (
    m2.sum(), np.median(np.abs(dev2)), np.percentile(np.abs(dev2),90), np.abs(dev2).max()))
