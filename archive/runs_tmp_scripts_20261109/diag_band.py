# -*- coding: utf-8 -*-
"""柱状带（真厚|柱状 → 柱状|岩性）在 6c 里到底算了多少东西。

三问：
  1 数值区右界（锚线）落在带东缘还是带西缘？→ 带在不在覆盖率窗口里
  2 有多少链/段整条落在带里？它们的 y 贴不贴行界？
  3 把窗口收到带西缘（= 用户"删掉柱状列"的做法），多少层界会因为带内墨迹而掉下去？

用法: python runs/tmp/diag_band.py [code...]        # 无参数=30 张
"""
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                              # noqa: E402

BAND_LO, BAND_HI = 120.0, 300.0     # 柱状带宽的合理区间(px)，30 张实测 152~206


def band_edges(stem):
    """定稿列线 → (带东缘=锚线, 带西缘=真厚|柱状)。带西缘取锚线左邻、间距像柱状带的那条。"""
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    seg = {s["id"]: s for s in cj["lines"]
           if s["direction"] == "vertical" and s["label"] == "high"}
    st = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json",
                        encoding="utf-8"))
    cols = sorted(st["columns"], key=lambda c: c["x_at_mid"])
    xs = [c["x_at_mid"] for c in cols]
    _, k = max((b - a, i) for i, (a, b) in enumerate(zip(xs, xs[1:])))
    east = tr.load_chain({"segment_ids": cols[k]["segment_ids"]}, seg)[0]
    west = None
    if k >= 1:
        w = xs[k] - xs[k - 1]
        if BAND_LO <= w <= BAND_HI:
            west = tr.load_chain({"segment_ids": cols[k - 1]["segment_ids"]}, seg)[0]
    return east, west, (xs[k] - xs[k - 1] if k >= 1 else -1), xs[k]


def main(codes):
    tot = {"层界": 0, "带内链": 0, "链数": 0, "降级": 0, "窗口宽": 0.0, "带宽": 0.0}
    for code in codes:
        stem = f"钻孔柱状图{code}"
        east, west, bw, ex = band_edges(stem)
        ch = tr.load_chains(stem)
        if ch is None:
            continue
        x_lo = ch["tab_l"]
        win_now = ex - x_lo
        n_in = sum(1 for it in ch["items"]
                   if west is not None and it["x"][0] >= tr.x_at(west, it["y"]) - 5
                   and it["x"][1] <= tr.x_at(west, it["y"]) + bw + 5)
        o_now = tr.assemble(ch)
        o_cut = dict(o_now)
        if west is not None:
            ch2 = dict(ch, col=west)
            o_cut = tr.assemble(ch2)
        lost = [r for r in o_now["rows"]
                if r["y_at_mid"] not in {q["y_at_mid"] for q in o_cut["rows"]}]
        tot["层界"] += len(o_now["rows"]); tot["链数"] += len(ch["items"])
        tot["带内链"] += n_in; tot["降级"] += len(lost)
        tot["窗口宽"] += win_now; tot["带宽"] += (bw if west is not None else 0)
        print(f"{code}: 锚线x={ex:.0f} 带宽={bw:.0f} 窗口={win_now:.0f}px "
              f"(带占 {100*bw/max(win_now,1):.0f}%) 链{len(ch['items'])} 整条在带里 {n_in} 条 | "
              f"层界 {len(o_now['rows'])} → 窗口收到带西缘 {len(o_cut['rows'])} "
              f"(掉 {len(lost)}) 剔线 {len(o_now['off_grid'])}→{len(o_cut['off_grid'])}")
    print(f"\n合计: 层界{tot['层界']} 链{tot['链数']} 整条在带里{tot['带内链']} "
          f"窗口里带的占比 {100*tot['带宽']/max(tot['窗口宽'],1):.0f}% "
          f"因收窗口而掉的层界 {tot['降级']}")


if __name__ == "__main__":
    codes = [a for a in sys.argv[1:] if a.isdigit()] or \
        sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
    main(codes)
