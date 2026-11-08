# -*- coding: utf-8 -*-
import sys
import numpy as np, cv2
from pathlib import Path
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

g = cv2.imread(str(paths.RAW_DIR / "钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
ref = R/"runs/参考表_1015-1044_20261011/1015-1044/钻孔柱状图1042_llm_corrected.xlsx"
ws = load_workbook(ref).active

X0, X1 = 540, 1010
WID = X1 - X0
marks = [(632, (0,0,255)), (711, (0,255,255)), (912, (0,255,0))]
tiles, info = [], []
for r in range(2, 22):
    yt, yb = ws.cell(row=r, column=2).value, ws.cell(row=r, column=3).value
    if not yt or not yb: continue
    yt, yb = int(yt), min(int(yb), H)
    if yb - yt < 30: yb = min(yt + 60, H)
    if yt >= H: continue
    sub = g[yt:yb, X0:X1]
    c = cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR)
    for x, col in marks:
        xx = x - X0
        if 0 <= xx < c.shape[1]:
            cv2.line(c, (xx, 0), (xx, c.shape[0]-1), col, 2)
    h = 100
    c = cv2.resize(c, (WID, h), interpolation=cv2.INTER_AREA)   # 统一宽度
    tiles.append(c)
    info.append((r, yt, yb, ws.cell(row=r, column=10).value, ws.cell(row=r, column=11).value))
out = np.vstack(tiles)
p = R/"runs/tmp/t2_rows_composite.png"
cv2.imwrite(str(p), out)
print("拼图:", out.shape, "->", p)
print()
print("行  y带                倾角   真厚")
for r, yt, yb, dip, tt in info:
    print("%-4d [%d,%d]   %-6s %s" % (r, yt, yb, dip, tt))
print()
print("图例: 红=632.7(真厚左界)  黄=711(候选线)  绿=912(柱状右界)")
