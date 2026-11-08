# -*- coding: utf-8 -*-
"""把 audit_invariants 的"值角色检测"应用到 v7 合订表,核对我先前按表头名算的不变量。
只读 v7,不落任何产物。"""
import sys, math, re
from pathlib import Path
import numpy as np
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
from src.tools.audit_invariants import _num, _roles, NUMCOLS

wb = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)
def txt(v):
    if v is None: return ""
    if isinstance(v, str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)

charts = {}
for name in wb.sheetnames:
    ws = wb[name]
    vals = [[txt(c.value) for c in row] for row in ws.iter_rows()]
    charts[name] = {"vals": vals, "hdr": vals[0]}

# 全局容差
all_err = []
for c in charts.values():
    di, ti, _ = _roles(c["vals"], c["hdr"])
    if di is None or ti is None: continue
    vals = c["vals"]
    dmap = {j: _num(vals[j][di]) for j in range(1, len(vals)) if _num(vals[j][di]) is not None}
    for j in range(2, len(vals)):
        t = _num(vals[j][ti])
        if j in dmap and j-1 in dmap and t is not None:
            all_err.append(abs(t - (dmap[j]-dmap[j-1])))
med = float(np.median(all_err)); mad = float(np.median(np.abs(np.asarray(all_err)-med)))
tol = max(0.05, med + 6*1.4826*mad)
print(f"全局容差 tol={tol:.4f}  (n={len(all_err)})")
print(f"\n{'图':>5} {'角色列(累计/层厚)':<16} {'行':>4} {'I1':>4} {'I2':>4} {'登记'}")
notes = []
tot1 = tot2 = 0
for s, c in sorted(charts.items()):
    vals, hdr = c["vals"], c["hdr"]
    di, ti, note = _roles(vals, hdr)
    if note: notes.append((s, note))
    i1 = i2 = 0
    if di is not None and ti is not None:
        dmap = {j: _num(vals[j][di]) for j in range(1, len(vals)) if _num(vals[j][di]) is not None}
        for j in range(2, len(vals)):
            d0, d1 = dmap.get(j-1), dmap.get(j)
            t = _num(vals[j][ti])
            if d0 is not None and d1 is not None:
                if d1 <= d0: i1 += 1
                if t is not None and abs(t-(d1-d0)) > tol: i2 += 1
    tot1 += i1; tot2 += i2
    roles = f"{hdr[di] if di is not None else '?'}/{hdr[ti] if ti is not None else '?'}"
    print(f"{s:>5} {roles:<16} {len(vals)-1:>4} {i1:>4} {i2:>4} {note[:40] if note else ''}")
print(f"\n合计 I1={tot1} I2={tot2}")
print("\n[登记] 角色↔表头名错配:")
for s, n in notes: print(f"  {s}: {n}")
