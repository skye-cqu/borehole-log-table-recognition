# -*- coding: utf-8 -*-
"""原图裁片:看真实表格结构(第一性原理)。"""
import cv2, json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R / "data" / "raw_images"
TR = R / "runs" / "table_reconstruct"
OUT = R / "runs" / "tmp"
OUT.mkdir(parents=True, exist_ok=True)

for stem in ["钻孔柱状图1032", "钻孔柱状图1042", "钻孔柱状图1019"]:
    hm = json.load(open(TR / f"{stem}_表头映射.json", encoding="utf-8"))
    img = cv2.imread(str(RAW / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    H, W = img.shape
    b0, b1 = hm["band"]
    print(stem, "shape", img.shape, "band", hm["band"], "n_sep", hm["n_sep"])
    # 表头区:band 上下各扩 120
    y0 = max(0, b0 - 150); y1 = min(H, b1 + 200)
    crop = img[y0:y1, :]
    # 缩到宽 1600 以内
    sc = min(1.0, 1600.0 / crop.shape[1])
    if sc < 1.0:
        crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(OUT / f"原图_{stem}_表头区.png"), crop)
    print("   ->", f"原图_{stem}_表头区.png", crop.shape)
