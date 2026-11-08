# -*- coding: utf-8 -*-
"""① 1032 深度列缺首位假说检验;② 1042 逐行竖线(容差±10px);③ 1023 验收.json"""
import cv2, json, re
import numpy as np
from pathlib import Path
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
RAW = R/"data"/"raw_images"; TR = R/"runs"/"table_reconstruct"

# ===== ① 1032 深度缺首位 =====
wb = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)
ws = wb["1032"]
def cell(r,c): 
    v = ws.cell(row=r,column=c).value
    return "" if v is None else str(v)
def fn(s):
    m = re.fullmatch(r"-?\d+(?:\.\d+)?", s.strip())
    return float(m.group()) if m else None
print("##### 1032 深度列缺首位检验(层厚 是否 = Δ深度)")
ok = bad = skip = 0
detail = []
for r in range(3, ws.max_row+1):
    d0, d1, t = fn(cell(r-1,1)), fn(cell(r,1)), fn(cell(r,2))
    if d0 is None or d1 is None or t is None: skip += 1; continue
    delta = round(d1 - d0, 2)
    if abs(delta - t) <= 0.011: ok += 1
    else:
        bad += 1
        if len(detail) < 10: detail.append((r, d0, d1, t, round(delta,2)))
print(f"  直接相减成立 {ok} 条, 不成立 {bad} 条, 跳过 {skip}")
print("  不成立样例(行,上行深度,本行深度,本行层厚,实测Δ):", detail)

# 尝试补首位: 找最小 k 使 深度+k*10^p 满足链
print("\n  >> 逐行补首位重建(贪心:上行深度+本行层厚 = 本行真深度):")
prev = 3.7; fixed = []
for r in range(3, ws.max_row+1):
    t = fn(cell(r,2)); d = fn(cell(r,1))
    if t is None or d is None: fixed.append(None); continue
    want = round(prev + t, 2)
    s = f"{want:.2f}"
    got = f"{d}"
    match = s.endswith(got.replace("D","6").replace("O","0")) or got in s
    fixed.append((r, d, want, match))
    prev = want
nm = sum(1 for f in fixed if f and f[3]); tt = sum(1 for f in fixed if f)
print(f"    '原值是本行应有值的后缀' 成立 {nm}/{tt} = {nm/max(1,tt):.0%}")
print("    样例:", [(r,d,w,m) for r,d,w,m in fixed[:8] if r])

# ===== ② 1042 逐行竖线(容差) =====
hm = json.load(open(TR/"钻孔柱状图1042_表头映射.json", encoding="utf-8"))
rd = json.load(open(TR/"钻孔柱状图1042_行判定.json", encoding="utf-8"))
g = cv2.imread(str(RAW/"钻孔柱状图1042.JPG"), cv2.IMREAD_GRAYSCALE)
rows = [r for r in rd["rows"] if min(p[1] for p in r["poly"]) >= hm["band"][1]]
ys = [float(np.mean([p[1] for p in r["poly"]])) for r in rows]
cands = [633, 637, 709, 713, 753, 872, 912]
hit = {c:0 for c in cands}; n=0
for i in range(len(ys)-1):
    y0,y1 = int(ys[i])+6, int(ys[i+1])-6
    if y1-y0 < 8: continue
    n += 1
    frac = (g[y0:y1] < 150).mean(axis=0)
    for c in cands:
        w = frac[max(0,c-10):c+11]
        if w.size and w.max() >= 0.60: hit[c] += 1
print(f"\n##### 1042 逐行竖线(±10px, 阈值0.60) 可比行={n}")
for c in cands: print(f"    x≈{c:>4}: {hit[c]:>4}/{n} = {hit[c]/max(1,n):.0%}")

# ===== ③ 1023 验收.json =====
p = R/"runs"/"table_整合_全量_20261011"/"钻孔柱状图1023_验收.json"
rep = json.load(open(p, encoding="utf-8"))
print("\n##### 1023 验收.json")
print("  名带:", rep["名带"])
print("  门禁问题数:", len(rep["门禁问题"]))
import collections
print("  门禁分类:", collections.Counter(f.get("列") for f in rep["门禁问题"]))
print("  样例:", rep["门禁问题"][:3])
