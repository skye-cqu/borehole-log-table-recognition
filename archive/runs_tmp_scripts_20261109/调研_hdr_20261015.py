# -*- coding: utf-8 -*-
"""验证:1032 原图表头是否真无"时代/层号"两列;1042 原图是否有"真厚"列。
逐格裁表头,数每格里的字。"""
import cv2, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R/"data"/"raw_images"; TR = R/"runs"/"table_reconstruct"
for stem in ["钻孔柱状图1032","钻孔柱状图1042","钻孔柱状图1019","钻孔柱状图1023"]:
    hm = json.load(open(TR/f"{stem}_表头映射.json", encoding="utf-8"))
    b0,b1 = hm["band"]
    print(f"##### {stem} band={hm['band']} n_sep={hm['n_sep']} ok={hm['ok']}")
    print("  sep_x_band:", [round(v,1) for v in hm["sep_x_band"]])
    print("  label_verify:", hm.get("label_verify"))
    print("  warnings:", hm.get("warnings"))
    print("  keep:", [(c["name"], round(c["x_in_band"][0]), round(c["x_in_band"][1])) for c in hm["keep"]])
    print("  drop:", [(c["name"], round(c["x_in_band"][0]), round(c["x_in_band"][1])) for c in hm["drop_columns"]])
    print()
