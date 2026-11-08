# -*- coding: utf-8 -*-
import cv2, json
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
img = cv2.imread(str(R/"data"/"raw_images"/"钻孔柱状图1023.JPG"), cv2.IMREAD_GRAYSCALE)
crop = img[560:1000, 150:900]
crop = cv2.resize(crop, None, fx=2.6, fy=2.6, interpolation=cv2.INTER_CUBIC)
cv2.imwrite(str(R/"runs"/"tmp"/"c1023_header_full.png"), crop)
print(crop.shape)
