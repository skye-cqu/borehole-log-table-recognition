# -*- coding: utf-8 -*-
"""1042:agnes 已读的 真厚 与参考表真值逐行比对。"""
import json, sys
from pathlib import Path
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")

ag = json.loads((R/"runs/table_reconstruct/钻孔柱状图1042_agnes读数.json").read_text(encoding="utf-8"))
cols = ag["columns"]
print("agnes 列:", cols)
i_tt = cols.index("真厚")
print("真厚 索引:", i_tt)
lay = ag["layers"]
print("层数:", len(lay))
tt = [ (l["readings"].get("真厚") or "").strip() for l in lay ]
print("真厚非空:", sum(1 for v in tt if v), "/", len(tt))
print("前 40 行 agnes 真厚:", tt[:40])

ref = R/"runs/参考表_1015-1044_20261011/1015-1044/钻孔柱状图1042_llm_corrected.xlsx"
ws = load_workbook(ref).active
rt = []
for r in range(2, ws.max_row+1):
    v = ws.cell(row=r, column=11).value
    rt.append("" if v is None else str(v).strip())
print()
print("参考表行数:", len(rt), " 真厚非空:", sum(1 for v in rt if v))
print("前 40 行 参考真厚:", rt[:40])
print()
n = min(len(tt), len(rt))
same = sum(1 for i in range(n) if tt[i] and rt[i] and abs(float(tt[i].replace("m","") or 0) - float(rt[i] or 0)) < 0.005)
print("逐行比较前 %d 行: 双方非空且相等 = %d" % (n, same))
for i in range(min(30, n)):
    mark = "OK " if (tt[i] and rt[i] and tt[i]==rt[i]) else "   "
    print("  %s行%-3d agnes=%-8s 参考=%s" % (mark, i+1, tt[i] or "-", rt[i] or "-"))
