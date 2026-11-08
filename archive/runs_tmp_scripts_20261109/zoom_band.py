# -*- coding: utf-8 -*-
"""柱状带放大对照片：原图 | 现行叠加，两条竖绿线之间就是"柱状"列。

用法: python runs/tmp/zoom_band.py 1035 5600 5900        # 输出 runs/tmp/柱状带_1035_5600-5900.png
"""
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs" / "tmp"))
from src.core import paths                                          # noqa: E402
from src.table import track_rows as tr                               # noqa: E402

code, y0, y1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
stem = f"钻孔柱状图{code}"
gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
ov = cv2.imread(str(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.png"))
# 绿线画的是"现行代码认为带在哪儿"：直接取 content_band + edge_at，逐 y 取值连成折线
# （整张表在下半张一路右偏，画成直上直下的竖线就成了"图上没有的线"）
west, east, _ = tr.content_band(stem)
ym = (y0 + y1) / 2
wl, er = int(tr.edge_at(west, ym)), int(tr.edge_at(east, ym))
x0, x1 = max(0, wl - 260), min(gray.shape[1], er + 260)
m = 40
sl = (slice(y0 - m, y1 + m), slice(x0, x1))
a = cv2.cvtColor(gray[sl], cv2.COLOR_GRAY2BGR)
b = ov[sl].copy()
ys = np.arange(y0 - m, y1 + m)
for img in (a, b):
    for edge in (west, east):
        pts = np.column_stack([np.round([tr.edge_at(edge, y) for y in ys]) - x0, ys - (y0 - m)])
        cv2.polylines(img, [pts.astype(np.int32)], False, (0, 200, 0), 2)
gap = np.full((a.shape[0], 14, 3), 40, np.uint8)
img = np.hstack([a, gap, b])
cv2.putText(img, f"{code} y={y0}-{y1}  绿线间=柱状列[{wl},{er}]  左=原图 右=现行叠加",
            (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
out = ROOT / "runs" / "tmp" / f"柱状带_{code}_{y0}-{y1}.png"
cv2.imwrite(str(out), img)
print(out, img.shape)
