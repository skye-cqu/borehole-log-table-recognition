# -*- coding: utf-8 -*-
"""门禁5 的成品核验：直接读 runs/ 里的 行判定.json，量"带内拽偏"还剩几条。

为什么不复用 A/B 的数：A/B 那三档是自己重建链跑的（还跳过了 1020/1042），
这里量的是**真正落盘的产物**——不读原图、不重跑建链，秒级。
拽偏 = 同一条层界在柱状带里的中位高度 − 带外的中位高度（先扣掉全表斜率），>0.35 行高记一条。
用法: python runs/tmp/verify_band.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                              # noqa: E402
from src.table.track_columns import x_at                            # noqa: E402


def drag(rows, band, row_h, s0):
    """(被拽偏的条数, 最狠的三条 (倍数, y), 可比条数)。band=None → 无从判，返回 (0,[],0)。"""
    west, east = band if band else (None, None)
    n = reach = 0
    worst = []
    for r in rows:
        p = np.asarray(r["poly"], float)
        if len(p) < 3 or west is None:
            continue
        ym = float(np.median(p[:, 1]))
        wl, er = x_at(west, ym), x_at(east, ym)
        inb = (p[:, 0] >= wl) & (p[:, 0] <= er)
        if inb.sum() < 3 or (~inb).sum() < 3:
            continue
        reach += 1
        q = p[:, 1] - s0 * p[:, 0]
        d = float(np.median(q[inb]) - np.median(q[~inb]))
        if abs(d) > 0.35 * row_h:
            n += 1
            worst.append((round(abs(d) / row_h, 2), int(r["y_at_mid"])))
    return n, sorted(worst, reverse=True)[:3], reach


def main():
    print(f"{'图':<6}{'层界':>6}{'带内可比':>9}{'拽偏':>6}{'最狠的三条(行高,y)':>26}")
    tn = tr_ = 0
    bad = []
    for fp in sorted((paths.RUNS_DIR / "table_reconstruct").glob("*_行判定.json")):
        stem = fp.name[:-len("_行判定.json")]
        d = json.load(open(fp, encoding="utf-8"))
        west, east, src = tr.content_band(stem)
        n, worst, reach = drag(d["rows"], None if west is None else (west, east),
                               float(d["row_h"]), float(d["slope_med"]))
        tn += n; tr_ += len(d["rows"])
        if n:
            bad.append((stem[-4:], n, worst))
        print(f"{stem[-4:]:<6}{len(d['rows']):>7}{reach:>9}{n:>7}"
              f"{'  '.join(f'{w}@{y}' for w, y in worst):>28}  {src}")
    print(f"\n合计 层界{tr_} 带内拽偏{tn} 条")
    for c, n, worst in bad:
        print(f"  {c}: {n} 条 → {worst}")


if __name__ == "__main__":
    main()
