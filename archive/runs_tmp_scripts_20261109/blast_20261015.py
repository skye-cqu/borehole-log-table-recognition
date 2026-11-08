# -*- coding: utf-8 -*-
"""B目录还原 xlsx 的列数 -> 判断 finalize_tables 的硬编码列号(row[7]/NUM=(2,3,4,6))对哪些图会崩。"""
from pathlib import Path
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
B = R/"runs"/"table_reconstruct_重出_20261005_项④行线补全"
NUM = (2,3,4,6)
print("图    列数   max_idx  row[7]可取?  NUM 全部可取?")
bad7 = []; badnum = []
for k in range(1015, 1045):
    p = B/f"钻孔柱状图{k}_还原.xlsx"
    if not p.exists(): print("  %d 缺" % k); continue
    ws = load_workbook(p).active
    n = ws.max_column
    ok7 = n >= 8
    oknum = n >= 7
    if not ok7: bad7.append(k)
    if not oknum: badnum.append(k)
    if not ok7 or not oknum:
        print("  %-5d %-5d %-8d %-13s %s" % (k, n, n-1, ok7, oknum))
print()
print("row[7] 会 IndexError 的图 (%d 张): %s" % (len(bad7), bad7))
print("NUM=(2,3,4,6) 会 IndexError 的图 (%d 张): %s" % (len(badnum), badnum))
