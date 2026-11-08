# -*- coding: utf-8 -*-
"""带缘准不准：冻结 vs 平行续接，拿阶段4 竖向 high 段当"原图真竖线"量距离。

用法: python runs/tmp/diag_band_acc.py            # 30 张
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                              # noqa: E402


def x_at_y(pts, y):
    p = np.asarray(pts, float)
    p = p[np.argsort(p[:, 1])]                      # 候选段的点常是自上而下或自下而上，先排
    if p[0, 1] <= y <= p[-1, 1]:
        return float(np.interp(y, p[:, 1], p[:, 0]))
    return None


codes = [f"1{c}" for c in "015 016 017 018 019 020 021 022 023 024 025 026 027 028 029 030 "
                         "031 032 033 034 035 036 037 038 039 040 041 042 043 044".split()]
tot = {"freeze": [], "anchor": []}
print(f"{'图':6s} {'断口以下采样数':>10s}  冻结 中位/90分位  续接 中位/90分位")
for code in codes:
    stem = f"钻孔柱状图{code}"
    fp = paths.CANDIDATE_COORD_DIR / f"{stem}.json"
    if not fp.exists():
        continue
    cj = json.load(open(fp, encoding="utf-8"))
    vs = [s for s in cj["lines"] if s["direction"] == "vertical" and s["label"] == "high"
          and s["length"] >= 150]
    cols = sorted(json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json",
                                 encoding="utf-8"))["columns"], key=lambda c: c["x_at_mid"])
    segd = {s["id"]: s for s in cj["lines"] if s["direction"] == "vertical" and s["label"] == "high"}
    ch = [tr.load_chain({"segment_ids": c["segment_ids"]}, segd)[0] for c in cols]
    west, east, src = tr.content_band(stem)          # 已续接
    if west is None:
        continue
    xs = [c["x_at_mid"] for c in cols]
    _, j = max((b - a, i) for i, (a, b) in enumerate(zip(xs, xs[1:])))
    orig = {0: ch[j - 1], 1: ch[j]}
    if xs[j] - xs[j - 1] < tr.BAND_MIN:
        orig = {0: ch[j], 1: None}
    d = {"freeze": [], "anchor": []}
    for which, ext in ((0, west), (1, east)):
        o = orig[which]
        if o is None:
            continue
        y0 = float(np.asarray(o, float)[-1, 0])
        for y in range(int(y0) + 50, int(cj["height"]), 100):
            real = [v for v in (x_at_y(s["points"], y) for s in vs)
                    if v is not None and abs(v - tr.edge_at(o, y)) < 400]
            if not real:
                continue
            # 两条规则各自量"离最近一条真竖线有多远"：落在两条线中间 = 图上根本没这条线
            for kk, e in (("freeze", o), ("anchor", ext)):
                x = tr.edge_at(e, y)
                d[kk].append(min(abs(v - x) for v in real))
    for kk in tot:
        tot[kk] += d[kk]
    if d["freeze"]:
        f, a = np.array(d["freeze"]), np.array(d["anchor"])
        print(f"{code:6s} {len(f):10d}  {np.median(f):6.0f}/{np.percentile(f,90):6.0f}"
              f"  {np.median(a):6.0f}/{np.percentile(a,90):6.0f}   {src}")
for kk in tot:
    v = np.array(tot[kk])
    print(f"30 张合计 {kk}: 中位 {np.median(v):.0f}  90分位 {np.percentile(v,90):.0f}  "
          f"最大 {v.max():.0f}  n={len(v)}")
