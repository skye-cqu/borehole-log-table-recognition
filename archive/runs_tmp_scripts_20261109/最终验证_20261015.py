# -*- coding: utf-8 -*-
"""三项决定性验证。"""
import cv2, json, re
import numpy as np
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R/"data"/"raw_images"; TR = R/"runs"/"table_reconstruct"; OUT = R/"runs"/"tmp"

# ===== ① 1023:交换 C/D 两列后不变量是否恢复 =====
wb = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)
ws = wb["1023"]
def txt(v):
    if v is None: return ""
    if isinstance(v,str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)
def fn(s):
    m = re.fullmatch(r"-?\d+(?:\.\d+)?", str(s).strip())
    return float(m.group()) if m else None
def inv(cdepth, cthick):
    d = [fn(txt(ws.cell(row=r,column=cdepth).value)) for r in range(2, ws.max_row+1)]
    t = [fn(txt(ws.cell(row=r,column=cthick).value)) for r in range(2, ws.max_row+1)]
    I1 = sum(1 for i in range(1,len(d)) if d[i] is not None and d[i-1] is not None and d[i] < d[i-1]-1e-9)
    cmp2 = I2 = 0
    for i in range(1,len(d)):
        if d[i] is None or d[i-1] is None or t[i] is None: continue
        cmp2 += 1
        if abs((d[i]-d[i-1]) - t[i]) > 0.011: I2 += 1
    return I1, I2, cmp2
print("##### 1023 列语义检验(表头 C=层厚 D=深度)")
print("  现状 (深度=C, 层厚=D):", inv(3,4))
print("  交换后 (深度=D, 层厚=C):", inv(4,3))

# ===== ② 1042 真厚列[633,710] 是否有数据 =====
hm = json.load(open(TR/"钻孔柱状图1042_表头映射.json", encoding="utf-8"))
rd = json.load(open(TR/"钻孔柱状图1042_行判定.json", encoding="utf-8"))
g = cv2.imread(str(RAW/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
rows = [r for r in rd["rows"] if min(p[1] for p in r["poly"]) >= hm["band"][1]]
ys = [float(np.mean([p[1] for p in r["poly"]])) for r in rows]
print("\n##### 1042 [633,710] 与对照区[468,551](采长) 的墨量")
ink = []
for i in range(min(20, len(ys)-1)):
    y0, y1 = int(ys[i])+10, int(ys[i+1])-10
    if y1-y0 < 12: continue
    a = (g[y0:y1, 640:705] < 140).mean()
    b = (g[y0:y1, 475:545] < 140).mean()
    ink.append((i+2, round(float(a),4), round(float(b),4)))
print("  (行, [633,710]墨占比, [468,551]采长墨占比)")
for x in ink: print("   ", x)

# ===== ③ 1032 可疑深度格 =====
print("\n##### 1032 可疑深度格(原图裁片)")
g2 = cv2.imread(str(RAW/"钻孔柱状图1032.JPG"), cv2.IMREAD_GRAYSCALE)
hm2 = json.load(open(TR/"钻孔柱状图1032_表头映射.json", encoding="utf-8"))
rd2 = json.load(open(TR/"钻孔柱状图1032_行判定.json", encoding="utf-8"))
rows2 = [r for r in rd2["rows"] if min(p[1] for p in r["poly"]) >= hm2["band"][1]]
ys2 = [float(np.mean([p[1] for p in r["poly"]])) for r in rows2]
for rn in (9, 10, 14, 24):
    i = rn - 2
    if i+1 >= len(ys2): continue
    y0, y1 = int(ys2[i])+4, int(ys2[i+1])-4
    c = g2[y0:y1, 0:105]
    c = cv2.resize(c, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
    cv2.imwrite(str(OUT/f"c1032_depth_r{rn}.png"), c)
    print(f"  行{rn} y[{y0},{y1}] -> c1032_depth_r{rn}.png")
