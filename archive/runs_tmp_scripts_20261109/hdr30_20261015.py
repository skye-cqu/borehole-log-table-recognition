# -*- coding: utf-8 -*-
from pathlib import Path
from collections import Counter
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
D = R/"runs"/"table_整合_全量_20261011"
cnt = Counter()
print("图     列数  表头")
for k in range(1015, 1045):
    p = D/f"钻孔柱状图{k}_整合.xlsx"
    ws = load_workbook(p, rich_text=True).active
    hdr = tuple(str(ws.cell(row=1,column=c).value) for c in range(1, ws.max_column+1))
    cnt[hdr] += 1
    if len(hdr) != 8:
        print("  %-5d %-4d %s" % (k, len(hdr), list(hdr)))
print()
print("== 表头形态统计 ==")
for h, n in cnt.most_common():
    print("  x%d  %s" % (n, list(h)))
