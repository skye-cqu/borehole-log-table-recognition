# -*- coding: utf-8 -*-
"""新旧层界对照：一张图上左边按旧 行判定.json 画线，右边按新 行判定.json 画线。

用法: python runs/tmp/compare_rows.py 1019 6862 8629
旧 JSON 取自 rollback/行判定_旧判据_20260923/（重生成前的快照）。
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402

OLD = ROOT / "rollback" / "行判定_旧判据_20260923"

code, y0, y1 = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
stem = f"钻孔柱状图{code}"
base = cv2.imread(str(paths.TRACK_GROUP_OVERLAY_DIR / f"{stem}.png"))
x0, x1 = 200, 1750
m = 45


def panel(p):
    d = json.loads(Path(p).read_text(encoding="utf-8"))
    im = base.copy()
    for r in d["rows"]:
        cv2.line(im, (int(r["x"][0]), int(r["y_at_mid"])),
                 (int(r["x"][1]), int(r["y_at_mid"])), (0, 0, 255), 5, cv2.LINE_AA)
    for r in d.get("sub_rows", []):
        cv2.line(im, (int(r["x"][0]), int(r["y_at_mid"])),
                 (int(r["x"][1]), int(r["y_at_mid"])), (0, 140, 255), 3, cv2.LINE_AA)
    return im[y0 - m:y1 + m, x0:x1], d


a, da = panel(OLD / f"{stem}_行判定.json")
b, db = panel(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_行判定.json")
gap = np.full((a.shape[0], 12, 3), 40, np.uint8)
img = np.hstack([a, gap, b])
k = 900 / img.shape[1]
img = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
for txt, x in ((f"旧判据 层界{len(da['rows'])}/子行{len(da.get('sub_rows',[]))}", x0),
               (f"新判据 层界{len(db['rows'])}/子行{len(db.get('sub_rows',[]))}",
                x0 + 12 + a.shape[1])):
    cv2.putText(img, txt, (int(x * k), 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                (0, 0, 255), 2)
out = paths.RUNS_DIR / "tmp" / f"新旧_{code}_{y0}-{y1}.png"
cv2.imwrite(str(out), img, [cv2.IMWRITE_PNG_COMPRESSION, 6])
print(out)
