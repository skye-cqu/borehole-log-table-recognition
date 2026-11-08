# -*- coding: utf-8 -*-
"""1032 深度列截断判别:逐行带测"首个墨像素 x"。
若数字被扫描左缘切掉 => 首墨 x≈0(墨紧贴图像左缘,无留白);
若数字完整       => 首墨 x 有正常留白(与 层厚 列留白同量级)。"""
import json
import cv2
import numpy as np
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R/"data"/"raw_images"; TR = R/"runs"/"table_reconstruct"

def txt(v):
    if v is None: return ""
    if isinstance(v,str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)

rd = json.load(open(TR/"钻孔柱状图1032_行判定.json", encoding="utf-8"))
hm = json.load(open(TR/"钻孔柱状图1032_表头映射.json", encoding="utf-8"))
rows = [r for r in rd["rows"] if min(p[1] for p in r["poly"]) >= hm["band"][1]]
g = cv2.imread(str(RAW/"钻孔柱状图1032.JPG"), cv2.IMREAD_GRAYSCALE)
w7 = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)["1032"]

def first_ink(y0, y1, x0, x1, thr=150, minrows=2):
    sub = g[int(y0):int(y1), int(x0):int(x1)]
    ink = (sub < thr)
    colink = ink.sum(axis=0)
    idx = np.where(colink >= minrows)[0]
    return int(idx[0]) + int(x0) if len(idx) else None

res = []
for i in range(len(rows)-1):
    y0 = float(np.mean([p[1] for p in rows[i]["poly"]]))
    y1 = float(np.mean([p[1] for p in rows[i+1]["poly"]]))
    if y1 - y0 < 8: continue
    a = first_ink(y0+4, y1-4, 0, 104)      # 深度格 x[0,105)
    b = first_ink(y0+4, y1-4, 107, 190)    # 层厚格 x[105,192)
    d = txt(w7.cell(row=i+2, column=1).value).strip()
    res.append((i+2, d, a, b, None if a is None else a-0, None if b is None else b-107))

v = [r for r in res if r[2] is not None and r[3] is not None]
print("行数:", len(res), " 两者都有墨:", len(v))
a0 = np.array([r[2] for r in v]); b0 = np.array([r[3] for r in v])
print("深度格 首墨 x: 中位=%d 均值=%.1f  min=%d  <=3px 的行数=%d/%d" % (np.median(a0), a0.mean(), a0.min(), (a0<=3).sum(), len(a0)))
print("层厚格 首墨(相对列左界): 中位=%d 均值=%.1f  min=%d  <=3px 的行数=%d/%d" % (np.median(b0), b0.mean(), b0.min(), (b0<=3).sum(), len(b0)))
print()
print("按 v7 深度位数分组(首墨 x 中位):")
from collections import defaultdict
grp = defaultdict(list)
for r in res:
    if r[2] is None: continue
    grp[len(r[1].replace(".",""))].append(r[2])
for k in sorted(grp): print("  位数=%d  n=%3d  首墨中位=%.1f  min=%d  max=%d" % (k, len(grp[k]), np.median(grp[k]), min(grp[k]), max(grp[k])))
print()
print("全部行 (行号, v7值, 深度首墨x, 层厚首墨x):")
for r in res[:40]: print("   ", r)
