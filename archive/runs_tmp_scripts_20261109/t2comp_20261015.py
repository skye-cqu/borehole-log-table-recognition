# -*- coding: utf-8 -*-
"""1042:用参考表的真实行带,逐行裁 [540,1000] 拼图,标出候选列界。
目的:肉眼判定 632.7~912 之间到底是 1 列还是 2 列。"""
import sys
import numpy as np, cv2
from pathlib import Path
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

g = cv2.imread(str(paths.RAW_DIR / "钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
ref = R/"runs/参考表_1015-1044_20261011/1015-1044/钻孔柱状图1042_llm_corrected.xlsx"
ws = load_workbook(ref).active

X0, X1 = 540, 1010
marks = [(632, (0,0,255), "632.7 真厚左界"), (711, (0,255,255), "711 候选"), (912, (0,255,0), "912 柱状右界")]
tiles = []
info = []
for r in range(2, 22):
    yt, yb = ws.cell(row=r, column=2).value, ws.cell(row=r, column=3).value
    if not yt or not yb: continue
    yt, yb = int(yt), int(yb)
    if yb - yt < 20: yb = yt + 40
    sub = g[yt:yb, X0:X1]
    if sub.size == 0: continue
    c = cv2.cvtColor(sub, cv2.COLOR_GRAY2BGR)
    for x, col, _ in marks:
        xx = x - X0
        if 0 <= xx < c.shape[1]:
            cv2.line(c, (xx, 0), (xx, c.shape[0]-1), col, 1)
    h = 90
    c = cv2.resize(c, (int(c.shape[1]*h/c.shape[0]), h), interpolation=cv2.INTER_AREA)
    tiles.append(c)
    info.append((r, yt, yb,
                 ws.cell(row=r, column=10).value,   # 倾角
                 ws.cell(row=r, column=11).value))  # 真厚
out = np.vstack(tiles)
p = R/"runs/tmp/t2_rows_composite.png"
cv2.imwrite(str(p), out)
print("拼图:", p, out.shape)
print()
print("行  y带              倾角   真厚")
for r, yt, yb, dip, tt in info:
    print("%-4d [%d,%d]   %-6s %s" % (r, yt, yb, dip, tt))
