# -*- coding: utf-8 -*-
"""带缘前后对照：同一片原图上画"冻在断口处"(橙) 和 "跟着邻线平移"(绿)。

用法: python runs/tmp/band_pair.py 1035 18700 19300      # 输出 runs/tmp/带缘前后_1035_18700-19300.png
"""
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
west, east, src = tr.content_band(stem)                 # 断口以下已跟着邻线平移
import json                                                          # noqa: E402
cols = sorted(json.load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_列结构定稿.json",
                             encoding="utf-8"))["columns"], key=lambda c: c["x_at_mid"])
cj = json.load(open(paths.CANDIDATE_COORD_DIR / f"{stem}.json", encoding="utf-8"))
segd = {s["id"]: s for s in cj["lines"] if s["direction"] == "vertical" and s["label"] == "high"}
ch = [tr.load_chain({"segment_ids": c["segment_ids"]}, segd)[0] for c in cols]
xs = [c["x_at_mid"] for c in cols]
_, k = max((b - a, i) for i, (a, b) in enumerate(zip(xs, xs[1:])))
old = (ch[k - 1], ch[k]) if xs[k] - xs[k - 1] >= tr.BAND_MIN else (ch[k], None)   # 冻结版=定稿原样

ys = np.arange(y0, y1)
x_lo = min([tr.edge_at(e, y) for y in ys for e in (west, old[0])]) - 120
x_hi = max([tr.edge_at(e, y) for y in ys for e in (east, old[1]) if e is not None]) + 120
img = cv2.cvtColor(gray[y0:y1, int(x_lo):int(x_hi)], cv2.COLOR_GRAY2BGR)
for which in (0, 1):
    o, n = old[which], (west, east)[which]
    if o is None:
        continue
    for arr, col in ((o, (0, 165, 255)), (n, (0, 200, 0))):
        pts = np.column_stack([np.round([tr.edge_at(arr, y) for y in ys]) - x_lo, ys - y0])
        cv2.polylines(img, [pts.astype(np.int32)], False, col, 2)
img = cv2.resize(img, None, fx=1.4, fy=1.0, interpolation=cv2.INTER_NEAREST)
cv2.putText(img, f"{code} y={y0}-{y1}  橙=冻在断口(改前)  绿=跟着邻线平移(改后)",
            (8, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
out = ROOT / "runs" / "tmp" / f"带缘前后_{code}_{y0}-{y1}.png"
cv2.imwrite(str(out), img)
print(out, img.shape, "  带出处", src)
for y in (y0, (y0 + y1) // 2, y1 - 1):
    print(f"  y={y}: 西 {tr.edge_at(old[0], y):.0f}→{tr.edge_at(west, y):.0f}"
          + (f"   东 {tr.edge_at(old[1], y):.0f}→{tr.edge_at(east, y):.0f}"
             if old[1] is not None else ""))
