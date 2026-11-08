# -*- coding: utf-8 -*-
"""run14:人工终裁验收包——28 格裁片生成。

窗设计(便于视觉判断):
- 短判层语/越界格(1019 系):x 从 desc 列左界外 450px 起,含上下各 0.6 行高
- 一般格:desc 列全宽+左右各 150px,上下各 0.6 行高
- 行带歧义(1020_118/119):两行连窗;1029_43:行42-44 连窗
- 图签行:desc 列右下角大区域(含图签块)
输出:人工裁定_20261109/img/<tag>_view.png,统一宽 1000px。
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
import numpy as np  # noqa: E402

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
PAIRS = {"1020_行118": ["1020_行118", "1020_行119"],
         "1029_行43": ["1029_行42", "1029_行43", "1029_行44"]}

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
    rows_want = PAIRS.get(tag, [tag])
    tiles = []
    for t in rows_want:
        rr = int(t.split("_行")[1])
        k = rr - 2
        y0, y1 = ivs.get(k, (0, 0))
        ya = max(0, int(min(y0, y1)) - int((y1 - y0) * 0.6))
        yb = min(gray.shape[0], int(max(y0, y1)) + int((y1 - y0) * 0.6))
        if tag in SHORT:
            x0, x1 = max(0, xa - 450), min(xa + 750, gray.shape[1])
        elif tag.endswith("_104") or tag == "1020_行173" or tag == "1017_行83":
            x0, x1 = max(0, xa - 100), min(xb, gray.shape[1])
        else:
            x0, x1 = max(0, xa - 150), min(xb + 150, gray.shape[1])
        tiles.append((ya, yb, gray[ya:yb, x0:x1]))
    ya_all = min(t[0] for t in tiles)
    yb_all = max(t[1] for t in tiles)
    # 连窗:取 y 并集后按首格 x 窗重切
    t0 = tiles[0][2]
    win = gray[ya_all:yb_all, t0.shape[1] and 0 or 0:0]  # placeholder
    x0 = max(0, xa - (450 if tag in SHORT else (100 if "图签" else 150)))
    if tag in SHORT:
        x0 = max(0, xa - 450); x1 = min(xa + 750, gray.shape[1])
    elif tag.endswith("_104") or tag == "1020_行173" or tag == "1017_行83":
        x0 = max(0, xa - 100); x1 = min(xb, gray.shape[1])
    else:
        x0 = max(0, xa - 150); x1 = min(xb + 150, gray.shape[1])
    win = gray[ya_all:yb_all, x0:x1]
    h, w = win.shape
    scale = min(1.0, 1000.0 / w)
    if scale < 1.0:
        win = cv2.resize(win, None, fx=scale, fy=scale)
    cv2.imwrite(str(OUT / f"{tag}_view.png"), win)
    print(tag, f"{w}x{h} -> {win.shape[1]}x{win.shape[0]}")
print("完成 ->", OUT)
