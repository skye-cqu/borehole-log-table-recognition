# -*- coding: utf-8 -*-
"""为什么"框内"档一条层界都没有：把每个簇的右界/覆盖率打出来，和生产档并排看。

用法: python runs/tmp/diag_frame.py 1018
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                              # noqa: E402
import ab_frame as AF                                               # noqa: E402

code = sys.argv[1] if len(sys.argv) > 1 else "1018"
stem = f"钻孔柱状图{code}"

def dump(tag, ch):
    print(f"--- {tag}: tab_l={ch['tab_l']:.0f} tab_r={ch['tab_r']:.0f} "
          f"tab_w={ch['tab_w']:.0f} col={'None' if ch['col'] is None else ''}")
    col = ch["col"]
    if isinstance(col, np.ndarray):
        print(f"    col ndarray shape={col.shape} 首={col[0]} 末={col[-1]} "
              f"c0范围[{col[:,0].min():.0f},{col[:,0].max():.0f}] "
              f"c1范围[{col[:,1].min():.0f},{col[:,1].max():.0f}]")
    else:
        print(f"    col type={type(col)}")
    cl = tr.cluster(ch["items"], tr.LINE_TOL)
    print(f"    簇 {len(cl)} 个，前 12 个:")
    for c in cl[:12]:
        pl = tr.polyline(c["mem"])
        x0, x1 = c["x"]
        b = tr.boundary_x(pl, col, x0, x1) if col is not None else ch["tab_r"]
        bb = float(np.clip(b, ch["tab_l"], ch["tab_r"]))
        cn = tr.cover(c["mem"], ch["tab_l"], bb)
        cd = tr.cover(c["mem"], bb, ch["tab_r"])
        print(f"      y={np.median(pl[:,1]):7.0f} span={x1-x0:5.0f} "
              f"x=[{x0:5.0f},{x1:5.0f}] rawB={b:7.0f} B={bb:7.0f} "
              f"cov_num={cn:6.2f} cov_desc={cd:5.2f} n_mem={len(c['mem'])}")


dump("生产", tr.load_chains(stem))

fr = AF.frame(stem)
L, R = fr
cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
src = [s for s in cj["lines"] if s["direction"] == "horizontal" and s["label"] == "high"]
west, east, _ = tr.content_band(stem)
band = (west, east) if west is not None else None
kept = []
for s in src:
    p = np.asarray(s["points"], float)
    if band is not None and tr.in_band(p, band):
        continue
    q = AF.clip(p, L, R)
    if q is None:
        continue
    s = dict(s)
    s["points"] = q.tolist()
    s["length"] = float(q[-1, 0] - q[0, 0])
    kept.append(s)
dump("框内", AF.build(stem, kept, cj, L, R))
