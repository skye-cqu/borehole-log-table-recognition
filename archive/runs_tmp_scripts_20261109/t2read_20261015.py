# -*- coding: utf-8 -*-
"""1042:细标尺高倍裁片,直读 真厚|柱状 界在哪。"""
import sys
import numpy as np, cv2
from pathlib import Path
from PIL import Image, ImageDraw
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)

def tile(x0, x1, y0, y1, sc, label):
    sub = g[y0:y1, x0:x1]
    c = cv2.resize(cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR),
                   ((x1-x0)*sc, (y1-y0)*sc), interpolation=cv2.INTER_NEAREST)
    return c, x0, x1, sc, label

specs = [
    (600, 960, 740, 935, 6, "表头带 y=[740,935]"),
    (600, 960, 4035, 4120, 8, "行6 真厚=4.67"),
    (600, 960, 4726, 4878, 6, "行14 真厚=3.52"),
]
tiles = [tile(*s) for s in specs]
W = max(t[0].shape[1] for t in tiles)
H = sum(t[0].shape[0] for t in tiles) + 60*len(tiles) + 40
canvas = np.full((H, W, 3), 255, np.uint8)
y = 40
for c, x0, x1, sc, lb in tiles:
    canvas[y:y+c.shape[0], 0:c.shape[1]] = c
    y += c.shape[0] + 60
img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
d = ImageDraw.Draw(img)
y = 40
for c, x0, x1, sc, lb in tiles:
    h = c.shape[0]
    for x in range(x0, x1, 10):
        px = (x-x0)*sc
        if px >= W: break
        major = (x % 50 == 0)
        d.line([(px, y-24 if major else y-12), (px, y+h)], fill=(255,0,0) if major else (120,180,255), width=1)
        if major: d.text((px+2, y-36), str(x), fill=(200,0,0))
    d.text((4, y+h+6), lb, fill=(0,0,180))
    y += h + 60
p = R/"runs/tmp/t2_read_20261015.png"
img.save(p)
print("saved", p, img.size)
