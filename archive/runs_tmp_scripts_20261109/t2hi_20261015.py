# -*- coding: utf-8 -*-
"""1042:阶段4 全部 label=high 竖线候选(全 y 范围),看 真厚|柱状 界是否全程有候选。"""
import json, sys
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

d = json.loads((paths.CANDIDATE_COORD_DIR/"钻孔柱状图1042.json").read_text(encoding="utf-8"))
vs = [s for s in d["lines"] if s.get("direction") == "vertical"]
print("竖线候选总数:", len(vs))
from collections import Counter
print("label 分布:", Counter(s.get("label") for s in vs))

hi = []
for s in vs:
    pts = np.array(s.get("points") or [], float)
    if len(pts) < 2: continue
    if s.get("label") != "high": continue
    hi.append({"id": s.get("id"), "x": float(np.median(pts[:,0])),
               "x0": float(pts[:,0].min()), "x1": float(pts[:,0].max()),
               "y0": float(pts[:,1].min()), "y1": float(pts[:,1].max()),
               "n": len(pts), "len": float(s.get("length") or 0),
               "score": float(s.get("final_score") or 0), "band": s.get("band_id")})
hi.sort(key=lambda r: (r["x"], r["y0"]))
print()
print("== label=high 竖线候选 %d 条 ==" % len(hi))
print("id        x中位  x范围        y范围            len  score band")
for r in hi:
    print("%-9s %-6.0f [%4.0f,%4.0f] [%6.0f,%6.0f] %-4.0f %.2f %s" % (
        r["id"], r["x"], r["x0"], r["x1"], r["y0"], r["y1"], r["len"], r["score"], r["band"]))

print()
print("== x∈[690,800] 的 high 候选(真厚|柱状 界) ==")
sel = [r for r in hi if 690 <= r["x"] <= 800]
for r in sorted(sel, key=lambda r: r["y0"]):
    print("   id=%-9s x=%-6.0f y=[%.0f,%.0f] len=%.0f score=%.2f" % (
        r["id"], r["x"], r["y0"], r["y1"], r["len"], r["score"]))
print("   共 %d 条, y 覆盖 [%.0f,%.0f]" % (
    len(sel), min(r["y0"] for r in sel) if sel else -1, max(r["y1"] for r in sel) if sel else -1))
