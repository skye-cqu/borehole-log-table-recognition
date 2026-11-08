# -*- coding: utf-8 -*-
import sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from openpyxl import load_workbook
from src.table.finalize_tables import column_roles, num_cols, unstuck_chain, drop_header_rows
from src.core import paths

print("新目录已登记:", paths.FINALIZE_FULL_DIR_20261016.name, "|", paths.ERA_CHAR_DIR_20261016.name)
print()
print("##### 列角色解析(B目录表头)")
for k in ["1032","1042","1019","1023","1015","1037"]:
    p = paths.REEMIT_DIR_20261005B / f"钻孔柱状图{k}_还原.xlsx"
    ws = load_workbook(p).active
    hdr = [ws.cell(row=1,column=c).value for c in range(1, ws.max_column+1)]
    roles = column_roles(hdr)
    print("  %-5s %d列 roles=%s NUM=%s" % (k, ws.max_column, roles, num_cols(roles)))
print()
print("##### unstuck_chain 不再崩")
for k in ["1032","1042","1015","1037"]:
    p = paths.REEMIT_DIR_20261005B / f"钻孔柱状图{k}_还原.xlsx"
    ws = load_workbook(p).active
    data = list(ws.iter_rows(values_only=True))
    roles = column_roles(data[0])
    try:
        d2, y2, ops, led = unstuck_chain(data, [0.0]*(len(data)-1), roles)
        print("  %-5s OK 列=%d 操作=%d 账=%d" % (k, ws.max_column, len(ops), len(led)))
    except Exception as e:
        print("  %-5s 崩 %s: %s" % (k, type(e).__name__, str(e)[:70]))
