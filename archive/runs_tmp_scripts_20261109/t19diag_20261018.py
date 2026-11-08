# -*- coding: utf-8 -*-
"""1019 逐格诊断:打印 walk 出来的格、_add_missing_splits 是否触发、x=904 的墨迹外延结果。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
from src.table import header_assign as H
STEM = "钻孔柱状图1019"
hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{STEM}_表头映射.json").read_text(encoding="utf-8"))
band = hm["band"]
g = cv2.imread(str(paths.RAW_DIR/f"{STEM}.JPG"), cv2.IMREAD_GRAYSCALE)
print("band =", band, " 图 =", g.shape)
bounds = H._sep_bounds(STEM)
print("_分割线 边界数 =", len(bounds))
ymid = (band[0]+band[1])/2
for b in bounds: b["x_mid"] = float(np.interp(ymid, b["ys"], b["xs"]))
bounds.sort(key=lambda b: b["x_mid"])
xs = [b["x_mid"] for b in bounds]
print("原始 sep =", [round(x,1) for x in xs])
warns = []
nb, nx = H._merge_twins(bounds, xs, g, warns)
print("去双描后 sep =", [round(x,1) for x in nx], " warns=", warns)
print("满高竖笔 =", H._header_strokes(g, band))
