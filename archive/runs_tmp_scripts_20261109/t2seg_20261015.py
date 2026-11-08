# -*- coding: utf-8 -*-
"""1042 _分割线.json 逐线 x(y) 剖面。"""
import json, sys
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
STEM = "钻孔柱状图1042"
seg = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{STEM}_分割线.json").read_text(encoding="utf-8"))
print("顶层键:", list(seg.keys()), "ends_report:", seg.get("ends_report"))
YS = [800, 2000, 4000, 6000, 8000, 10000, 12000, 14000, 16000, 18000, 19500]
for ln in seg["lines"]:
    pts = np.array(ln["pts"], dtype=float)
    if len(pts) < 2: continue
    o = np.argsort(pts[:,1]); pts = pts[o]
    prof = " ".join("%d:%.0f" % (y, float(np.interp(y, pts[:,1], pts[:,0])))
                    for y in YS if pts[0,1] <= y <= pts[-1,1])
    print("[%2s] %-8s %-16s n=%-4d y=[%.0f,%.0f] x=[%.0f,%.0f]" % (
        str(ln.get("index")), ln["kind"], str(ln.get("name"))[:16], len(pts),
        pts[0,1], pts[-1,1], pts[:,0].min(), pts[:,0].max()))
    print("     src=%-22s orig=%d fills=%s ext=%s unfilled=%s" % (
        str(ln.get("src")), len(ln.get("_orig_ids") or []), ln.get("fills"), ln.get("extends"), ln.get("unfilled")))
    print("     x(y):", prof)
