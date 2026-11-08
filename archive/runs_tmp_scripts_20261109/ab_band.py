# -*- coding: utf-8 -*-
"""形状闸的参照带 A/B：全表参照(SKEW_BAND=0) vs 局部参照(上下 1 行高)。

为什么要这一跑：形状闸量的是"这条线歪不歪"，而歪是相对一个参照量出来的。参照取全表中位
斜率，在整张纸慢慢转的图上会把真行当成歪线——1020 的全表中位斜率自己就是 2.10%，闸也是 2%，
于是它一半以上的线被剔，其中 64 条离墨 ≤10%（就贴在真横线上）。换成"邻近链的窗斜率中位"做
参照，量的是这条线相对它的上下文偏离多少，纸整体转多少都不算它歪。

标尺沿用 ab_split 那三把：原图横线墨(离墨>10%/>30%)、漏线带、行距规整（不靠墨）。
被剔的线也拿同一把尺量（rej10 列）：剔的若是贴墨的真行 = 阈值过紧，这是本轮要看的重点。

用法: python runs/tmp/ab_band.py            # 30 张，两档并排 + 合计
      python runs/tmp/ab_band.py sweep 1020 1035   # 参照带宽度的分档细跑
"""
from __future__ import annotations

import os
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
from ab_split import spacing                                        # noqa: E402

BANDS = [("全表" if b == 0 else f"{b}行高", b) for b in
         [float(x) for x in os.environ.get("BANDS", "0,1.0").split(",")]]
COLS = "层界   剔 剔墨  漏 >10  挤 规整%"


def measure(ch, ruling, band):
    tr.SKEW_BAND = band
    o = tr.assemble(ch)
    oi = offink(ruling, o["rows"])
    rej = offink(ruling, o["off_grid"])
    reg, tight, _ = spacing(o)
    return dict(n=len(o["rows"]), miss=len(M.missed(o, ruling)),
                o10=sum(1 for v in oi if v > 10), o30=sum(1 for v in oi if v > 30),
                med=float(np.median(oi)) if oi else 0.0, off=len(o["off_grid"]),
                rej10=sum(1 for v in rej if v <= 10),
                reg=reg, tight=tight, row_h=o["row_h"], s0=o["slope_med"])


def sweep(codes, bands=(0.5, 1.0, 1.5, 2.0, 3.0)):
    """参照带取几行高的分档：同一批链、同一把尺子，逐档报层界/剔线/剔中贴墨/漏线。"""
    for code in codes:
        stem = f"钻孔柱状图{code}"
        ch = tr.load_chains(stem)
        ruling = Y.masks(stem)[0]
        print(f"\n=== {code} ===")
        for b in bands:
            m = measure(ch, ruling, b)
            print(f"  带{b:>3.1f}行高({b * m['row_h']:5.0f}px) 层界{m['n']:>4} 剔{m['off']:>4} "
                  f"剔中贴墨{m['rej10']:>4} 漏{m['miss']:>3} 离墨>10 {m['o10']:>4} "
                  f"离墨>30 {m['o30']:>3} 挤{m['tight']:>3} 规整{m['reg']:>3.0f}%")


def main():
    codes = [a for a in sys.argv[1:] if a.isdigit()] or \
        sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
    if "sweep" in sys.argv[1:]:
        sweep(codes)
        return
    print(f"{'图':<6}" + "".join(f"{f'{t}({COLS})':>36}" for t, _ in BANDS))
    acc = {t: [] for t, _ in BANDS}
    for code in codes:
        stem = f"钻孔柱状图{code}"
        ch = tr.load_chains(stem)
        ruling = Y.masks(stem)[0]
        vs = [measure(ch, ruling, b) for _, b in BANDS]
        for (t, _), v in zip(BANDS, vs):
            acc[t].append(v)
        print(f"{code:<6}" + "".join(
            f"{m['n']:>6}{m['off']:>5}{m['rej10']:>5}{m['miss']:>4}{m['o10']:>5}"
            f"{m['tight']:>4}{m['reg']:>6.0f}%" for m in vs))
    for t, ms in acc.items():
        print(f"合计 {t:<8} 层界{sum(m['n'] for m in ms):>5} 剔{sum(m['off'] for m in ms):>5} "
              f"剔中贴墨{sum(m['rej10'] for m in ms):>4} 漏{sum(m['miss'] for m in ms):>4} "
              f">10%{sum(m['o10'] for m in ms):>5} 挤{sum(m['tight'] for m in ms):>4} "
              f"行距规整{np.mean([m['reg'] for m in ms]):>4.0f}% 中位离墨"
              f"{np.mean([m['med'] for m in ms]):>5.1f}")


if __name__ == "__main__":
    main()
