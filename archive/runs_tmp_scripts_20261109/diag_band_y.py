# -*- coding: utf-8 -*-
"""删带之后 1035 的 y≈12500~13300 整块层界不见了——点名看链条断在哪一环。

两档各跑一遍建链（约 2 分钟/档），对给定 y 打印：
  · 该高度 ±半行高内的链（跨度、链级斜率/台阶）→ 证据还在不在
  · 这条线在 rows / sub_rows / off_grid 哪一档，cov_num 多少 → 判据卡在哪
用法: python runs/tmp/diag_band_y.py 1035 12904 12762
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


def arms(stem):
    real = tr.content_band
    tr.content_band = lambda s: (None, None, None)
    now = tr.load_chains(stem)
    tr.content_band = real
    return {"现状": now, "删带": tr.load_chains(stem)}


def main(code, ys):
    stem = f"钻孔柱状图{code}"
    ch = arms(stem)
    out = {k: tr.assemble(v) for k, v in ch.items()}
    real = tr.content_band
    tr.content_band = lambda s: (None, None, None)
    anchor = {"现状": tr.column_anchor(stem)}
    tr.content_band = real
    anchor["删带"] = real(stem)[0]
    for name, o in out.items():
        items = ch[name]["items"]
        west = float(np.median(anchor[name][:, 1]))
        print(f"\n=== {name} === 层界{len(o['rows'])} 子行线{len(o['sub_rows'])} "
              f"剔{len(o['off_grid'])} 行高{o['row_h']:.0f} "
              f"窗口{o['table_x'][0]}→锚线中位x{west:.0f}")
        for y in ys:
            near = [it for it in items if abs(it["y"] - y) <= 0.5 * o["row_h"]]
            innum = [it for it in near if it["x"][0] < 0.9 * west]
            print(f" y={y}: 链 {len(near)} 条（{len(innum)} 条伸进数值区）→ "
                  + " ".join(f"[{a:.0f},{b:.0f}]" for a, b in sorted(it["x"] for it in near)))
            for key in ("rows", "sub_rows", "off_grid"):
                hit = [r for r in o[key] if abs(r["y_at_mid"] - y) <= 0.6 * o["row_h"]]
                for r in hit:
                    print(f"      {key:8s} y={r['y_at_mid']:.0f} cov_num={r['cov_num']:.2f} "
                          f"cov_desc={r.get('cov_desc', 0):.2f} 跨度{r['x'][0]:.0f}~{r['x'][1]:.0f} "
                          f"链{r['n_chains']} win={r['win']:.2%} 界{r['boundary_x']:.0f}")
            if not hit:
                print(f"      （三档名单里都没有）")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if x.isdigit()]
    main(a[0], [float(v) for v in a[1:]])
