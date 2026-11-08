# -*- coding: utf-8 -*-
"""按表头映射的每个 keep 格裁原图表头,单独放大,逐格看清楚。"""
import sys, json
import cv2
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
stem = sys.argv[1]
hm = json.load(open(R/"runs"/"table_reconstruct"/f"{stem}_表头映射.json", encoding="utf-8"))
img = cv2.imread(str(R/"data"/"raw_images"/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
b0, b1 = hm["band"]
cells = hm["keep"] + hm["drop_columns"]
cells = sorted(cells, key=lambda c: c["x_in_band"][0])
tiles = []
for c in cells:
    x0, x1 = int(c["x_in_band"][0]), int(c["x_in_band"][1])
    x0, x1 = max(0, x0-4), min(img.shape[1], x1+4)
    t = img[max(0,b0-8):min(img.shape[0],b1+8), x0:x1]
    if t.size == 0: continue
    sc = max(1.0, 150.0 / max(1, t.shape[1]))
    t = cv2.resize(t, None, fx=min(sc,4.0), fy=min(sc,4.0), interpolation=cv2.INTER_CUBIC)
    h = 320
    t = cv2.resize(t, (int(t.shape[1]*h/t.shape[0]), h), interpolation=cv2.INTER_CUBIC)
    tiles.append((c["name"], f"x[{x0},{x1}]", t))
W = sum(t.shape[1]+16 for _,_,t in tiles)
canvas = np.full((400, W, 3), 255, np.uint8)
x = 0
for name, rng, t in tiles:
    canvas[50:50+t.shape[0], x:x+t.shape[1]] = cv2.cvtColor(t, cv2.COLOR_GRAY2BGR)
    cv2.putText(canvas, name, (x+2, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0,0,200), 2)
    cv2.putText(canvas, rng, (x+2, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (150,0,0), 1)
    x += t.shape[1]+16
out = f"表头逐格_{stem}.png"
cv2.imwrite(str(R/"runs"/"tmp"/out), canvas)
print(out, canvas.shape, "->", [(c["name"], c["x_in_band"]) for c in cells])
