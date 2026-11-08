# -*- coding: utf-8 -*-
"""并排 dump 我方整合表 vs 参考表(_llm_corrected)。只读。"""
import sys
from pathlib import Path
from openpyxl import load_workbook

ROOT = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
REF = ROOT / "runs" / "参考表_1015-1044_20261011" / "1015-1044"
MINE = ROOT / "runs" / "table_整合_全量_20261011"

def txt(v):
    if v is None: return ""
    if isinstance(v, str): return v
    if type(v).__name__ == "CellRichText":
        return "".join(b if isinstance(b, str) else (b.text or "") for b in v)
    return str(v)

def rows_of(p, n=None, w=22):
    wb = load_workbook(p, rich_text=True, data_only=True)
    ws = wb.active
    out = []
    for r in range(1, ws.max_row + 1):
        if n and r > n: break
        out.append([txt(ws.cell(row=r, column=c).value)[:w] for c in range(1, ws.max_column + 1)])
    return out, ws.max_row, ws.max_column

for stem in sys.argv[1:]:
    a, ar, ac = rows_of(MINE / f"钻孔柱状图{stem}_整合.xlsx", 16)
    b, br, bc = rows_of(REF / f"钻孔柱状图{stem}_llm_corrected.xlsx", 16)
    print(f"########## {stem}  我方 rows={ar} cols={ac} | 参考 rows={br} cols={bc}")
    print("-- 我方 --")
    for i, row in enumerate(a, 1): print(f" r{i:>3}| " + " | ".join(x.ljust(22) for x in row))
    print("-- 参考 --")
    for i, row in enumerate(b, 1): print(f" r{i:>3}| " + " | ".join(x.ljust(22) for x in row))
    print()
