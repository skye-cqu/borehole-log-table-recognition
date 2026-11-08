# -*- coding: utf-8 -*-
"""1042 表头左区高倍细读:确定 137/199/260 哪个是列界。"""
import sys
import numpy as np, cv2
from pathlib import Path
from PIL import Image, ImageDraw
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
xa, xb, ya, yb, sc = 55, 500, 730, 1010, 5
sub = g[ya:yb, xa:xb]
c = cv2.resize(cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR), ((xb-xa)*sc, (yb-ya)*sc), interpolation=cv2.INTER_NEAREST)
img = Image.fromarray(cv2.cvtColor(c, cv2.COLOR_BGR2RGB))
d = ImageDraw.Draw(img)
for x in range(xa, xb, 10):
    px = (x-xa)*sc
    maj = (x % 50 == 0)
    d.line([(px, 0), (px, 34 if maj else 16)], fill=(230,0,0) if maj else (0,160,255), width=1)
    d.line([(px, c.shape[0]-34 if maj else c.shape[0]-16), (px, c.shape[0])], fill=(230,0,0) if maj else (0,160,255), width=1)
    if maj:
        d.text((px+2, 36), str(x), fill=(220,0,0))
        d.text((px+2, c.shape[0]-50), str(x), fill=(220,0,0))
# 标出候选界
for x, col in [(68,(0,200,0)), (137,(255,0,0)), (199,(0,0,255)), (260,(255,0,255)), (383,(0,180,180))]:
    px = (x-xa)*sc
    d.line([(px, 0), (px, c.shape[0])], fill=col, width=2)
p = R/"runs/tmp/t2_leftzoom_20261015.png"
img.save(p); print("saved", p, img.size)
