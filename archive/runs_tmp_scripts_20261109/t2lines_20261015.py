# -*- coding: utf-8 -*-
"""逐条 _分割线.json 线测 x(y) 剖面,判定 550.7/553.0 是否同一物理线的双描。"""
import json, sys
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
STEM = "钻孔柱状图1042"
d = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{STEM}_分割线.json").read_text(encoding="utf-8"))
print("键 =", list(d.keys()))
for i, ln in enumerate(d["lines"]):
    pts = np.asarray(ln["pts"], float)
    pts = pts[np.argsort(pts[:,1])]
    xs, ys = pts[:,0], pts[:,1]
    xm = float(np.interp(829, ys, xs))
    print("\n[%d] %s idx=%s name=%s src=%s n=%d x=[%.0f,%.0f] y=[%.0f,%.0f] x@829=%.1f" % (
        i, ln["kind"], ln.get("index"), ln.get("name"), ln.get("src"), len(pts),
        xs.min(), xs.max(), ys.min(), ys.max(), xm))
    prof = " ".join("y%.0f:x%.0f" % (y, np.interp(y, ys, xs))
                    for y in range(int(ys.min()), int(ys.max())+1, max(1,(int(ys.max())-int(ys.min()))//6)))
    print("    剖面:", prof)
    print("    fills=%s unfilled=%s trims=%s extends=%s" % (
        ln.get("fills"), (ln.get("unfilled") or [])[:3], ln.get("trims"), ln.get("extends")))
