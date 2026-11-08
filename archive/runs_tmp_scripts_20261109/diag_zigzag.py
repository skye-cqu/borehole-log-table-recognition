# -*- coding: utf-8 -*-
"""按"线本身走没走在横线墨上"给每条层界定性,找出不合格线的真实形态。

三条独立读数(同一把尺 yardstick 的 ruling 墨迹掩膜):
  离墨%  = 采样处 ±60px 内找不到横线墨 或 距离 >5px 的占比   → 线不在横线上
  压字%  = 画的线(±2px)穿过字/短笔的占比                    → 线挡住了字
  局部斜 = 折线在 100px 横向窗内的 |Δy| 最大值(换算成 %)      → 用户说的"斜率波动"
交叉表看:不合格线是不是集中在"局部斜大"那一堆。

用法: python runs/tmp/diag_zigzag.py [1027 1040 ...]
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
from src.table.track_rows import row_y                              # noqa: E402
import yardstick as Y                                               # noqa: E402

SRC = Path(os.environ.get("SRC", ROOT / "runs" / "table_reconstruct"))
DX = 100          # 局部斜的横向窗(px)
NS = 60


def local_jump(poly):
    """折线在 DX 横向窗内的最大竖向跳变(px)。"""
    p = np.asarray(poly, float)
    j = 0.0
    for i in range(len(p)):
        m = (p[:, 0] > p[i, 0]) & (p[:, 0] <= p[i, 0] + DX)
        if m.any():
            j = max(j, float(np.abs(p[m, 1] - p[i, 1]).max()))
    return j


def per_line(code):
    stem = f"钻孔柱状图{code}"
    rd = json.loads((SRC / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    ruling, glyph = Y.masks(stem)
    H, W = ruling.shape
    out = []
    for r in rd["rows"]:
        x0, x1 = int(r["x"][0]), int(r["x"][1])
        xs = np.linspace(x0 + 10, min(x1 - 10, W - 2), NS)
        off = ink = press = 0
        for x in xs:
            xi = int(x)
            y = row_y(r, x)
            band = ruling[max(0, int(y) - Y.SEARCH):int(y) + Y.SEARCH, xi]
            idx = np.flatnonzero(band)
            d = float(np.abs(idx + max(0, int(y) - Y.SEARCH) - y).min()) if len(idx) else np.inf
            ink += np.isfinite(d) and d <= 5.0
            off += not (np.isfinite(d) and d <= 5.0)
            press += bool(glyph[int(y) - 2:int(y) + 3, xi].any())
        out.append({"y": r["y_at_mid"], "n": r["n_chains"], "cov": r["cov_num"],
                    "off": off / NS * 100, "press": press / NS * 100,
                    "jump": local_jump(r["poly"]), "span": r["x"][1] - r["x"][0]})
    return out


for code in [a for a in sys.argv[1:] if a.isdigit()] or ["1027"]:
    L = per_line(code)
    bad = [x for x in L if x["off"] > 10]
    print(f"\n{code}: 层界 {len(L)} 条,离墨>10% 的 {len(bad)} 条,压字>30% 的 "
          f"{sum(1 for x in L if x['press'] > 30)} 条")
    print(f"{'局部跳变px':>12}{'线数':>6}{'其中离墨>10%':>13}{'离墨%中位':>10}{'压字%中位':>10}")
    for lo, hi in ((0, 8), (8, 15), (15, 25), (25, 40), (40, 999)):
        g = [x for x in L if lo <= x["jump"] < hi]
        if not g:
            continue
        print(f"{f'{lo}-{hi}':>12}{len(g):>6}{sum(1 for x in g if x['off'] > 10):>13}"
              f"{np.median([x['off'] for x in g]):>10.0f}{np.median([x['press'] for x in g]):>10.0f}")
    print("  最坏的 8 条:")
    for x in sorted(L, key=lambda q: -q["off"])[:8]:
        print(f"    y={x['y']:<9} 链{x['n']} 跨{x['span']:>5}px cov={x['cov']:.2f} "
              f"离墨{x['off']:3.0f}% 压字{x['press']:3.0f}% 局部跳{x['jump']:4.0f}px")
