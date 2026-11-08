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
wb7 = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)
print("图    v7行  参考行  B还原行  差(v7-参考)")
for k in ["1015","1019","1023","1032","1042"]:
    rp = R/"runs"/"参考表_1015-1044_20261011"/"1015-1044"/f"钻孔柱状图{k}_llm_corrected.xlsx"
    nr = load_workbook(rp).active.max_row-1
    n7 = wb7[k].max_row-1
    nb = load_workbook(R/"runs"/"table_reconstruct_重出_20261005_项④行线补全"/f"钻孔柱状图{k}_还原.xlsx").active.max_row-1
    print("  %-5s %-5d %-6d %-7d %d" % (k, n7, nr, nb, n7-nr))
print()
print("1019 参考表 前 6 行 全列:")
wr = load_workbook(R/"runs"/"参考表_1015-1044_20261011"/"1015-1044"/"钻孔柱状图1019_llm_corrected.xlsx").active
hr = [txt(wr.cell(row=1,column=c).value) for c in range(1, wr.max_column+1)]
print("  hdr:", hr[:13])
for i in range(2, 8):
    print("  行%d" % i, [txt(wr.cell(row=i,column=c).value)[:22] for c in range(1, 14)])
print()
print("1019 v7 前 6 行 全列:")
w7 = wb7["1019"]
for i in range(2, 8):
    print("  行%d" % i, [txt(w7.cell(row=i,column=c).value)[:22] for c in range(1, w7.max_column+1)])
