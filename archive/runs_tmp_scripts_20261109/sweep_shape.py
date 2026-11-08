# -*- coding: utf-8 -*-
"""线级形状门禁该长什么样：三种形状缺陷要三把尺子，一把会漏。

离线跑（读无门禁快照的 poly，不重跑管线），逐条线算三个读数，配原图离墨%：
  窗中位斜率 300px 窗斜率的中位数 → 抓"一路斜着爬"(1027 y=10886：整体-7.6%、窗中位-3.7%)
  台阶 step  Δx<60px 的相邻顶点落差 → 抓"链内部跳行"(1027 y=3514：整体-8.6% 但窗中位 0.7%)
  整体斜率   最小二乘 → 会被"真而弯"的行线骗到(1040 y=20654：整体 5.5%、窗中位-0.8%、离墨 0.0%)
好坏标签用原图墨：离墨≤10% = 贴在横线墨上(真行)，>15% = 线上没墨(坏)。
枚举阈值组合，看"消掉的坏线"和"误杀的真行"。

用法: python runs/tmp/sweep_shape.py 1027 1040     # 快照目录用 SRC，默认 runs/tmp/ab/ref
"""
from __future__ import annotations

import itertools
import json
import os
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.table import track_rows as tr                              # noqa: E402
import yardstick as Y                                               # noqa: E402

SRC = Path(os.environ.get("SRC", str(ROOT / "runs" / "tmp" / "ab" / "ref")))
DX = 300
GOOD, BAD = 10.0, 15.0          # 离墨% 两档：≤10 判真行，>15 判坏线


def win_med(pl, s0, dx=DX):
    """300px 窗斜率的中位数（减全表中位斜率）。先铺 1px 网格：poly 只剩几个顶点。"""
    xs = np.arange(pl[0, 0], pl[-1, 0] + 1)
    if len(xs) < 2 * dx:
        return 0.0
    ys = np.interp(xs, pl[:, 0], pl[:, 1])
    ws = [tr.slope_of(np.column_stack([xs[a:a + dx], ys[a:a + dx]])) - s0
          for a in range(0, len(xs) - dx, int(dx / 2))]
    return float(np.median(ws))


def feats(code):
    stem = f"钻孔柱状图{code}"
    rd = json.loads((SRC / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    ruling, _ = Y.masks(stem)
    H, W = ruling.shape
    s0 = rd["slope_med"]
    row_h = max(rd["row_h"], 1.0)
    out = []
    for r in rd["rows"]:
        pl = np.asarray(r["poly"], float)
        x0, x1 = int(r["x"][0]), int(r["x"][1])
        ds = []
        for x in np.linspace(x0 + 10, min(x1 - 10, W - 2), 60):
            y = tr.row_y(r, x)
            band = ruling[max(0, int(y) - 60):min(H, int(y) + 60), int(x)]
            idx = np.flatnonzero(band)
            ds.append(float(np.abs(idx + max(0, int(y) - 60) - y).min())
                      if len(idx) else np.nan)
        out.append({"y": r["y_at_mid"], "span": r["span"], "step": r["step"] / row_h,
                    "glob": abs(r["slope"]), "win": abs(win_med(pl, s0)),
                    "ink": float(np.mean([not np.isfinite(v) or v > 5 for v in ds])) * 100})
    return out, row_h


for code in [a for a in sys.argv[1:] if a.isdigit()] or ["1027", "1040"]:
    F, row_h = feats(code)
    good = [f for f in F if f["ink"] <= GOOD]
    bad = [f for f in F if f["ink"] > BAD]
    print(f"\n=== {code} 层界 {len(F)}：真行(离墨≤{GOOD:.0f}%) {len(good)}，"
          f"坏线(离墨>{BAD:.0f}%) {len(bad)}，行高 {row_h:.0f}px ===")
    print(f"{'读数':<12}" + "".join(f"{q:>10}" for q in ("真行中位", "真行p90", "真行最大",
                                                         "坏线中位", "坏线p90", "坏线最大")))
    for k, lab in (("glob", "整体斜率"), ("win", "窗中位斜率"), ("step", "台阶/行高")):
        g = np.array([f[k] for f in good]) * (1 if k != "step" else 1)
        b = np.array([f[k] for f in bad])
        print(f"{lab:<12}{np.median(g):>10.2f}{np.percentile(g, 90):>10.2f}{g.max():>10.2f}"
              f"{np.median(b):>10.2f}{np.percentile(b, 90):>10.2f}{b.max():>10.2f}")
    print(f"{'阈值组合':<16}{'杀真行':>7}{'消坏线':>7}{'剩坏线':>7}")
    for wg, ws in itertools.product((0.02, 0.03, 0.04, 0.06), (0.25, 0.4, 0.6, 9.0)):
        kill = [f for f in F if f["win"] > wg or f["step"] > ws]
        print(f"窗中位>{wg:.0%} 台阶>{ws:.1f}"
              f"{sum(1 for f in kill if f['ink'] <= GOOD):>7}"
              f"{sum(1 for f in kill if f['ink'] > BAD):>7}"
              f"{len(bad) - sum(1 for f in kill if f['ink'] > BAD):>7}")
    # 剩下那些形状完全正常的坏线长什么样：跨度越短越像"凭空一小截"，越长越像"贴错行"
    print("  坏线明细(离墨>15%)：")
    for f in sorted(bad, key=lambda f: -f["ink"]):
        print(f"    y={f['y']:7.0f} 离墨{f['ink']:5.1f}% 跨{f['span']:5d}px "
              f"整体{f['glob']:.1%} 窗中位{f['win']:.1%} 台阶{f['step']:.2f}行高")
