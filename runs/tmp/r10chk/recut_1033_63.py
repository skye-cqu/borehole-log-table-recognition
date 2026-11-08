# -*- coding: utf-8 -*-
"""临时核验:1033_行63 行框仅7px,重裁加高窗供视觉判读。"""
import sys
from pathlib import Path
ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runs/tmp"))
import cv2
from src.core import paths
from src.handwriting.reread import ROLE_KEEP
from run5_pkg_v2 import row_ivs_stem, build

stem = "钻孔柱状图1033"
top_bot, ivs = row_ivs_stem(stem)
gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
hm = __import__("json").load(open(paths.RUNS_DIR / "table_reconstruct" / f"{stem}_表头映射.json", encoding="utf-8"))
keep = None
for k in hm["keep"]:
    if k["name"] == ROLE_KEEP["desc"]:
        keep = sorted(k["x_in_band"])
H, W = gray.shape[:2]
x0 = max(0, int(keep[0]) - 8); x1 = min(W, int(keep[1]) + 8)
for tag, r in [("行63", 63)]:
    y0, y1 = ivs[r - 2]
    print(tag, "y0,y1=", y0, y1, "h=", y1 - y0)
    t = top_bot[r - 2] if r - 2 in top_bot else (None, None)
    ys = max(0, y0 - 45); ye = min(H, y1 + 45)
    cell, stripw = build(gray, x0, x1, t[0], ys, t[1], ye)
    out = ROOT / "runs/tmp/r10chk"
    cv2.imwrite(str(out / f"1033_{tag}_big_cell.png"), cell)
    cv2.imwrite(str(out / f"1033_{tag}_big_strip.png"), stripw)
    print("written", out)
