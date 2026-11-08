# -*- coding: utf-8 -*-
import json, re
from pathlib import Path
from collections import Counter
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
V7 = R/"runs"/"全量整合_合订表_v7.xlsx"

def txt(v):
    if v is None: return ""
    if isinstance(v,str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)
def sheet(p):
    ws = load_workbook(p, rich_text=True).active
    hdr = [txt(ws.cell(row=1,column=c).value) for c in range(1, ws.max_column+1)]
    rows = [[txt(ws.cell(row=r,column=c).value) for c in range(1, ws.max_column+1)]
            for r in range(2, ws.max_row+1)]
    return hdr, rows

print("##### 1) 1042 倾角列内容")
ws = load_workbook(V7, rich_text=True)["1042"]
hdr = [txt(ws.cell(row=1,column=c).value) for c in range(1, ws.max_column+1)]
print("  hdr:", hdr)
ci = hdr.index("倾角")+1
dip = [txt(ws.cell(row=r,column=ci).value) for r in range(2, ws.max_row+1)]
print("  倾角取值分布(前20):", Counter(dip).most_common(20))
big = [v for v in dip if (m:=re.fullmatch(r"(\d+(?:\.\d+)?)°", v.strip())) and float(m.group(1))>45]
print(f"  >> 倾角>45 格数={len(big)} 样例={big[:12]}")
rh, rr = sheet(R/"runs"/"参考表_1015-1044_20261011"/"1015-1044"/"钻孔柱状图1042_llm_corrected.xlsx")
print("  参考 hdr:", rh[:13])
print("  参考倾角:", [x[9] for x in rr[:14]])
print("  参考真厚:", [x[10] for x in rr[:14]])

print()
print("##### 2) 1032 深度截断检验")
ws2 = load_workbook(V7, rich_text=True)["1032"]
def fn(s):
    m = re.fullmatch(r"-?\d+(?:\.\d+)?", str(s).strip().replace("D","0").replace("O","0"))
    return float(m.group()) if m else None
cur = fn(txt(ws2.cell(row=2,column=1).value)); nval=nsuf=0; bad=[]
for r in range(3, ws2.max_row+1):
    t = fn(txt(ws2.cell(row=r,column=2).value))
    raw = str(txt(ws2.cell(row=r,column=1).value)).replace("D","0").replace("O","0").strip()
    if t is None or cur is None:
        bad.append((r,raw,"无层厚/断链")); continue
    want = round(cur + t, 2); s = f"{want:.2f}"
    nval += 1
    if s.endswith(raw) and len(raw) >= 3: nsuf += 1
    else: bad.append((r, raw, s))
    cur = want
print(f"  可比={nval} 后缀吻合={nsuf} ({nsuf/max(1,nval):.0%})")
print(f"  不吻合 {len(bad)} 条前15:", bad[:15])
print("  层厚列前15:", [txt(ws2.cell(row=r,column=2).value) for r in range(2,17)])

print()
print("##### 3) 行数对照")
wb7 = load_workbook(V7)
for k in ("1032","1042"):
    a = wb7[k]
    b = load_workbook(R/"runs"/"参考表_1015-1044_20261011"/"1015-1044"/f"钻孔柱状图{k}_llm_corrected.xlsx").active
    print(f"  {k}: 我方 {a.max_row-1} 行 {a.max_column} 列 / 参考 {b.max_row-1} 行 {b.max_column} 列")
