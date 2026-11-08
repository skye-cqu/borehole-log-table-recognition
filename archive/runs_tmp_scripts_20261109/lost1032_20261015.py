# -*- coding: utf-8 -*-
"""1032: B还原(104 行) -> 整合(103 行),定位消失的那一行。"""
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
def txt(v):
    if v is None: return ""
    if isinstance(v,str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)
def rows_of(p):
    ws = load_workbook(p, rich_text=True).active
    return [[txt(ws.cell(row=r,column=c).value) for c in range(1, ws.max_column+1)]
            for r in range(2, ws.max_row+1)]
B = rows_of(R/"runs"/"table_reconstruct_重出_20261005_项④行线补全"/"钻孔柱状图1032_还原.xlsx")
I = rows_of(R/"runs"/"table_整合_全量_20261011"/"钻孔柱状图1032_整合.xlsx")
print("B还原 %d 行 / 整合 %d 行" % (len(B), len(I)))
# 找第一处不一致
k = 0
while k < min(len(B), len(I)) and B[k] == I[k]: k += 1
print("首个不一致处: B行%d  vs  整合行%d" % (k+1, k+1))
for j in range(max(0,k-2), min(len(B), k+4)):
    print("  B[%3d] %s" % (j+1, B[j]))
print()
for j in range(max(0,k-2), min(len(I), k+3)):
    print("  I[%3d] %s" % (j+1, I[j]))
