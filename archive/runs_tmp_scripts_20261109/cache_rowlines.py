# -*- coding: utf-8 -*-
"""阶段A(慢,可缓存):对每张图跑现行建链,把"候选横线"按 y 聚合并导出并集覆盖区间。

产物 runs/tmp/行链_<code>.json:
  {tab_l, tab_r, num_x, lines:[[y, [[a,b],..]数值区区间, [[a,b],..]描述区区间], ..], chains:N}
一次跑完,阈值扫描(阶段B)即可秒级反复查——判据推导不该每次重建链。
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                    # noqa: E402
from src.table import track_group, track_rows                  # noqa: E402
from src.table.track_columns import merge_tracks               # noqa: E402
sys.path.insert(0, str(paths.PROJECT_ROOT / "runs/tmp"))
from probe_rows2 import chains                                  # noqa: E402

TOL = 25


def collect(stem):
    groups, tab_l, tab_r, num_x = chains(stem)
    items = []
    for g in groups:
        items.append((track_rows.x_at_mid(g), min(max(g["y0"], tab_l), num_x),
                      min(max(g["y1"], tab_l), num_x),
                      min(max(g["y0"], num_x), tab_r), min(max(g["y1"], num_x), tab_r)))
    items.sort()
    lines = []
    for y, nl, nr, dl, dr in items:
        if lines and y - lines[-1][-1] <= TOL:
            lines[-1][1] += [(nl, nr)]
            lines[-1][2] += [(dl, dr)]
            lines[-1][3] = y                      # 簇内最后一条的 y 作为参照
        else:
            lines.append([y, [(nl, nr)], [(dl, dr)], y])
    return {"tab_l": tab_l, "tab_r": tab_r, "num_x": num_x, "n_chains": len(groups),
            "lines": [[round(r[0], 1), r[1], r[2]] for r in lines]}


def main():
    codes = [a for a in sys.argv[1:] if a.isdigit()] or [str(n) for n in range(1015, 1045)]
    for code in codes:
        out = paths.RUNS_DIR / "tmp" / f"行链_{code}.json"
        if out.exists():
            print(f"{code}: 已有缓存")
            continue
        stem = f"钻孔柱状图{code}"
        d = collect(stem)
        out.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
        print(f"{code}: 链 {d['n_chains']} → 线 {len(d['lines'])}", flush=True)


if __name__ == "__main__":
    main()
