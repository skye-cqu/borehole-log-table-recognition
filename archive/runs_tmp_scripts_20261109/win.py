# -*- coding: utf-8 -*-
"""原图窗 / 画线窗并排（全分辨率，不缩放）：一条线在图上有没有，直接对得上。

门禁的争论不该靠猜阈值，先看片：红线走的地方有没有横线墨、是不是把上一行接到下一行。
第三格 = 把 yardstick 的横线墨迹 mask 涂成绿色叠在原图上，"图上有横线"这件事本身可视化，
红线贴绿 = 线上存在；红线走在没有绿的地方 = 凭空画的。

用法: python runs/tmp/win.py <code> <y0> <y1> [json目录]     # 默认 runs/table_reconstruct
产物: runs/tmp/窗_<code>_<y0>.png
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
from src.table.track_rows import row_y                              # noqa: E402
import yardstick as Y                                               # noqa: E402


def main(code, y0, y1, src):
    stem = f"钻孔柱状图{code}"
    rd = json.loads((Path(src) / f"{stem}_行判定.json").read_text(encoding="utf-8"))
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    ruling, _ = Y.masks(stem)
    x0, x1 = int(rd["table_x"][0]) - 20, int(rd["table_x"][1]) + 20
    y0, y1 = int(y0), int(y1)
    crop = lambda a: a[y0:y1, x0:x1]                                # noqa: E731

    raw = cv2.cvtColor(crop(gray), cv2.COLOR_GRAY2BGR)
    ink = raw.copy()
    ink[crop(ruling) > 0] = (0, 200, 0)                             # 横线墨 = 绿
    ovl = ink.copy()
    for r in rd["rows"]:
        pts = [[x - x0, row_y(r, x) - y0] for x in
               np.linspace(r["x"][0], r["x"][1], min(400, r["x"][1] - r["x"][0]))]
        cv2.polylines(ovl, [np.asarray(pts, np.int32).reshape(-1, 1, 2)],
                      False, (0, 0, 255), 2, cv2.LINE_AA)
    # 2px 红线在整幅宽(2800+)的图上会被看图软件缩成看不见——按 x 切成 ≤1300px 的条，竖着摞
    W = raw.shape[1]
    nt = int(np.ceil(W / 1300.))
    tw = int(np.ceil(W / nt))                       # 等宽切格：末格补齐，否则竖摞不起来
    tiles = []
    for i in range(nt):
        a, b = i * tw, min((i + 1) * tw, W)
        pair = np.hstack([raw[:, a:b], np.full((raw.shape[0], 8, 3), 128, np.uint8),
                          ovl[:, a:b]])
        if pair.shape[1] < tw * 2 + 8:
            pair = np.pad(pair, ((0, 0), (0, tw * 2 + 8 - pair.shape[1]), (0, 0)),
                          constant_values=(50, 50))
        cv2.putText(pair, f"原图 x={x0 + a}-{x0 + b}", (10, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, .7, (255, 0, 255), 2)
        cv2.putText(pair, "绿=图上横线墨  红=层界", (tw + 30, 24),
                    cv2.FONT_HERSHEY_SIMPLEX, .7, (255, 0, 255), 2)
        tiles.append(pair)
    out = ROOT / "runs" / "tmp" / f"窗_{code}_{y0}.png"
    cv2.imwrite(str(out), np.vstack(tiles), [cv2.IMWRITE_PNG_COMPRESSION, 3])
    print(f"{out}  层界 {len(rd['rows'])} 条，窗口 y={y0}..{y1} {tiles[0].shape[1]}x"
          f"{sum(t.shape[0] for t in tiles)}，{len(tiles)} 条")


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]),
         sys.argv[4] if len(sys.argv) > 4 else str(paths.RUNS_DIR / "table_reconstruct"))
