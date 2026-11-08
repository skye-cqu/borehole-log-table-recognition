# -*- coding: utf-8 -*-
"""1042 定案:(a)表头字形簇 (b)数据行满高竖笔+数字串位置 → 真列界。"""
import json, sys
import numpy as np, cv2
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

stem = "钻孔柱状图1042"
g = cv2.imread(str(paths.RAW_DIR/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
H, W = g.shape
rj = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_行判定.json").read_text(encoding="utf-8"))
rows = rj["rows"]
hm = json.loads((paths.RUNS_DIR/"table_reconstruct"/f"{stem}_表头映射.json").read_text(encoding="utf-8"))
print("sep_x_band =", hm["sep_x_band"])

def runs_x(y0, y1, x0, x1, mincov):
    d = (g[int(y0):int(y1), x0:x1] < 140)
    if d.shape[0] < 4: return []
    cf = d.mean(axis=0)
    out, i = [], 0
    while i < len(cf):
        if cf[i] >= mincov:
            j = i
            while j < len(cf) and cf[j] >= mincov: j += 1
            out.append((x0+(i+j-1)/2.0, float(cf[i:j].max()), j-i)); i = j
        else: i += 1
    return out

print()
print("== 数据行满高竖笔(覆盖>=0.80) 全宽 ==")
for idx in [5, 7, 8, 9, 10, 11, 12]:
    a = rows[idx]["poly"][-1]; b = rows[idx+1]["poly"][-1]
    y0, y1 = a[1], b[1]
    if y1-y0 < 25: continue
    st = runs_x(y0+3, y1-3, 0, W, 0.80)
    print("  r%-3d y=[%6.0f,%6.0f] h=%-4.0f  %s" % (idx, y0, y1, y1-y0,
          " ".join("%.0f" % s for s,_,_ in st)))

print()
print("== 表头带字形簇(剔除覆盖>=0.85的线列) ==")
y0, y1 = hm["band"]
d = (g[int(y0):int(y1)] < 140)
cf = d.mean(axis=0)
mask = np.ones(W, bool)
for x in np.where(cf >= 0.85)[0]: mask[max(0,x-2):x+3] = False
prof = d[:, mask].sum(axis=1) if False else (d & mask[None, :]).sum(axis=0)
cl, i = [], 0
while i < W:
    if prof[i] > 0:
        j = i
        while j < W and prof[j] > 0: j += 1
        if j-i >= 6: cl.append((i, j))
        i = j
    else: i += 1
print("  表头字形簇 %d 个:" % len(cl))
for a, b in cl:
    if a > 1200: continue
    print("     x=[%4d,%4d] 宽=%-4d 中心=%-5.0f" % (a, b, b-a, (a+b)/2))

print()
print("== 数字串位置(逐行OCR候选) ==")
for idx in [5, 7, 10]:
    a = rows[idx]["poly"][-1]; b = rows[idx+1]["poly"][-1]
    y0, y1 = a[1], b[1]
    if y1-y0 < 25: continue
    sub = (g[int(y0)+3:int(y1)-3] < 140)
    pf = sub.sum(axis=0)
    tk, i = [], 0
    while i < len(pf):
        if pf[i] > 0:
            j = i
            while j < len(pf) and pf[j] > 0: j += 1
            if j-i >= 4: tk.append((i, j))
            i = j
        else: i += 1
    merged = []
    for a2, b2 in tk:
        if merged and a2 - merged[-1][1] <= 12: merged[-1] = (merged[-1][0], b2)
        else: merged.append((a2, b2))
    print("  r%-3d y=[%.0f,%.0f]: %s" % (idx, y0, y1,
          " ".join("[%d,%d]" % m for m in merged if m[0] < 1200)))
