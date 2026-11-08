# -*- coding: utf-8 -*-
"""① 1032 深度列:左缘是否有"被切半的字"(判别 源缺失 vs OCR漏读);
② 1042:真厚数值 与 柱状花纹 的 x 区间实测。"""
import json
import cv2
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R/"data"/"raw_images"; TR = R/"runs"/"table_reconstruct"

def bands(stem, ymin):
    rd = json.load(open(TR/f"{stem}_行判定.json", encoding="utf-8"))
    rows = [r for r in rd["rows"] if min(p[1] for p in r["poly"]) >= ymin]
    out = []
    for i in range(len(rows)-1):
        out.append((float(np.mean([p[1] for p in rows[i]["poly"]])),
                    float(np.mean([p[1] for p in rows[i+1]["poly"]]))))
    return out

print("##### 1) 1032 深度格左缘字形宽度(切半判别)")
hm = json.load(open(TR/"钻孔柱状图1032_表头映射.json", encoding="utf-8"))
bs = bands("钻孔柱状图1032", hm["band"][1])
g = cv2.imread(str(RAW/"钻孔柱状图1032.JPG"), cv2.IMREAD_GRAYSCALE)
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
def txt(v):
    if v is None: return ""
    if isinstance(v,str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)
w7 = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)["1032"]

def runs_in(sub, thr=150, minrows=2):
    ink = (sub < thr); colink = ink.sum(axis=0)
    idx = np.where(colink >= minrows)[0]
    if not len(idx): return []
    out = []; s = idx[0]; p = idx[0]
    for i in idx[1:]:
        if i - p > 2: out.append((int(s), int(p))); s = i
        p = i
    out.append((int(s), int(p)))
    return out

n_touch = n_full = 0; rows_touch = []
for i, (a, b) in enumerate(bs):
    if b - a < 8: continue
    sub = g[int(a)+4:int(b)-4, 0:104]
    rs = runs_in(sub)
    if not rs: continue
    first = rs[0]
    widths = [r[1]-r[0]+1 for r in rs]
    med = float(np.median(widths))
    d = txt(w7.cell(row=i+2, column=1).value).strip()
    touch = first[0] == 0
    if touch:
        n_touch += 1
        if len(rows_touch) < 14: rows_touch.append((i+2, d, first, round(med,1), widths))
    else: n_full += 1
print("  左缘起笔(x=0)的行数=%d  有留白的行数=%d" % (n_touch, n_full))
print("  样例(行, v7值, 首墨run, 同格字形宽中位, 全部run宽):")
for t in rows_touch: print("   ", t)

print()
print("##### 2) 1042 真厚数值 x 区间 vs 柱状花纹 x 区间")
hm2 = json.load(open(TR/"钻孔柱状图1042_表头映射.json", encoding="utf-8"))
bs2 = bands("钻孔柱状图1042", hm2["band"][1])
g2 = cv2.imread(str(RAW/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
for i in [1, 2, 3, 4, 5, 7, 9, 11]:
    a, b = bs2[i]
    sub = g2[int(a)+5:int(b)-5, 540:960]
    rs = runs_in(sub, thr=150, minrows=3)
    print("  行%-3d 带高=%-5d x[540,960] 墨run: %s" % (i+2, int(b-a), [(540+u, 540+v) for u,v in rs]))
