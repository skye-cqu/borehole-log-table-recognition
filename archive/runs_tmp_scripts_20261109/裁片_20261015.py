# -*- coding: utf-8 -*-
"""任意裁片工具:python 裁片.py <stem> <x0> <x1> <y0> <y1> <scale> <out>"""
import sys
import cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
stem, x0, x1, y0, y1, sc, out = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), float(sys.argv[6]), sys.argv[7]
img = cv2.imread(str(R / "data" / "raw_images" / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
crop = img[y0:y1, x0:x1]
if sc != 1.0:
    crop = cv2.resize(crop, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
cv2.imwrite(str(R / "runs" / "tmp" / out), crop)
print(out, crop.shape)
