# -*- coding: utf-8 -*-
"""柱状带两条缘：现行(冻结) vs 照最近一条还在的列线平移 vs 阶段4 真竖段。

黄=现行(edge_at 冻结)，青=锚点平移(带缘 = 最近一条覆盖到的列线 + 断口处实测偏移)，
品红=阶段4 竖向 high 段(原图里真存在的竖线，逐段画)。
用法: python runs/tmp/diag_band_follow.py 1035 12000 20100
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
cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
segs = [s for s in cj["lines"] if s["direction"] == "vertical" and s["label"] == "high"]
cols = sorted(json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json",
                             encoding="utf-8"))["columns"], key=lambda c: c["x_at_mid"])
segd = {s["id"]: s for s in cj["lines"] if s["direction"] == "vertical" and s["label"] == "high"}
chains = [tr.load_chain({"segment_ids": c["segment_ids"]}, segd)[0] for c in cols]
west, east, _ = tr.content_band(stem)
aw, ae = np.asarray(west, float), np.asarray(east, float)
XLO, XHI = int(min(aw[:, 1].min(), ae[:, 1].min())) - 400, int(max(ae[:, 1].max(), 1400))


def anchored(chain_edge, y):
    """断口以下：带缘 = 最近一条在该高度还覆盖到的列线 + 断口处实测的横向偏移。"""
    a = np.asarray(chain_edge, float)
    if a[0, 0] <= y <= a[-1, 0]:
        return tr.edge_at(chain_edge, y)
    off_best, anchor_best = None, None
    for ch in chains:
        c = np.asarray(ch, float)
        if not (c[0, 0] <= y <= c[-1, 0]):
            continue
        d = tr.edge_at(chain_edge, a[-1, 0]) - tr.edge_at(ch, a[-1, 0])
        cand = (abs(tr.edge_at(ch, a[-1, 0]) - tr.edge_at(chain_edge, a[-1, 0])), d, ch)
        if off_best is None or cand[0] < off_best[0]:
            off_best = cand
    if off_best is None:
        return tr.edge_at(chain_edge, y)
    return tr.edge_at(off_best[2], y) + off_best[1]


img = cv2.cvtColor(gray[y0:y1], cv2.COLOR_GRAY2BGR)
for s in segs:                                     # 品红：原图里真的画出来的竖线段
    p = np.asarray(s["points"], float)
    if p[:, 1].min() > y1 or p[:, 1].max() < y0 or not XLO <= p[:, 0].mean() <= XHI:
        continue
    for (x1, y_1), (x2, y_2) in zip(p, p[1:]):
        if y0 <= min(y_1, y_2) and max(y_1, y_2) < y1:
            cv2.line(img, (int(x1), int(y_1 - y0)), (int(x2), int(y_2 - y0)), (200, 0, 200), 2)
for tag, edge, col in (("冻结", west, (0, 200, 255)), ("平移", west, (255, 200, 0))):
    f = tr.edge_at if tag == "冻结" else anchored
    pts = [(int(f(edge, y)), y - y0) for y in range(y0, y1, 4)]
    cv2.polylines(img, [np.asarray(pts, np.int32)], False, col, 2)
for tag, edge, col in (("冻结", east, (0, 200, 255)), ("平移", east, (255, 200, 0))):
    f = tr.edge_at if tag == "冻结" else anchored
    pts = [(int(f(edge, y)), y - y0) for y in range(y0, y1, 4)]
    cv2.polylines(img, [np.asarray(pts, np.int32)], False, col, 2)
sc = 1400 / img.shape[1]
img = cv2.resize(img, None, fx=sc, fy=sc)
out = ROOT / "runs" / "tmp" / f"带缘对比_{code}_{y0}-{y1}.png"
cv2.imwrite(str(out), img)
print(out, img.shape)
for y in range(y0 + 500, y1, 1000):
    print(f"y={y}  西 冻结{tr.edge_at(west, y):.0f} 平移{anchored(west, y):.0f}   "
          f"东 冻结{tr.edge_at(east, y):.0f} 平移{anchored(east, y):.0f}")
