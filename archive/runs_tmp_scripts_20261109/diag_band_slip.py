# -*- coding: utf-8 -*-
"""量的是一件事：柱状带画在哪儿，会因为列线中断而滑走多少。

对照两版取 x 的规矩（同一批 6a 定稿列线、同一批阶段4 横段，只有取边的写法不同）：
  第一版 = 裸外推（x_at 原样：y 出覆盖按末端斜率直延伸）
  修好   = 常量延接（edge_at：y 出覆盖按断点原地平行往下延）

用法：python runs/tmp/diag_band_slip.py [编号...]   不给编号=30 张全量
输出：每张的带内段计数差、差异段落在哪儿（y 区间 + 中点 x 中位）、
      最深一条层界处的带位置两版对照。报告"带的两条缘会中断"一节由此而来。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.core import paths  # noqa: E402
from src.table import track_rows as tr  # noqa: E402
from src.table.track_columns import load_chain, x_at  # noqa: E402


def band_first(pts, band):
    """门禁5 第一版的带内判定：与 tr.in_band 同式，只是取边不夹覆盖范围。"""
    west, east = band
    p = np.asarray(pts, float)
    ym = float(np.median(p[:, 1]))
    x = (p[:, 0].min() + p[:, 0].max()) / 2
    return x_at(np.asarray(west, float), ym) + tr.BAND_PAD <= x <= x_at(np.asarray(east, float), ym) - tr.BAND_PAD


def x_raw(chain, y):
    return float(x_at(np.asarray(chain, float), y))


def x_fixed(chain, y):
    return tr.edge_at(chain, y)


def report(stem):
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
    segs = [s for s in cj["lines"] if s["direction"] == "horizontal" and s["label"] == "high"]
    west, east, src = tr.content_band(stem)
    if west is None:
        print(f"{stem}: 认不出带，两版一样（0 条改动）")
        return 0, 0
    band = (west, east)
    a = np.asarray(west, float)          # 缘点列按 (y,x) 存，[0,0]/[-1,0] 即覆盖到的 y 上下界
    b = np.asarray(east, float)
    fj = Path(paths.RUNS_DIR, "table_reconstruct", f"{stem}_行判定.json")
    deepest = 0.0
    if fj.exists():
        rows = json.load(open(fj, encoding="utf-8"))["rows"]
        if rows:
            deepest = max(float(p[1]) for r in rows for p in r["poly"])
    y = deepest or float(np.median([np.median(np.asarray(s["points"], float)[:, 1]) for s in segs]))

    first = [s for s in segs if band_first(s["points"], band)]
    fixed = [s for s in segs if tr.in_band(s["points"], band)]
    ids_f = {s["id"] for s in first}
    ids_x = {s["id"] for s in fixed}
    lost = [s for s in first if s["id"] not in ids_x]        # 第一版排掉、修好后留下
    new = [s for s in fixed if s["id"] not in ids_f]         # 第一版没排掉、修好后排掉

    def span(group):
        if not group:
            return "-"
        ys = [float(np.median(np.asarray(s["points"], float)[:, 1])) for s in group]
        xs = [(float(np.asarray(s["points"], float)[:, 0].min()) + float(np.asarray(s["points"], float)[:, 0].max())) / 2
              for s in group]
        return f"y {min(ys):.0f}~{max(ys):.0f} 中点x中位 {int(np.median(xs))}"

    print(f"{stem}（带缘来自 {src}）")
    print(f"  横段 {len(segs)} 条｜带内：第一版 {len(first)} → 修好 {len(fixed)}")
    print(f"  第一版多排掉（修好后找回）{len(lost)} 条：{span(lost)}")
    print(f"  修好后新排掉 {len(new)} 条：{span(new)}")
    print(f"  最深层界 y={y:.0f}｜西缘覆盖到 {a[0, 0]:.0f}~{a[-1, 0]:.0f}、东缘 {b[0, 0]:.0f}~{b[-1, 0]:.0f}")
    print(f"    带位置 第一版 [{x_raw(west, y):.0f}, {x_raw(east, y):.0f}] → 修好 [{x_fixed(west, y):.0f}, {x_fixed(east, y):.0f}]")
    return len(first), len(fixed)


def main():
    stems = [f"钻孔柱状图{a}" if a.isdigit() else a for a in sys.argv[1:]] or \
            sorted(p.stem for p in paths.CANDIDATE_COORD_DIR.glob("*.json"))
    tot = [0, 0]
    for s in stems:
        r = report(s)
        tot[0] += r[0]
        tot[1] += r[1]
    print(f"\n合计 带内段判定：第一版 {tot[0]} → 修好 {tot[1]}")


if __name__ == "__main__":
    main()
