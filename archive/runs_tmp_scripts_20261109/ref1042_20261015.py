# -*- coding: utf-8 -*-
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
def txt(v):
    if v is None: return ""
    if isinstance(v,str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)
wr = load_workbook(R/"runs"/"参考表_1015-1044_20261011"/"1015-1044"/"钻孔柱状图1042_llm_corrected.xlsx").active
print("参考 1042 行28-34 (序号,时代,层号,深度,层厚,采长,倾角,真厚):")
for i in range(28, 35):
    print("  行%d" % i, [txt(wr.cell(row=i,column=c).value) for c in (1,5,6,7,8,9,10,11)])
print()
print("参考 1042 全部非空倾角:")
for i in range(2, wr.max_row+1):
    v = txt(wr.cell(row=i,column=10).value).strip()
    if v: print("   行%-4d 倾角=%-6s 深度=%-9s 真厚=%s" % (i, v, txt(wr.cell(row=i,column=7).value), txt(wr.cell(row=i,column=11).value)))
