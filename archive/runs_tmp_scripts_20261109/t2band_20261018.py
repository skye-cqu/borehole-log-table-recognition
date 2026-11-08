# -*- coding: utf-8 -*-
"""第一性原理:判定"双描"不能用 x_mid 单点距离。
两条 _分割线 若真是同一物理线的两次检出,则在整个表头带内逐 y 都应贴在一起;
若在某处分开,就是两条不同的线。逐对测带内偏差。"""
import json, sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
import numpy as np

RECON = paths.RUNS_DIR / "table_reconstruct"
def interp(xs, ys, y):
    return float(np.interp(y, ys, xs))

rows = []
for f in sorted(RECON.glob("*_分割线.json")):
    stem = f.name[:-len("_分割线.json")]
    hmf = RECON / f"{stem}_表头映射.json"
    if not hmf.exists(): continue
    hm = json.loads(hmf.read_text(encoding="utf-8"))
    band = hm.get("band")
    if not band: continue
    d = json.loads(f.read_text(encoding="utf-8"))
    L = []
    for ln in d["lines"]:
        p = np.asarray(ln["pts"], float)
        p = p[np.argsort(p[:, 1])]
        if len(p) < 2: continue
        L.append((ln.get("name") or ln["kind"], p[:, 0], p[:, 1]))
    if len(L) < 2: continue
    L.sort(key=lambda t: interp(t[1], t[2], (band[0]+band[1])/2))
    for i in range(len(L) - 1):
        nA, xA, yA = L[i]
        nB, xB, yB = L[i+1]
        xm = interp(xA, yA, (band[0]+band[1])/2)
        xn = interp(xB, yB, (band[0]+band[1])/2)
        if xn - xm >= 40: continue
        lo = max(float(yA.min()), float(yB.min()), band[0])
        hi = min(float(yA.max()), float(yB.max()), band[1])
        if hi - lo < 20: 
            rows.append((stem, nA, nB, xm, xn, 0.0, 0.0, 0)); continue
        dd = [abs(interp(xA, yA, y) - interp(xB, yB, y)) for y in np.arange(lo, hi+1, 2)]
        dd = np.array(dd)
        rows.append((stem, nA, nB, xm, xn, float(dd.mean()), float(dd.max()), len(dd)))
print("表头带内间距 <40px 的相邻线对: 共 %d 对\n" % len(rows))
print("%-16s %-10s %-10s %7s %7s %8s %8s" % ("stem","A","B","xmid差","带内均差","带内最大","样本"))
for r in rows:
    print("%-16s %-10s %-10s %7.1f %8.1f %8.1f %6d" % (r[0][-4:], r[1][:9], r[2][:9], r[4]-r[3], r[5], r[6], r[7]))
