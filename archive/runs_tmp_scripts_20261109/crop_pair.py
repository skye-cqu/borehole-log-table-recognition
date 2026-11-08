# -*- coding: utf-8 -*-
"""两档门禁的同一块区域并排片：吃两份 行判定.json 的 poly，画在原图裁片上。

跟 make_evidence_crop.py 的分工：那张是"原图 vs 生产叠加"（看线对不对），这张是
"档A vs 档B"（看门禁改动落在哪条线上）。折线按 JSON 原样画，不重新拟合。
红=层界，紫=被形状闸剔掉的线（画出来才看得清剔的是不是真歪）。

用法: python runs/tmp/crop_pair.py 1020 6800 7300 runs/tmp/ab/全表参照 runs/table_reconstruct
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402

code, y0, y1, dir_a, dir_b = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4], sys.argv[5]
stem = f"钻孔柱状图{code}"
gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
x0, x1, m = 200, 1750, 45
sl = (slice(y0 - m, y1 + m), slice(x0, x1))


def panel(d):
    o = json.loads(Path(d).joinpath(f"{stem}_行判定.json").read_text(encoding="utf-8"))
    img = cv2.cvtColor(gray[sl], cv2.COLOR_GRAY2BGR).copy()
    for rows, col, w in ((o["rows"], (0, 0, 255), 3), (o.get("off_grid", []), (255, 0, 255), 2)):
        for r in rows:
            pts = np.asarray(r["poly"], np.int32)
            pts[:, 1] -= y0 - m
            pts[:, 0] -= x0
            cv2.polylines(img, [pts], False, col, w, cv2.LINE_AA)
    tag = Path(d).name if Path(d).name != "table_reconstruct" else "生产"
    return img, f"{tag}: 层界{len(o['rows'])} 剔{len(o.get('off_grid', []))}"


a, la = panel(dir_a)
b, lb = panel(dir_b)
gap = np.full((a.shape[0], 12, 3), 40, np.uint8)
img = np.hstack([a, gap, b])
k = 1600 / img.shape[1]
img = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
for txt, x in ((la, x0), (lb, x0 + 12 + a.shape[1])):
    cv2.putText(img, txt, (int(x * k), 30), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 2)
out = ROOT / "runs" / "tmp" / f"对比_{code}_{y0}-{y1}.png"
cv2.imwrite(str(out), img, [cv2.IMWRITE_PNG_COMPRESSION, 6])
print(out, img.shape)
