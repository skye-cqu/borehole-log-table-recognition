# -*- coding: utf-8 -*-
"""顺序墨迹追踪器(1033 先例同法)对照扇形真值。
种子=表头带内 709 竖笔;每 y 在 ±WIN 内找最接近上一位置的细行程(w<=WMAX,墨量>=TH);失配冻结。"""
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
fan = np.load(str(R/"runs/tmp/t2_fan709_20261015.npy")); FY, FX = fan[:,0], fan[:,1]
Y0, Y1 = 760, int(FY[-1])

def runs_row(y, x0=90, x1=1210, wmax=5):
    row = dark[y, x0:x1]; out = []; s = None
    for i, v in enumerate(row):
        if v and s is None: s = i
        elif not v and s is not None:
            if i - s <= wmax: out.append((x0+(s+i-1)/2.0, i-s))
            s = None
    if s is not None and len(row)-s <= wmax: out.append((x0+(s+len(row)-1)/2.0, len(row)-s))
    return out

def track(win, wmax=5, seed=None, y0=Y0, y1=Y1, frac=0.55):
    # 种子:表头带 y0 处最接近 709 的细行程
    rr = runs_row(y0, wmax=wmax)
    cands = [c for c, w in rr]
    cur = seed if seed is not None else min(cands, key=lambda c: abs(c-709.0))
    xs, ys = [], []
    misses = 0
    for y in range(y0, y1+1):
        rr = runs_row(y, wmax=wmax)
        best, bd = None, None
        for c, w in rr:
            d = abs(c - cur)
            if d <= win and (bd is None or d < bd): best, bd = c, d
        if best is None:
            misses += 1
            if misses > 200: break
            continue
        misses = 0
        cur = best
        xs.append(cur); ys.append(y)
    return np.array(xs), np.array(ys)

print("== 顺序墨迹追踪器 vs 扇形真值 ==")
for win in (3, 4, 6, 8, 12, 18):
    xs, ys = track(win)
    m = (ys >= FY[0]) & (ys <= FY[-1])
    dev = np.abs(xs[m] - np.interp(ys[m], FY, FX))
    print("  WIN=%-3d 点=%5d y=[%d,%d] 覆盖=%.3f  |差|中位=%.1f P90=%.1f 最大=%.1f  >8px=%.3f"
          % (win, len(ys), ys[0], ys[-1], (ys[-1]-ys[0])/(Y1-Y0),
             np.median(dev), np.percentile(dev,90), dev.max(), (dev>8).mean()))
# 对照:同法追踪 633(已知真界),自检方法
print("\n== 自检:同法追踪 633 ==")
fan633 = 632.7 + (FY - FY[0])*0  # 占位
tr633 = np.load(str(R/"runs/tmp/t2_chain_633_20261015.npy")); tr633 = tr633[np.argsort(tr633[:,1])]
for win in (6, 12):
    xs, ys = track(win, seed=None, y0=760)
    # 用 633 的种子重跑
    xs2, ys2 = track(win, seed=float(np.interp(760, tr633[:,1], tr633[:,0])))
    dev = np.abs(xs2 - np.interp(ys2, tr633[:,1], tr633[:,0]))
    print("  WIN=%-3d 点=%5d y=[%d,%d]  vs 633链 |差|中位=%.1f P90=%.1f 最大=%.1f"
          % (win, len(ys2), ys2[0], ys2[-1], np.median(dev), np.percentile(dev,90), dev.max()))
