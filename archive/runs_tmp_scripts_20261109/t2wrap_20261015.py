# -*- coding: utf-8 -*-
"""T2 收尾核查:(a)全30张相邻界间距<20px 的图 (b)1042 track 源边界 (c)1042 表头带内阶段4 high 竖线。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
RECON = paths.RUNS_DIR/"table_reconstruct"

print("== (a) 相邻 sep 间距 < 20px 的图(双描/幽灵线嫌疑) ==")
for p in sorted(RECON.glob("*_表头映射.json")):
    hm = json.loads(p.read_text(encoding="utf-8"))
    xs = hm.get("sep_x_band") or []
    if len(xs) < 2: continue
    close = [(a, b, b-a) for a, b in zip(xs, xs[1:]) if b-a < 20]
    if close:
        print("   %-21s %s" % (p.name.replace("_表头映射.json",""), ["%.1f/%.1f(%.1fpx)" % c for c in close]))
print("   (无输出 = 只有 1042 有)")

print()
print("== (b) 1042 track 源(_列判定.json) ==")
tp = paths.TRACK_GROUP_DIR/"钻孔柱状图1042_列判定.json"
print("  存在:", tp.exists())
if tp.exists():
    tj = json.loads(tp.read_text(encoding="utf-8"))
    print("  顶层键:", list(tj.keys())[:14])
    for k in ("columns", "lines", "seps", "column_bounds", "groups"):
        if k in tj:
            v = tj[k]
            print("  %s: %s" % (k, ("len=%d" % len(v)) if isinstance(v, list) else type(v).__name__))
            if isinstance(v, list) and v and isinstance(v[0], dict):
                print("     首元素键:", list(v[0].keys()))
                for it in v[:14]:
                    print("       %s" % json.dumps({kk: (round(vv,1) if isinstance(vv,float) else vv) for kk, vv in it.items() if not isinstance(vv,(list,dict))}, ensure_ascii=False)[:190])
            break

print()
print("== (c) 1042 表头带内 x∈[640,910] 的阶段4 high 竖线 ==")
cj = json.loads((paths.CANDIDATE_COORD_DIR/"钻孔柱状图1042.json").read_text(encoding="utf-8"))
for s in cj["lines"]:
    if s.get("direction") != "vertical" or s.get("label") != "high": continue
    pts = np.array(s.get("points") or [], float)
    if len(pts) < 2: continue
    xm = float(np.median(pts[:,0]))
    if not (640 <= xm <= 910): continue
    y0, y1 = float(pts[:,1].min()), float(pts[:,1].max())
    inband = not (y1 < 747 or y0 > 911)
    print("   id=%-8s x=%-6.1f y=[%6.0f,%6.0f] len=%-5.0f score=%.2f %s" % (
        s.get("id"), xm, y0, y1, float(s.get("length") or 0), float(s.get("final_score") or 0),
        "<-覆盖表头带" if inband else ""))
