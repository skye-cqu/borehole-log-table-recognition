# -*- coding: utf-8 -*-
"""1042:把 sep_x_band(绿) 与 表头实测满高竖笔(红,未在sep里) 叠在原图上直接读。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
from PIL import Image, ImageDraw
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

RECON = paths.RUNS_DIR/"table_reconstruct"
stem = "钻孔柱状图1042"
hm = json.loads((RECON/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
g = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
y0, y1 = int(hm["band"][0]), int(hm["band"][1])
dark = (g[y0:y1] < 140)
cf = dark.mean(axis=0)
strokes = []
x = 0
while x < len(cf):
    if cf[x] >= 0.45:
        j = x
        while j < len(cf) and cf[j] >= 0.45: j += 1
        strokes.append((float((x+j-1)/2), float(cf[x:j].max()))); x = j
    else: x += 1
seps = sorted(hm["sep_x_band"])
print("表头带满高竖笔:", [round(s,1) for s,_ in strokes])
print("sep_x_band   :", [round(s,1) for s in seps])
missing = [(s,f) for s,f in strokes if not any(abs(s-v)<=4 for v in seps)]
print("实测有/sep无 :", [(round(s), round(f,2)) for s,f in missing])
print("sep有/实测无 :", [round(v,1) for v in seps if not any(abs(s-v)<=4 for s,_ in strokes)])

tiles = [(60, 1000, y0-25, y1+35, 3, "表头带 y=[%d,%d]" % (y0,y1)),
         (60, 1000, 4020, 4680, 3, "数据行 y=[4020,4680]")]
outs = []
for xa, xb, ya, yb, sc, lb in tiles:
    sub = g[ya:yb, xa:xb]
    c = cv2.resize(cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR), ((xb-xa)*sc, (yb-ya)*sc), interpolation=cv2.INTER_NEAREST)
    outs.append([c, xa, xb, ya, yb, sc, lb])

W = max(o[0].shape[1] for o in outs) + 90
H = sum(o[0].shape[0] for o in outs) + 90*len(outs) + 40
canvas = np.full((H, W, 3), 255, np.uint8)
yy = 40
for c, xa, xb, ya, yb, sc, lb in outs:
    canvas[yy:yy+c.shape[0], 90:90+c.shape[1]] = c
    yy += c.shape[0] + 90
img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
d = ImageDraw.Draw(img)
yy = 40
for c, xa, xb, ya, yb, sc, lb in outs:
    h = c.shape[0]
    for v in seps:
        if not (xa <= v <= xb): continue
        px = 90 + (v-xa)*sc
        d.line([(px, yy), (px, yy+h)], fill=(0,170,0), width=2)
        d.text((px+2, yy-16), "%.0f" % v, fill=(0,140,0))
    for s, f in missing:
        if not (xa <= s <= xb): continue
        px = 90 + (s-xa)*sc
        d.line([(px, yy), (px, yy+h)], fill=(230,0,0), width=2)
        d.text((px+2, yy+h+4), "%.0f" % s, fill=(200,0,0))
    for x in range(xa, xb, 50):
        px = 90 + (x-xa)*sc
        d.line([(px, yy+h), (px, yy+h+10)], fill=(0,0,255), width=1)
        d.text((px+2, yy+h+14), str(x), fill=(0,0,200))
    d.text((4, yy+h//2), lb, fill=(0,0,180))
    yy += h + 90
p = R/"runs/tmp/t2_overlay_20261015.png"
img.save(p); print("saved", p, img.size)
