# -*- coding: utf-8 -*-
"""独立真值:表头 8 条界址整体漂移 d(y) 拟合(等距签名)。
表是扇形展开,漂移近似一致 → 用统一 d 拟合每条界,再与 _分割线.json 各线比对。"""
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
HDR = [196.7, 260.2, 384.5, 468.7, 551.9, 632.7, 709.0, 913.0]
NAMES = ["地质|煤层","煤层|深度","深度|层厚","层厚|采长","采长|倾角","倾角|真厚","真厚|柱状","柱状|岩性"]
d = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{STEM}_分割线.json").read_text(encoding="utf-8"))
LN = []
for i, ln in enumerate(d["lines"]):
    p = np.asarray(ln["pts"], float); p = p[np.argsort(p[:, 1])]
    LN.append((i, ln.get("name"), p[:, 0], p[:, 1]))

def thin_runs(y, x0=90, x1=1200, wmax=4):
    row = dark[y, x0:x1]; out = []; s = None
    for i, v in enumerate(row):
        if v and s is None: s = i
        elif not v and s is not None:
            if i - s <= wmax: out.append(x0 + (s + i - 1) / 2.0)
            s = None
    if s is not None and len(row) - s <= wmax: out.append(x0 + (s + len(row) - 1) / 2.0)
    return np.array(out)

def fit_delta(y, tol=15.0):
    rr = thin_runs(y)
    if len(rr) == 0: return None, None
    best, bs = None, 1e9
    for dd in np.arange(-60, 220, 0.5):
        exp = np.array(HDR) + dd
        dist = np.abs(rr[None, :] - exp[:, None]).min(axis=1)
        if dist.max() > tol: continue
        if dist.mean() < bs: best, bs = dd, dist.mean()
    return best, bs

# 与 _分割线 各线对应:按表头 x_mid 最近匹配
ys = np.arange(1000, 19600, 25)
res = []
for y in ys:
    dd, s = fit_delta(y)
    if dd is None: continue
    res.append((y, dd))
res = np.array(res)
print("可拟合 y 数 = %d / %d" % (len(res), len(ys)))
print("d(y):  y=1000 -> %.1f   y=5000 -> %.1f   y=10000 -> %.1f   y=15000 -> %.1f   y=19000 -> %.1f"
      % tuple(np.interp(t, res[:,0], res[:,1]) for t in (1000,5000,10000,15000,19000)))

# 每条 _分割线 线与拟合真值比对(仅在其 y 覆盖区间内)
print("\n_分割线.json 线与真值偏差(中位/最大, px):")
for i, nm, xs, lys in LN:
    ds = []
    for y, dd in res:
        if lys.min() <= y <= lys.max():
            ds.append(float(np.interp(y, lys, xs)) - (float(np.interp(y, res[:,0], res[:,1])) + 0))
    if not ds: continue
    ds = np.array(ds)
    # 与 8 条真值界里最近的一条比
    dev = np.min(np.abs(ds[:, None] - np.array(HDR)[None, :]), axis=1)
    print("  [%2d] %-8s n=%4d  最近界偏差 中位%6.1f 最大%6.1f  >20px占比 %.2f"
          % (i, nm, len(ds), np.median(dev), dev.max(), (dev > 20).mean()))
np.save(str(R/"runs/tmp/t2_delta_20261015.npy"), res)
