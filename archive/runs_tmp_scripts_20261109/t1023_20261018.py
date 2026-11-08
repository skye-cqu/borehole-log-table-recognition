# -*- coding: utf-8 -*-
"""1023 的两格(325.6-450.6 / 450.6-537.6)到底写的是什么?
与 1015 同样两格对照。直接 OCR 原图表头带,不依赖 LAYOUT_OVERRIDES。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
from rapidocr_onnxruntime import RapidOCR
ocr = RapidOCR()
RECON = paths.RUNS_DIR / "table_reconstruct"
for stem in ("钻孔柱状图1023", "钻孔柱状图1015"):
    w = json.loads((RECON/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
    b0, b1 = w["band"]
    g = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    print("\n=== %s band=[%d,%d] ===" % (stem[-4:], b0, b1))
    for c in w["columns"]:
        x0, x1 = c["x_in_band"]
        x0i, x1i = int(x0)+4, int(x1)-4
        if x1i - x0i < 8: continue
        crop = g[b0:b1, x0i:x1i]
        res, _ = ocr(crop)
        t = "".join(x[1] for x in (res or [])).strip()
        print("  %-8s x=[%6.1f,%6.1f] w=%6.1f  OCR=%r" % (c["name"], x0, x1, c["width"], t))
