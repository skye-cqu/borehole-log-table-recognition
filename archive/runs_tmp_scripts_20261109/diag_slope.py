# -*- coding: utf-8 -*-
"""诊断A（用户提的门禁）：层界折线的斜率是不是歪了。

对每条层界：用 poly 最小二乘拟合斜率 s（px/px），再取
  · 全表中位斜率 s0（稳健基准，"全表大部分行线的斜率"）
  · 线内最大台阶 = 相邻顶点（Δx<60px）间 |Δy| 最大值 → 上一行/下一行被连起来的直接指纹
并按用户建议的两档阈值 3% / 5% 数出超差条数。
关键校验：斜率超差与"离墨"（yardstick 的客观读数）是不是同一批线——门禁能不能真抓到坏线。

用法: python runs/tmp/diag_slope.py [1027 1040 ...]     # 无参数=30 张
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
import yardstick as Y                                               # noqa: E402


def stats(recs):
    """poly → 斜率(px/px) + 线内最大台阶(px)。"""
    s, step = [], []
    for r in recs:
        p = np.asarray(r["poly"], float)
        if len(p) < 2 or p[-1, 0] - p[0, 0] < 50:
            s.append(np.nan)
            step.append(0.0)
            continue
        s.append(float(np.polyfit(p[:, 0], p[:, 1], 1)[0]))
        dx, dy = np.diff(p[:, 0]), np.abs(np.diff(p[:, 1]))
        step.append(float(dy[dx < 60].max()) if (dx < 60).any() else 0.0)
    return np.array(s), np.array(step)


def ink_off(recs, code):
    """每条线的离墨采样%（与 yardstick 同一把尺，逐条落到线上）。"""
    stem = f"钻孔柱状图{code}"
    ruling, _ = Y.masks(stem)
    W = ruling.shape[1]
    out = []
    for r in recs:
        x0, x1 = int(r["x"][0]), int(r["x"][1])
        off = n = 0
        for x in np.linspace(x0 + 10, min(x1 - 10, W - 2), Y.SAMPLE):
            xi = int(x)
            y = Y.line_y(r, x)
            band = ruling[max(0, int(y) - Y.SEARCH):int(y) + Y.SEARCH, xi]
            idx = np.flatnonzero(band)
            n += 1
            if not len(idx) or np.abs(idx + max(0, int(y) - Y.SEARCH) - y).min() > 5:
                off += 1
        out.append(off / max(n, 1) * 100)
    return np.array(out)


for code in [a for a in sys.argv[1:] if a.isdigit()] or \
        sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob("*.json")):
    stem = f"钻孔柱状图{code}"
    rd = json.loads((paths.RUNS_DIR / "table_reconstruct" /
                     f"{stem}_行判定.json").read_text(encoding="utf-8"))
    recs = rd["rows"]
    s, step = stats(recs)
    s0 = float(np.nanmedian(s))
    dev = np.abs(s - s0)
    off = ink_off(recs, code)
    bad = off > 10                                    # 离墨>10% = 坏线（yardstick 同口径）
    print(f"\n{code}: 层界 {len(recs)} 条  全表中位斜率 s0={s0:+.4f}"
          f"（{s0 * 100:+.1f}%，即每 100px 宽降 {s0 * 100:.1f}px）")
    print(f"    斜率偏离 |s-s0|: 中位 {np.median(dev) * 100:.1f}%  "
          f"p90 {np.percentile(dev, 90) * 100:.1f}%  最大 {dev.max() * 100:.0f}%")
    for t in (0.03, 0.05):
        hit = dev > t
        print(f"    阈值 {t * 100:.0f}%: 超差 {hit.sum()} 条  "
              f"其中判为坏线 {int((hit & bad).sum())} 条  "
              f"漏掉的坏线 {int((~hit & bad).sum())}/{bad.sum()} 条")
    hit = step > 15
    print(f"    线内台阶>15px: {hit.sum()} 条（其中坏线 {int((hit & bad).sum())}）")
    worst = np.argsort(-off)[:5]
    for i in worst:
        r = recs[i]
        print(f"      y={r['y_at_mid']:<7} x={r['x'][0]}-{r['x'][1]:<6} 链{r['n_chains']} "
              f"斜率{s[i] * 100:+6.1f}%(偏{dev[i] * 100:5.1f}%) 台阶{step[i]:5.0f}px "
              f"离墨{off[i]:3.0f}%")
