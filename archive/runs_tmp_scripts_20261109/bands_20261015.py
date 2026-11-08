# -*- coding: utf-8 -*-
"""poly = 行上边界。行带 = [poly_i, poly_{i+1}]。"""
import json
import cv2
import numpy as np
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R/"data"/"raw_images"; TR = R/"runs"/"table_reconstruct"; OUT = R/"runs"/"tmp"

def txt(v):
    if v is None: return ""
    if isinstance(v,str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)

def bands(stem, ymin):
    rd = json.load(open(TR/f"{stem}_行判定.json", encoding="utf-8"))
    rows = [r for r in rd["rows"] if min(p[1] for p in r["poly"]) >= ymin]
    out = []
    for i in range(len(rows)-1):
        y0 = float(np.mean([p[1] for p in rows[i]["poly"]]))
        y1 = float(np.mean([p[1] for p in rows[i+1]["poly"]]))
        out.append((y0, y1))
    return out

# ===== 1032 深度列:整行带裁片 =====
hm = json.load(open(TR/"钻孔柱状图1032_表头映射.json", encoding="utf-8"))
bs = bands("钻孔柱状图1032", hm["band"][1])
w7 = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)["1032"]
g = cv2.imread(str(RAW/"钻孔柱状图1032.JPG"), cv2.IMREAD_GRAYSCALE)
print("1032 行带数:", len(bs), " 平均带高:", round(float(np.mean([b-a for a,b in bs])),1))
want = {"15","62","0","45","60","50","20","14.39","2.8","2.2","3","1.1"}
picks = []
for i, (a, b) in enumerate(bs):
    d = txt(w7.cell(row=i+2, column=1).value).strip()
    if d in want and len(picks) < 9: picks.append((i, a, b, d))
print("抽样行:", [(i+2, d, round(a), round(b)) for i,a,b,d in picks])
tiles = []
for i, a, b, d in picks:
    c = g[int(a)-4:int(b)+4, 0:112]
    c = cv2.copyMakeBorder(c, 4,4,4,4, cv2.BORDER_CONSTANT, value=255)
    sc = min(2.0, 190.0/max(1, c.shape[0]))
    c = cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
    c = cv2.cvtColor(c, cv2.COLOR_GRAY2BGR)
    cv2.putText(c, f"r{i+2}={d}", (5, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,0,220), 1)
    cv2.line(c, (4,0), (4,c.shape[0]), (220,0,0), 2)
    tiles.append(c)
h = max(t.shape[0] for t in tiles); wtot = sum(t.shape[1] for t in tiles) + 8*len(tiles)
canvas = np.full((h+8, wtot, 3), 255, np.uint8); x = 0
for t in tiles:
    canvas[4:4+t.shape[0], x:x+t.shape[1]] = t; x += t.shape[1]+8
cv2.imwrite(str(OUT/"e1032_depth.png"), canvas); print("-> e1032_depth.png", canvas.shape)

# ===== 1042 真厚区(x 553..912) =====
hm2 = json.load(open(TR/"钻孔柱状图1042_表头映射.json", encoding="utf-8"))
bs2 = bands("钻孔柱状图1042", hm2["band"][1])
g2 = cv2.imread(str(RAW/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
print("1042 行带数:", len(bs2))
sel = [i for i in range(len(bs2)) if 1 <= i <= 26]
tiles2 = []
for i in sel:
    a, b = bs2[i]
    c = g2[int(a)-3:int(b)+3, 540:930]
    c = cv2.copyMakeBorder(c, 3,3,3,3, cv2.BORDER_CONSTANT, value=255)
    sc = min(1.5, 210.0/max(1, c.shape[0]))
    c = cv2.resize(c, None, fx=sc, fy=sc, interpolation=cv2.INTER_CUBIC)
    c = cv2.cvtColor(c, cv2.COLOR_GRAY2BGR)
    for x0, lab, cl in [(553,"s5",(0,170,0)), (633,"s7",(0,170,0)), (709,"?",(0,0,230)), (912,"s8",(0,170,0))]:
        xi = int((x0-540+3)*sc)
        if 0 <= xi < c.shape[1]:
            cv2.line(c, (xi,0), (xi,c.shape[0]), cl, 1)
    cv2.putText(c, f"r{i+2}", (5, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0,0,220), 1)
    tiles2.append(c)
h2 = max(t.shape[0] for t in tiles2); wtot2 = sum(t.shape[1] for t in tiles2) + 6*len(tiles2)
canvas2 = np.full((h2+6, wtot2, 3), 255, np.uint8); x = 0
for t in tiles2:
    canvas2[3:3+t.shape[0], x:x+t.shape[1]] = t; x += t.shape[1]+6
cv2.imwrite(str(OUT/"e1042_zhj.png"), canvas2); print("-> e1042_zhj.png", canvas2.shape)
