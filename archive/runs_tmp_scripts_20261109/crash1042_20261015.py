# -*- coding: utf-8 -*-
"""① finalize 的保存路径(是否会覆盖既有整合表);② 1042 是否也崩。"""
import re, sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
t = (R/"src"/"table"/"finalize_tables.py").read_text(encoding="utf-8")
print("##### 1) finalize 的保存/输出路径")
for m in re.finditer(r".*(wb\.save|FINALIZE_FULL_DIR|OUT_|\.save\(|_整合\.xlsx|校正账).*", t):
    ln = t[:m.start()].count("\n")+1
    s = m.group(0).strip()
    if s: print("  L%-5d %s" % (ln, s[:130]))
print()
print("##### 2) 1042 走 unstuck_chain 是否崩")
from src.table.finalize_tables import unstuck_chain
from openpyxl import load_workbook
for k in ["1042", "1015"]:
    p = R/"runs"/"table_reconstruct_重出_20261005_项④行线补全"/f"钻孔柱状图{k}_还原.xlsx"
    ws = load_workbook(p).active
    data = list(ws.iter_rows(values_only=True))
    rows_b = [0.0]*(len(data)-1)
    try:
        d2, y2, ops, led = unstuck_chain(data, rows_b)
        print("  %s: OK (列数=%d) 操作=%d" % (k, ws.max_column, len(ops)))
    except Exception as e:
        print("  %s: 崩 -> %s: %s  (列数=%d)" % (k, type(e).__name__, str(e)[:80], ws.max_column))
