# -*- coding: utf-8 -*-
"""用"全重叠跨度"而非"表头带内"判双描:两线若同属一条物理线,应全程贴在一起。"""
import json, sys
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
RECON = paths.RUNS_DIR / "table_reconstruct"
def itp(xs, ys, y): return np.interp(y, ys, xs)

print("%-5s %-9s %-9s %7s %7s %8s %8s  %s" % ("stem","A","B","xmid差","带内均","全段均","全段最大","重叠y"))
for f in sorted(RECON.glob("*_分割线.json")):
    stem = f.name[:-len("_分割线.json")]
    hmf = RECON / f"{stem}_表头映射.json"
    if not hmf.exists(): continue
    hm = json.loads(hmf.read_text(encoding="utf-8")); band = hm.get("band")
    if not band: continue
    d = json.loads(f.read_text(encoding="utf-8"))
    L = []
    for ln in d["lines"]:
        p = np.asarray(ln["pts"], float); p = p[np.argsort(p[:,1])]
        if len(p) >= 2: L.append((ln.get("name") or ln["kind"], p[:,0], p[:,1]))
    if len(L) < 2: continue
    ym = (band[0]+band[1])/2
    L.sort(key=lambda t: float(itp(t[1], t[2], ym)))
    for i in range(len(L)-1):
        nA, xA, yA = L[i]; nB, xB, yB = L[i+1]
        gap = float(itp(xB,yB,ym)) - float(itp(xA,yA,ym))
        if gap >= 40: continue
        lo = max(float(yA.min()), float(yB.min())); hi = min(float(yA.max()), float(yB.max()))
        if hi - lo < 50: continue
        ys = np.arange(lo, hi+1, 2.0)
        dd = np.abs(itp(xA,yA,ys) - itp(xB,yB,ys))
        yb0, yb1 = max(lo, band[0]), min(hi, band[1])
        db = np.abs(itp(xA,yA,np.arange(yb0,yb1+1,2.0)) - itp(xB,yB,np.arange(yb0,yb1+1,2.0))) if yb1-yb0>10 else np.array([0.])
        print("%-5s %-9s %-9s %7.1f %7.1f %8.1f %8.1f  [%.0f,%.0f]" % (
            stem[-4:], nA[:8], nB[:8], gap, db.mean(), dd.mean(), dd.max(), lo, hi))
