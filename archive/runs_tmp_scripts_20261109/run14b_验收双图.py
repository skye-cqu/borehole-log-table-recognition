# -*- coding: utf-8 -*-
"""run14b:验收裁片 v2——每格双图。
<tag>_band.png:本行精确行带(y0-8..y1+8),本行内容无歧义
<tag>_ctx.png :上下文窗(±0.9 行高),定位/邻行对照
"""
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
BASE = ROOT / "runs/autoresearch_align/多源定级_20261106"
OUT = BASE / "人工裁定_20261109/img"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs/tmp"))

import cv2  # noqa: E402

from src.core import paths  # noqa: E402
from run5_pkg_v2 import row_ivs_stem  # noqa: E402

TAGS = [
    "1017_行83", "1020_行173", "1032_行104",
    "1020_行118", "1020_行119", "1029_行43",
    "1019_行19", "1019_行47", "1019_行51", "1019_行52", "1019_行54",
    "1019_行56", "1019_行59", "1019_行61", "1019_行63", "1019_行64",
    "1019_行65", "1019_行66", "1019_行67", "1019_行68", "1019_行69",
    "1019_行73", "1019_行85",
    "1029_行24", "1029_行40", "1029_行45", "1029_行52", "1029_行58",
]
SHORT = [t for t in TAGS if t.startswith("1019_")]
SIGN = {"1017_行83", "1020_行173", "1032_行104"}

cache = {}
for tag in TAGS:
    stem0, row = tag.split("_行")
    stem = "钻孔柱状图" + stem0
    r = int(row)
    if stem not in cache:
        cache[stem] = (row_ivs_stem(stem),
                       cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE),
                       json.load(open(paths.RUNS_DIR / "table_reconstruct" /
                                      f"{stem}_表头映射.json", encoding="utf-8")))
    (top_bot, ivs), gray, hm = cache[stem]
    keep = [sorted(c["x_in_band"]) for c in hm["keep"]
            if c["name"] in ("岩性描述", "desc")][0]
    xa, xb = int(keep[0]), int(keep[-1])
    k = r - 2
    y0, y1 = ivs.get(k, (0, 0))
    h = max(1, int(y1 - y0))
    if tag in SHORT:
        x0, x1 = max(0, xa - 450), min(xa + 800, gray.shape[1])
    elif tag in SIGN:
        x0, x1 = max(0, xa - 150), min(xb, gray.shape[1])
    else:
        x0, x1 = max(0, xa - 150), min(xb + 150, gray.shape[1])
    for name, ya, yb in (
            ("band", max(0, int(y0) - 8), min(gray.shape[0], int(y1) + 8)),
            ("ctx", max(0, int(y0) - int(h * 0.9)),
             min(gray.shape[0], int(y1) + int(h * 0.9)))):
        win = gray[ya:yb, x0:x1]
        hh, ww = win.shape
        if hh < 24:
            pad = 24 - hh
            win = cv2.copyMakeBorder(win, pad // 2, pad - pad // 2, 0, 0,
                                     cv2.BORDER_CONSTANT, value=255)
            hh = win.shape[0]
        scale = min(1.0, 1000.0 / ww)
        if scale < 1.0:
            win = cv2.resize(win, None, fx=scale, fy=scale)
        cv2.imwrite(str(OUT / f"{tag}_{name}.png"), win)
print("完成 ->", OUT)
