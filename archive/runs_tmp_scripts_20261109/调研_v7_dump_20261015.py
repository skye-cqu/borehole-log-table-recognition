# -*- coding: utf-8 -*-
"""v7 合订表:降级图 1032/1042/1019/1033 逐行 dump(只读,不改任何产物)。"""
import sys
from openpyxl import load_workbook

P = r"D:\Skye\Documents\Work\高维智矿\7.13杂活\runs\全量整合_合订表_v7.xlsx"
wb = load_workbook(P, rich_text=True)

def txt(v):
    if v is None: return ""
    if isinstance(v, str): return v
    t = type(v).__name__
    if t == "CellRichText":
        return "".join(b if isinstance(b, str) else (b.text or "") for b in v)
    return str(v)

def dump(name, maxrow):
    ws = wb[name]
    print(f"===== {name} rows={ws.max_row} cols={ws.max_column} =====")
    for r in range(1, min(ws.max_row, maxrow) + 1):
        cells = [txt(ws.cell(row=r, column=c).value) for c in range(1, ws.max_column + 1)]
        print(f"r{r:>3} | " + " | ".join(x[:30].ljust(30) for x in cells))

dump("1032", 30)
print()
dump("1042", 20)
print()
dump("1033", 20)
