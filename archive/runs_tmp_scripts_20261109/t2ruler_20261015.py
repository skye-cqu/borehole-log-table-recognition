# -*- coding: utf-8 -*-
"""1042:带标尺的行带拼图,客观读出 倾角/真厚/柱状 的真实列界。"""
import sys
import numpy as np, cv2
from pathlib import Path
from PIL import Image, ImageDraw
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

g = cv2.imread(str(paths.RAW_DIR/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ref = R/"runs/参考表_1015-1044_20261011/1015-1044/钻孔柱状图1042_llm_corrected.xlsx"
ws = load_workbook(ref).active

X0, X1, SC = 430, 990, 3
rows = [2, 5, 6, 8, 10, 14, 16, 19]
tiles, labs = [], []
for r in rows:
    yt, yb = ws.cell(row=r,column=2).value, ws.cell(row=r,column=3).value
    if not yt or not yb: continue
    yt, yb = int(yt), min(int(yb), g.shape[0])
    if yb-yt < 40: yb = min(yt+70, g.shape[0])
    sub = g[yt:yb, X0:X1]
    c = cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR)
    c = cv2.resize(c, ((X1-X0)*SC, max(int(sub.shape[0]*SC), 1)), interpolation=cv2.INTER_CUBIC)
    tiles.append(c)
    labs.append("r%d 深%s 厚%s 采%s 倾%s 真%s" % (
        r, ws.cell(row=r,column=7).value, ws.cell(row=r,column=8).value,
        ws.cell(row=r,column=9).value, ws.cell(row=r,column=10).value,
        ws.cell(row=r,column=11).value))

H = sum(t.shape[0] for t in tiles) + 40*len(tiles) + 46
W = (X1-X0)*SC
canvas = np.full((H, W, 3), 255, np.uint8)
y = 46
for t, lb in zip(tiles, labs):
    canvas[y:y+t.shape[0]] = t
    y += t.shape[0] + 40
img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
d = ImageDraw.Draw(img)
for x in range(X0, X1, 10):
    px = (x-X0)*SC
    major = (x % 50 == 0)
    d.line([(px,0),(px,46 if major else 26)], fill=(255,0,0) if major else (0,160,255), width=1)
    if major:
        d.text((px+2, 2), str(x), fill=(200,0,0))
for x, col, nm in [(468,(0,0,255),"468"),(551,(0,140,255),"551"),(633,(255,0,255),"633"),
                   (715,(0,180,0),"715?"),(745,(160,0,160),"745?"),(790,(120,80,0),"790?"),(912,(0,0,0),"912")]:
    px = (x-X0)*SC
    if 0 <= px < W:
        d.line([(px,0),(px,H)], fill=col, width=1)
y = 46
for t, lb in zip(tiles, labs):
    d.text((4, y+t.shape[0]+6), lb, fill=(0,0,180))
    y += t.shape[0] + 40
p = R/"runs/tmp/t2_ruler_20261015.png"
img.save(p)
print("saved", p, img.size)
print("竖线颜色: 468红 551橙 633品红 715绿 745紫 790棕 912黑")
