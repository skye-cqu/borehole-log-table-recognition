# -*- coding: utf-8 -*-
"""1035 在删带这一档 层界 166→163、漏线 2→7 —— 这张是唯一变差的，点名看是哪几条。

用法: python runs/tmp/diag_band_one.py 1035
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                              # noqa: E402
import yardstick as Y                                               # noqa: E402
import diag_missed as M                                             # noqa: E402
from sweep_gates import offink                                      # noqa: E402


def arms(stem):
    real = tr.content_band
    tr.content_band = lambda s: (None, None, None)
    now = tr.load_chains(stem)
    tr.content_band = real
    return now, tr.load_chains(stem)


def main(code):
    stem = f"钻孔柱状图{code}"
    ruling = Y.masks(stem)[0]
    for name, ch in zip(("现状", "删带"), arms(stem)):
        o = tr.assemble(ch)
        oi = offink(ruling, o["rows"])
        print(f"\n=== {name} === 层界{len(o['rows'])} 行高{o['row_h']:.0f} "
              f"带内段剔{o['n_band_segments']}({o['band_src']})")
        for r, v in zip(o["rows"], oi):
            yield_rows.setdefault(name, {})[round(r["y_at_mid"])] = (v, r["cov_num"], r["x"])
        miss = M.missed(o, ruling)
        print("漏线带 " + " ".join(f"{int(y)}" for y, c, n, s in miss))
        for y, c, n, s in miss:
            print(f"   y={int(y)} 墨覆盖{c:.0%} 最近层界差{n:.0f}px 子行线cov={s}")
    a, b = yield_rows["现状"], yield_rows["删带"]
    for lo, hi in [(12300, 13500)]:
        print(f"\n区间 {lo}~{hi}  现状: {' '.join(str(y) for y in sorted(a) if lo <= y <= hi)}")
        print(f"区间 {lo}~{hi}  删带: {' '.join(str(y) for y in sorted(b) if lo <= y <= hi)}")
    print(f"\n删带后不见的层界({len([y for y in a if y not in b])}):")
    for y in sorted(y for y in a if y not in b):
        v, cov, x = a[y]
        near = min((abs(y - z) for z in b), default=9999)
        print(f"  y={y} 离墨{v:5.1f}% cov_num={cov:.2f} 跨度{x[0]:.0f}~{x[1]:.0f} "
              f"→ 删带后最近线 {near}px")
    print(f"删带后新出现的层界({len([y for y in b if y not in a])}):")
    for y in sorted(y for y in b if y not in a):
        v, cov, x = b[y]
        near = min((abs(y - z) for z in a), default=9999)
        print(f"  y={y} 离墨{v:5.1f}% cov_num={cov:.2f} 跨度{x[0]:.0f}~{x[1]:.0f} "
              f"→ 现状最近线 {near}px")


yield_rows = {}
if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "1035")
