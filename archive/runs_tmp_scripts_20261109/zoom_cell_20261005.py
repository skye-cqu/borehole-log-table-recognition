# -*- coding: utf-8 -*-
"""单格取墨:按 (图号, xlsx行号, 列名) 渲染该格 3× 裁片,用于错数回原图复核。
列 x 界与 build_cells 同源(表头映射 keep + sep_pts 插值)。

用法: python runs/tmp/zoom_cell_20261005.py 图号 行号 列名 [图号 行号 列名 ...]
输出: runs/tmp/错数缩放_20261005/{图号}_r{行}_{列名}.png
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from src.core import paths

OUT = paths.RUNS_DIR / "tmp" / "错数缩放_20261005"
OUT.mkdir(parents=True, exist_ok=True)

args = sys.argv[1:]
cache = {}
for i in range(0, len(args), 3):
    num, r, colname = args[i], int(args[i + 1]), args[i + 2]
    stem = f"钻孔柱状图{num}"
    if stem not in cache:
        hm = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json",
                            encoding="utf-8"))
        rd = json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json",
                            encoding="utf-8"))
        cache[stem] = (hm, rd)
    hm, rd = cache[stem]
    v3 = hm.get("sep_pts")
    keep = hm["keep"]
    ki = next(j for j, c in enumerate(keep) if c["name"] == colname)
    tab_l, tab_r = rd["table_x"]
    x_tbl = (tab_l + tab_r) / 2
    rows_r = [q for q in rd["rows"] if row_y(q, x_tbl) >= hm["band"][1]] if False else None
    # 行带:与 build_cells 同序(不排序)
    from src.table.track_rows import row_y
    rows_r = [q for q in rd["rows"] if row_y(q, x_tbl) >= hm["band"][1]]
    top, bot = rows_r[r - 2], rows_r[r - 1]

    def bx(i, y, edge):
        if i is None or i < 0:
            return edge
        b = v3[i]
        v = np.interp(y, b["ys"], b["xs"])
        return v if np.ndim(v) else float(v)

    y_mid = (row_y(top, x_tbl) + row_y(bot, x_tbl)) / 2
    x0 = bx(keep[ki]["left_sep"], y_mid, 0.0)
    x1 = bx(keep[ki]["right_sep"], y_mid, float(1 << 14))
    y0c, y1c = row_y(top, (x0 + x1) / 2), row_y(bot, (x0 + x1) / 2)
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    x1 = min(x1, gray.shape[1])
    y0, y1 = max(0, int(y0c) - 18), min(gray.shape[0], int(y1c) + 18)
    xx0, xx1 = max(0, int(x0) - 12), int(x1) + 12
    viz = cv2.cvtColor(gray[y0:y1, xx0:xx1], cv2.COLOR_GRAY2BGR)
    viz = cv2.resize(viz, (viz.shape[1] * 3, viz.shape[0] * 3), interpolation=cv2.INTER_NEAREST)
    p = OUT / f"{num}_r{r}_{colname}.png"
    cv2.imwrite(str(p), viz)
    print(p, f"y[{y0c:.0f},{y1c:.0f}] x[{x0:.0f},{x1:.0f}]")
