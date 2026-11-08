# -*- coding: utf-8 -*-
"""1042 表头右区细读:x=430..960, y=720..1020。"""
import sys
import numpy as np, cv2
from pathlib import Path
from PIL import Image, ImageDraw
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
xa, xb, ya, yb, sc = 430, 960, 715, 1030, 4
sub = g[ya:yb, xa:xb]
c = cv2.resize(cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR), ((xb-xa)*sc, (yb-ya)*sc), interpolation=cv2.INTER_NEAREST)
img = Image.fromarray(cv2.cvtColor(c, cv2.COLOR_BGR2RGB))
d = ImageDraw.Draw(img)
Hh = c.shape[0]
for x in range(xa, xb, 10):
    px = (x-xa)*sc
    maj = (x % 50 == 0)
    d.line([(px, 0), (px, 30 if maj else 14)], fill=(230,0,0) if maj else (0,160,255), width=1)
    d.line([(px, Hh-(30 if maj else 14)), (px, Hh)], fill=(230,0,0) if maj else (0,160,255), width=1)
    if maj:
        d.text((px+2, 32), str(x), fill=(220,0,0))
        d.text((px+2, Hh-46), str(x), fill=(220,0,0))
for x, col, lab in [(469,(0,200,0),"469"), (550,(255,0,0),"550"), (633,(0,0,255),"633"), (709,(255,0,255),"709"), (913,(0,180,180),"913")]:
    px = (x-xa)*sc
    d.line([(px, 0), (px, Hh)], fill=col, width=2)
    d.text((px+3, 6), lab, fill=col)
p = R/"runs/tmp/t2_rightzoom_20261015.png"
img.save(p); print("saved", p, img.size)
