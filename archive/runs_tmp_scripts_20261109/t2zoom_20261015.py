# -*- coding: utf-8 -*-
"""1042:单行带高倍裁片 + 标尺,肉眼直读列界。"""
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

X0, X1, SC = 430, 1000, 4
rows = [6, 8, 10, 16, 19]
tiles, labs = [], []
for r in rows:
    yt, yb = int(ws.cell(row=r,column=2).value), int(ws.cell(row=r,column=3).value)
    yb = min(yb, g.shape[0])
    if yb-yt < 40: yb = min(yt+70, g.shape[0])
    sub = g[yt:yb, X0:X1]
    c = cv2.resize(cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR), ((X1-X0)*SC, sub.shape[0]*SC), interpolation=cv2.INTER_CUBIC)
    tiles.append(c)
    labs.append("r%d 层厚=%s 采长=%s 倾角=%s 真厚=%s 柱状=%s" % (
        r, ws.cell(row=r,column=8).value, ws.cell(row=r,column=9).value,
        ws.cell(row=r,column=10).value, ws.cell(row=r,column=11).value, ws.cell(row=r,column=12).value))

RH = 30
W = (X1-X0)*SC
H = 56 + sum(t.shape[0]+RH for t in tiles)
canvas = np.full((H, W, 3), 255, np.uint8)
y = 56
for t in tiles:
    canvas[y:y+t.shape[0]] = t
    y += t.shape[0] + RH
img = Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))
d = ImageDraw.Draw(img)
for x in range(X0, X1):
    if x % 50: continue
    px = (x-X0)*SC
    d.line([(px,20),(px,H)], fill=(255,0,0), width=1)
    d.text((px+2, 4), str(x), fill=(200,0,0))
for x, col in [(633,(255,0,255)),(709,(0,180,0)),(790,(160,80,0)),(912,(0,0,0))]:
    px = (x-X0)*SC
    d.line([(px,20),(px,H)], fill=col, width=1)
y = 56
for t, lb in zip(tiles, labs):
    d.text((4, y+t.shape[0]+4), lb, fill=(0,0,180))
    y += t.shape[0] + RH
p = R/"runs/tmp/t2_zoom_20261015.png"
img.save(p)
print("saved", p, img.size, " 缩放=%dx  x范围=[%d,%d]" % (SC, X0, X1))
print("红线=x%50 品红=633 绿=709 棕=790 黑=912")
