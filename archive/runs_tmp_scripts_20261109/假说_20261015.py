# -*- coding: utf-8 -*-
"""① 1032 深度截断假说:用算术链重建 depth[i]=depth[i-1]+thick[i],看原读数是否为真值后缀;
② 1042 sep_pts 折线沿表高是否漂移(倾角|真厚界 index7)。"""
import cv2, json, re
import numpy as np
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
TR = R/"runs"/"table_reconstruct"

wb = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)
ws = wb["1032"]
def txt(v):
    if v is None: return ""
    if isinstance(v,str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)
def fn(s):
    m = re.fullmatch(r"-?\d+(?:\.\d+)?", str(s).strip().replace("D","0").replace("O","0"))
    return float(m.group()) if m else None

print("##### 1032 深度截断假说(链: depth[i] = depth[i-1] + thick[i])")
cur = None
rows = []
for r in range(2, ws.max_row+1):
    d_raw, t = txt(ws.cell(row=r,column=1).value), fn(txt(ws.cell(row=r,column=2).value))
    if r == 2:
        cur = fn(d_raw); rows.append((r, d_raw, cur, t, "锚")); continue
    if t is None: rows.append((r, d_raw, None, None, "无层厚")); continue
    if cur is None: rows.append((r, d_raw, None, t, "断链")); continue
    want = round(cur + t, 2)
    s = f"{want:.2f}"
    raw = str(d_raw).replace("D","0").replace("O","0").strip()
    suffix = s.endswith(raw) and len(raw) >= 3
    lost = len(s) - len(raw) if suffix else None
    rows.append((r, d_raw, want, t, "后缀✓丢%d位" % lost if suffix else "✗"))
    cur = want
nsuf = sum(1 for x in rows if isinstance(x[4], str) and x[4].startswith("后缀"))
nval = sum(1 for x in rows if x[2] is not None)
print(f"  可比行={nval}  原读数是链值后缀={nsuf} ({nsuf/max(1,nval):.0%})")
lost = [int(x[4][-2]) for x in rows if isinstance(x[4],str) and x[4].startswith("后缀") and x[4][-2].isdigit()]
print(f"  丢失位数分布: {dict((k,lost.count(k)) for k in sorted(set(lost)))}")
print("  前 16 行:")
for x in rows[:16]: print("   ", x)
bad = [x for x in rows if isinstance(x[4],str) and not x[4].startswith("后缀") and x[2] is not None]
print(f"  不合后缀的行 {len(bad)} 条:", [(r,raw,want) for r,raw,want,_,_ in bad][:12])

# ===== ② 1042 sep_pts 漂移 =====
print("\n##### 1042 sep_pts 折线沿表高(表头带 vs 全表)")
hm = json.load(open(TR/"钻孔柱状图1042_表头映射.json", encoding="utf-8"))
seps = hm["sep_pts"]
names = ["s0","s1","s2","s3","s4","s5","s6","s7","s8","s9","s10"]
for y in (800, 2000, 5000, 10000, 15000, 19500):
    vals = []
    for p in seps:
        ys = np.asarray(p["ys"], float); xs = np.asarray(p["xs"], float)
        if y < ys.min() or y > ys.max():
            vals.append("外")
        else:
            vals.append(round(float(np.interp(y, ys, xs)),1))
    print(f"  y={y:>6}: " + " ".join(f"{n}={v}" for n,v in zip(names,vals)))
print("  表头带内 sep_x_band:", [round(v,1) for v in hm["sep_x_band"]])
