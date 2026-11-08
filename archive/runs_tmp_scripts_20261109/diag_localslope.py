# -*- coding: utf-8 -*-
"""斜率该整体量还是逐窗量：拿"局部斜率中位数"能不能把真弯线和拼歪线分开。

门禁按整体最小二乘斜率判，1040 误杀一条真行线(y=20654，离墨 0.0%，跨 2526px)：
那条行线是弯的，两端落差大但每一小段都跟表平行。1027 的坏线(y=10886)是"一路斜着爬"，
每一小段都离全表中位斜率很远。→ 整体斜率分不开，逐窗斜率可能分得开。
打三条读数：整体斜率、300px 窗斜率中位数、窗斜率 p90，配原图离墨%。

用法: python runs/tmp/diag_localslope.py 1027 1040
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
from src.table.track_columns import x_at                            # noqa: E402
from src.table import track_rows as tr                              # noqa: E402
import yardstick as Y                                               # noqa: E402

SRC = Path(os.environ.get("SRC", str(ROOT / "runs" / "table_reconstruct")))
DX = 300


def win_slopes(pl, s0, dx=DX):
    """折线按 dx 切窗，每窗最小二乘斜率（减全表中位斜率）。

    先铺到 1px 网格再切：poly 是 approxPolyDP 简化过的，2000px 只剩几个顶点，
    直接按顶点切窗 = 窗里常常只有接缝那一段，读数能到 -20%（第一版就是这么错的）。
    """
    xs = np.arange(pl[0, 0], pl[-1, 0] + 1)
    if len(xs) < 4:
        return np.array([])
    ys = np.interp(xs, pl[:, 0], pl[:, 1])
    return np.array([tr.slope_of(np.column_stack([xs[a:a + dx], ys[a:a + dx]])) - s0
                     for a in range(0, len(xs) - dx, int(dx / 2))])


def offink(ruling, rec):
    H, W = ruling.shape
    x0, x1 = int(rec["x"][0]), int(rec["x"][1])
    ds = []
    for x in np.linspace(x0 + 10, min(x1 - 10, W - 2), 60):
        y = tr.row_y(rec, x)
        band = ruling[max(0, int(y) - 60):min(H, int(y) + 60), int(x)]
        idx = np.flatnonzero(band)
        ds.append(float(np.abs(idx + max(0, int(y) - 60) - y).min()) if len(idx) else np.nan)
    return float(np.mean([not np.isfinite(v) or v > 5 for v in ds])) * 100


for code in [a for a in sys.argv[1:] if a.isdigit()] or ["1027", "1040"]:
    stem = f"钻孔柱状图{code}"
    rd = json.loads((SRC / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    ruling, _ = Y.masks(stem)
    s0 = rd["slope_med"]
    lines = sorted(rd["rows"] + rd.get("off_grid", []), key=lambda r: -abs(r["slope"]))
    print(f"\n=== {code} 中位斜率 {s0:+.4f}，层界 {len(rd['rows'])} + 剔 {len(rd.get('off_grid', []))} ===")
    print(f"{'y':>7}{'整体':>8}{'窗中位':>8}{'窗p90':>8}{'离墨%':>7}{'跨px':>7}{'链':>3}{'身份':>6}")
    for r in lines[:14]:
        ws = win_slopes(np.asarray(r["poly"], float), s0)
        if not len(ws):
            continue
        who = "已剔" if any(abs(o["y_at_mid"] - r["y_at_mid"]) < 6 for o in rd.get("off_grid", [])) \
            else "层界"
        print(f"{r['y_at_mid']:>7.0f}{r['slope']:>8.1%}{np.median(ws):>8.1%}"
              f"{np.percentile(ws, 90):>8.1%}{offink(ruling, r):>7.1f}{r['span']:>7}"
              f"{r['n_chains']:>3}{who:>6}")
