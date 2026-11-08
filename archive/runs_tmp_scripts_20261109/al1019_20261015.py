# -*- coding: utf-8 -*-
"""1019: 参考表(118行) vs v7(110行) 逐行对齐,找差在哪。"""
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
def txt(v):
    if v is None: return ""
    if isinstance(v,str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)
wr = load_workbook(R/"runs"/"参考表_1015-1044_20261011"/"1015-1044"/"钻孔柱状图1019_llm_corrected.xlsx").active
w7 = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)["1019"]
# 参考: 列7=深度
ref = [(i, txt(wr.cell(row=i,column=7).value).strip()) for i in range(2, wr.max_row+1)]
v7  = [(i, txt(w7.cell(row=i,column=3).value).strip()) for i in range(2, w7.max_row+1)]
print("参考 非空深度=%d / %d 行 ; v7 非空深度=%d / %d 行" % (
    sum(1 for _,v in ref if v), len(ref), sum(1 for _,v in v7 if v), len(v7)))
print()
print("参考深度序列(前 40):", [v for _,v in ref[:40]])
print()
print("v7   深度序列(前 40):", [v for _,v in v7[:40]])
print()
print("参考 末尾 12 行深度:", [v for _,v in ref[-12:]])
print("v7   末尾 12 行深度:", [v for _,v in v7[-12:]])
