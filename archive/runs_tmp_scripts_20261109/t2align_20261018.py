# -*- coding: utf-8 -*-
"""keep↔sep_pts 索引对齐校验:在表头带 ymid 处插值 sep_pts 折线,与 keep.x_in_band 比对。"""
import json, sys
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
A = paths.RUNS_DIR / "table_reconstruct"
bad_total = 0
for f in sorted(A.glob("*_表头映射.json")):
    stem = f.name[:-len("_表头映射.json")]
    w = json.loads(f.read_text(encoding="utf-8"))
    sp = w.get("sep_pts")
    if not sp:
        print("%-16s 无 sep_pts(旧版映射)" % stem[-4:]); continue
    band = w["band"]; ymid = (band[0] + band[1]) / 2.0
    xs_at = [float(np.interp(ymid, p["ys"], p["xs"])) for p in sp]
    bad = []
    for c in w.get("keep") or []:
        for k, side in (("left_sep", 0), ("right_sep", 1)):
            i = c[k]
            if i is None or i < 0: continue
            if i >= len(xs_at): bad.append("%s.%s=%d 越界" % (c["name"], k, i)); continue
            d = abs(xs_at[i] - c["x_in_band"][side])
            if d > 30: bad.append("%s.%s=%d 差%.0fpx" % (c["name"], k, i, d))
    if bad:
        bad_total += len(bad)
        print("%-16s ✗ %s" % (stem[-4:], "; ".join(bad)))
    else:
        print("%-16s ✓ 对齐(%d 界)" % (stem[-4:], len(sp)))
print("\n总错位数 =", bad_total)
