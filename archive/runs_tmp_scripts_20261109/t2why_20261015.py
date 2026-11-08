# -*- coding: utf-8 -*-
"""1042:为何 x=709 真厚|柱状 界没进 _分割线.json?追阶段4候选链。"""
import json, sys
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

sp = json.loads((paths.RUNS_DIR/"table_reconstruct"/"钻孔柱状图1042_分割线.json").read_text(encoding="utf-8"))
print("== _分割线.json 顶层键 ==", list(sp.keys()))
lines = sp["lines"]
print("lines 条数 =", len(lines))
print()
print("kind        index  name/src           x@顶   x@中   x@底   n点   y范围")
for i, ln in enumerate(lines):
    pts = np.array([p for seg, _ in ln.get("parts", []) for p in seg] or [[0,0]], float)
    if len(pts) == 0: continue
    pts = pts[np.argsort(pts[:,1])]
    ys = pts[:,1]
    x_top, x_mid, x_bot = pts[0,0], pts[len(pts)//2,0], pts[-1,0]
    print("[%2d] %-8s %-6s %-18s %-6.0f %-6.0f %-6.0f %-4d  [%.0f,%.0f]" % (
        i, ln.get("kind"), ln.get("index"), str(ln.get("name") or ln.get("src")),
        x_top, x_mid, x_bot, len(pts), ys.min(), ys.max()))

print()
print("== 任何 parts/bridged 点落在 x∈[700,720] 的行 ==")
for i, ln in enumerate(lines):
    allp = [p for seg, _ in ln.get("parts", []) for p in seg] + [p for seg, _ in ln.get("bridged", []) for p in seg]
    hit = [p for p in allp if 700 <= p[0] <= 720]
    if hit:
        ys = [p[1] for p in hit]
        print("   [%2d] kind=%-8s index=%-6s 命中 %d 点 y=[%.0f,%.0f]" % (i, ln.get("kind"), ln.get("index"), len(hit), min(ys), max(ys)))
print("   (无输出 = 709 界确实不在 _分割线.json)")

print()
print("== 阶段4 候选:与 id=23397(x=709,y=755) 同一 x 带的链 ==")
cj = json.loads((paths.CANDIDATE_COORD_DIR/"钻孔柱状图1042.json").read_text(encoding="utf-8"))
vs = [s for s in cj["lines"] if s.get("direction") == "vertical"]
near = []
for s in vs:
    pts = np.array(s.get("points") or [], float)
    if len(pts) < 2: continue
    xm = float(np.median(pts[:,0]))
    if 700 <= xm <= 725:
        near.append((float(pts[:,1].min()), float(pts[:,1].max()), xm, s.get("id"), s.get("label"),
                     float(s.get("length") or 0), float(s.get("final_score") or 0)))
near.sort()
print("x∈[700,725] 候选 %d 条(按 y0 升序):" % len(near))
for y0, y1, xm, i, lb, ln_, sc in near[:40]:
    print("   y=[%6.0f,%6.0f] x=%-6.0f id=%-8s %-6s len=%-5.0f score=%.2f" % (y0, y1, xm, i, lb, ln_, sc))
if len(near) > 40: print("   ... 共 %d 条" % len(near))
