# -*- coding: utf-8 -*-
"""柱状带两条缘的数据源核对：现行位置 vs 原图真竖线 vs 阶段4 候选竖段。

用法: python runs/tmp/diag_band_source.py 1034 12000 17000
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                              # noqa: E402

code, y0, y1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
stem = f"钻孔柱状图{code}"
gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
bw = (gray < 160).astype(np.uint8)
# 每个 x 在这一行往上能连上多少像素的黑 = 这条竖线在这一高度有多"实"
run = np.zeros_like(bw)
for y in range(bw.shape[0]):
    run[y] = (run[y - 1] + 1) * bw[y] if y else bw[y] * 0

cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
segs = [s for s in cj["lines"] if s["direction"] == "vertical" and s["label"] == "high"]
west, east, src = tr.content_band(stem)
aw, ae = np.asarray(west, float), np.asarray(east, float)
print(f"{code} 带出处={src}  西缘覆盖 y {aw[0,0]:.0f}~{aw[-1,0]:.0f}  "
      f"东缘覆盖 y {ae[0,0]:.0f}~{ae[-1,0]:.0f}  表高 {gray.shape[0]}")

XLO, XHI = 600, 1400
for y in range(y0, y1 + 1, 400):
    wl, el = tr.edge_at(west, y), tr.edge_at(east, y)
    cw = aw[0, 0] <= y <= aw[-1, 0]
    ce = ae[0, 0] <= y <= ae[-1, 0]
    ink = [int(x) for x in range(XLO, XHI) if run[y, x] >= 250]
    grp = []
    for x in ink:
        if grp and x - grp[-1][-1] <= 3:
            grp[-1].append(x)
        else:
            grp.append([x])
    near = [(int(np.mean(g)), max(run[y, x] for x in g)) for g in grp]
    cands = []
    for s in segs:
        p = np.asarray(s["points"], float)
        if p[:, 1].min() <= y <= p[:, 1].max() and XLO <= p[:, 0].mean() <= XHI:
            cands.append((round(float(p[:, 0].mean()), 1),
                          int(p[:, 1].min()), int(p[:, 1].max()), s["id"]))
    cands.sort()
    print(f"\ny={y}  现行带=[{wl:.0f},{el:.0f}] 西{'覆盖' if cw else '断'} 东{'覆盖' if ce else '断'}")
    print(f"  原图≥250px 实竖线 x: {near}")
    print(f"  阶段4竖段(过该y, x均值/y范围/id): {cands}")
