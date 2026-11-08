# -*- coding: utf-8 -*-
""""图上有竖墨、但我们没定成列线"的那几处，裁片给人眼看：是真分隔线，还是描述栏里的图案边框。

底图原分辨率灰度，绿=已定稿列线，红=候选竖线位置，青=该候选 ±20px 内的竖线墨。
用法: python runs/tmp/mark_cols.py 1024:2396 1026:2408      # 无参数=用下面默认那两处
"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
import yard_cols as Y                                               # noqa: E402

HALF = 220          # 裁片左右各留多少 px
TILE = 1400         # 一张多高
DEFAULT = ["1024:2396", "1026:2408"]

for arg in (sys.argv[1:] or DEFAULT):
    code, xc = arg.split(":")
    stem = f"钻孔柱状图{code}"
    xc = int(xc)
    gray, v = Y.vmask(stem)
    canvas = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
    _, chains = Y.chains_of(stem)
    for _, pts in chains:                       # 已定稿列线画绿
        for (y0, x0), (y1, x1) in zip(pts[:-1], pts[1:]):
            cv2.line(canvas, (int(x0), int(y0)), (int(x1), int(y1)), (0, 200, 0), 2)
    near = np.zeros_like(v, bool)
    near[:, max(0, xc - 20):xc + 21] = (v > 0)[:, max(0, xc - 20):xc + 21]
    ys, xs = np.nonzero(near)
    canvas[ys, xs] = (255, 255, 0)              # 候选附近的真竖线墨 = 青
    cv2.line(canvas, (xc, 0), (xc, canvas.shape[0]), (0, 0, 255), 2)

    y0 = int(min(p[:, 0].min() for _, p in chains))
    y1 = int(max(p[:, 0].max() for _, p in chains))
    x0, x1 = max(0, xc - HALF), min(canvas.shape[1], xc + HALF)
    for n, ty in enumerate(range(y0, y1, TILE)):
        crop = canvas[ty:min(ty + TILE, y1), x0:x1].copy()
        cv2.putText(crop, f"{code} x={xc} tile{n} y={ty}", (8, 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        out = ROOT / "runs" / "tmp" / f"漏竖线_{code}_{xc}_{n}.png"
        cv2.imwrite(str(out), crop)
        print(out)
