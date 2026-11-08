# -*- coding: utf-8 -*-
"""真厚|柱状 列界(表头709)是否由阶段4候选段构成? —— 沿跟踪折线测候选覆盖与墨迹连续性。"""
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
cj = json.loads((paths.CANDIDATE_COORD_DIR / f"{STEM}.json").read_text(encoding="utf-8"))
vf = [s for s in cj["lines"] if s["direction"] == "vertical" and s["label"] == "high"]
print("vertical/high 候选段总数 =", len(vf))

def track(x0, y0, y1, WIN=26):
    pred, pts = float(x0), []
    for y in range(y0, y1 + 1):
        a, b = max(0, y-10), min(H, y+11)
        lo, hi = int(max(0, pred-WIN)), int(min(W, pred+WIN+1))
        if hi - lo < 3: continue
        seg = dark[a:b, lo:hi].sum(axis=0)
        k = int(np.argmax(seg)); frac = seg[k] / float(b-a)
        if frac >= 0.75:
            x = float(lo + k); pts.append((y, x)); pred = x
    return np.array(pts)

tr709 = track(709, 763, 19731)
tr633 = track(633, 763, 19731)
for nm, tr in (("709", tr709), ("633", tr633)):
    print("\n== 跟踪 x0=%s ==  测量行=%d  y=[%d,%d]  x=%.0f..%.0f" % (
        nm, len(tr), tr[0,0], tr[-1,0], tr[:,1].min(), tr[:,1].max()))

def cand_cov(tr, tol):
    cov = np.zeros(H + 2, dtype=bool); n = 0
    for s in vf:
        p = np.asarray(s["points"], float)
        ys = p[:, 1]
        lo, hi = max(0, int(ys.min())), min(H, int(ys.max()))
        if hi - lo < 3: continue
        ys2 = np.arange(lo, hi)
        xs2 = np.interp(ys2, tr[:,0], tr[:,1])
        d = np.abs(np.interp(ys2, ys, p[:,0]) - xs2)
        if (d <= tol).mean() >= 0.8:
            cov[lo:hi] = True; n += 1
    return cov.sum()/H, n

for tol in (8, 12, 20, 30):
    f, n = cand_cov(tr709, tol)
    print("  709 界: tol=%2d 候选覆盖=%.3f 段数=%d" % (tol, f, n))
for tol in (8, 12, 20, 30):
    f, n = cand_cov(tr633, tol)
    print("  633 界: tol=%2d 候选覆盖=%.3f 段数=%d" % (tol, f, n))

for nm, tr in (("709", tr709), ("633", tr633)):
    hit = sum(1 for y, x in tr if dark[y, max(0,int(round(x))-3):int(round(x))+4].any())
    print("  %s 界: 折线±3px 墨迹命中 %d/%d = %.3f" % (nm, hit, len(tr), hit/len(tr)))
np.save(str(R/"runs/tmp/t2_trk709_20261015.npy"), tr709)
np.save(str(R/"runs/tmp/t2_trk633_20261015.npy"), tr633)
print("\n折线已存")
