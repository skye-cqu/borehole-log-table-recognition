# -*- coding: utf-8 -*-
"""修正口径重算:层厚属于"深度=区间底"的那一行 → I2: depth[i]-depth[i-1] == thick[i]。
按每 sheet 的【实际表头名】取列(不是硬编码序)。只读。"""
import json, re
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
wb = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)

def txt(v):
    if v is None: return ""
    if isinstance(v, str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)
def fnum(s):
    m = re.fullmatch(r"-?\d+(?:\.\d+)?", str(s).strip())
    return float(m.group()) if m else None

print(f"{'图':>5} {'列数':>4} {'行数':>4} | I1深度逆序 I2层厚≠Δ I3真厚>层厚 I4采长>层厚 I5倾角>90 | I2可比")
out = []
for name in wb.sheetnames:
    ws = wb[name]
    hdr = [txt(ws.cell(row=1, column=c).value) for c in range(1, ws.max_column+1)]
    ci = {h: i+1 for i, h in enumerate(hdr)}
    def g(h, r):
        c = ci.get(h)
        return txt(ws.cell(row=r, column=c).value) if c else ""
    rs = range(2, ws.max_row+1)
    d = [fnum(g("深度", r)) for r in rs]
    t = [fnum(g("层厚", r)) for r in rs]
    z = [fnum(g("真厚", r)) for r in rs]
    cc = [fnum(g("采长", r)) for r in rs]
    dp = [g("倾角", r) for r in rs]
    I1 = sum(1 for i in range(1, len(d)) if d[i] is not None and d[i-1] is not None and d[i] < d[i-1]-1e-9)
    cmp2 = 0; I2 = 0
    for i in range(1, len(d)):
        if d[i] is None or d[i-1] is None or t[i] is None: continue
        cmp2 += 1
        if abs((d[i]-d[i-1]) - t[i]) > 0.011: I2 += 1
    I3 = sum(1 for i in range(len(t)) if t[i] is not None and z[i] is not None and z[i] > t[i]*1.05+0.05)
    I4 = sum(1 for i in range(len(t)) if t[i] is not None and cc[i] is not None and cc[i] > t[i]*1.05+0.05)
    I5 = sum(1 for s in dp if (m:=re.fullmatch(r"(\d+(?:\.\d+)?)°", s.strip())) and float(m.group(1))>90)
    print(f"{name:>5} {ws.max_column:>4} {ws.max_row-1:>4} | {I1:>9} {I2:>8} {I3:>9} {I4:>9} {I5:>8} | {cmp2:>6}")
    out.append({"图":name,"列数":ws.max_column,"表头":hdr,"I1":I1,"I2":I2,"I2可比":cmp2,"I3":I3,"I4":I4,"I5":I5})
json.dump(out, open(R/"runs"/"tmp"/"审计_v7_修正口径_20261015.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n-- 非 8 列 / 表头非标准 --")
for o in out:
    if o["列数"] != 8: print("  ", o["图"], o["列数"], o["表头"])
