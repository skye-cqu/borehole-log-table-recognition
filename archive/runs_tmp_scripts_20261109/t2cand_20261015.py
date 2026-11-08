# -*- coding: utf-8 -*-
"""1042:阶段4候选里有没有 真厚|柱状 那条界(表头带 x~709)?数据源神圣判定的前提。"""
import sys, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
from src.table import col_segments

p = paths.CANDIDATE_COORD_DIR / "钻孔柱状图1042.json"
print("候选文件:", p, "存在=", p.exists())
d = json.loads(p.read_text(encoding="utf-8"))
print("顶层键:", list(d.keys()))
vs = [s for s in d["lines"] if s.get("direction") == "vertical"]
print("竖线候选数:", len(vs))
if vs: print("样本键:", list(vs[0].keys()))

print()
print("== 竖线候选:表头带(y<1000)内 x∈[600,850] ==")
for s in vs:
    pts = s.get("pts") or []
    if not pts: continue
    a = np.array(pts, float)
    top = a[a[:,1] < 1100]
    if len(top) == 0: continue
    xm = float(np.median(top[:,0]))
    if 600 <= xm <= 850:
        print("  id=%-8s label=%-10s n=%-4d x=[%.0f,%.0f] y=[%.0f,%.0f] 表头段x=%.0f" % (
            s.get("id"), s.get("label"), len(a), a[:,0].min(), a[:,0].max(),
            a[:,1].min(), a[:,1].max(), xm))

print()
print("== 全部竖线候选按 x 排序(中位) ==")
rows = []
for s in vs:
    pts = s.get("pts") or []
    if not pts: continue
    a = np.array(pts, float)
    rows.append((float(np.median(a[:,0])), s.get("id"), s.get("label"), len(a), a[:,0].min(), a[:,0].max(), a[:,1].min(), a[:,1].max()))
rows.sort()
for xm, i, lb, n, x0, x1, y0, y1 in rows:
    print("  x=%-7.0f id=%-8s label=%-10s n=%-4d x=[%.0f,%.0f] y=[%.0f,%.0f]" % (xm, i, lb, n, x0, x1, y0, y1))
