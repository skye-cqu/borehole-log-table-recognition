# -*- coding: utf-8 -*-
from pathlib import Path
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
B = R/"runs"/"table_reconstruct_重出_20261005_项④行线补全"
for k in ["1032", "1042", "1019", "1023", "1015"]:
    p = B/f"钻孔柱状图{k}_还原.xlsx"
    ws = load_workbook(p).active
    hdr = [ws.cell(row=1,column=c).value for c in range(1, ws.max_column+1)]
    print("B还原 %s: %d 列  hdr=%s" % (k, ws.max_column, hdr))
print()
print("对比:整合目录与 v7")
from openpyxl import load_workbook as L
for k in ["1032","1042"]:
    for tag, p in [("整合", R/"runs"/"table_整合_全量_20261011"/f"钻孔柱状图{k}_整合.xlsx"),
                   ("v7", R/"runs"/"全量整合_合订表_v7.xlsx")]:
        if tag == "v7":
            ws = L(p)[k]
        else:
            ws = L(p).active
        hdr = [ws.cell(row=1,column=c).value for c in range(1, ws.max_column+1)]
        print("  %s %s: %d 列 hdr=%s" % (tag, k, ws.max_column, hdr))
