# -*- coding: utf-8 -*-
"""T0 关键回归:新目录产物 vs 20261011 既有产物 逐格对比(对照图必须完全一致)。"""
import json
from pathlib import Path
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
NEW = R/"runs"/"table_整合_全量_20261016"
OLD = R/"runs"/"table_整合_全量_20261011"

def cells(p):
    ws = load_workbook(p).active
    return [[ws.cell(row=r, column=c).value for c in range(1, ws.max_column+1)]
            for r in range(1, ws.max_row+1)]

for k in ["1015", "1023"]:
    n = NEW/f"钻孔柱状图{k}_整合.xlsx"; o = OLD/f"钻孔柱状图{k}_整合.xlsx"
    if not (n.exists() and o.exists()):
        print("  %s 缺产物 (新=%s 旧=%s)" % (k, n.exists(), o.exists())); continue
    cn, co = cells(n), cells(o)
    print("  %-6s 新 %dx%d  旧 %dx%d" % (k, len(cn), len(cn[0]), len(co), len(co[0])))
    if len(cn) != len(co) or len(cn[0]) != len(co[0]):
        print("        形状不同 -> 需人工核")
        continue
    diff = [(r+1, c+1, co[r][c], cn[r][c])
            for r in range(len(co)) for c in range(len(co[0])) if co[r][c] != cn[r][c]]
    print("        差异格数 = %d" % len(diff))
    for d in diff[:12]:
        print("          r%d c%d: 旧=%r 新=%r" % d)
print()
print("##### 验收.json 门禁数对比")
for k in ["1015","1023","1032","1042"]:
    for tag, D in (("旧", OLD), ("新", NEW)):
        p = D/f"钻孔柱状图{k}_验收.json"
        if p.exists():
            d = json.load(open(p, encoding="utf-8"))
            print("  %-6s %s 门禁=%-4d 账=%-4d 名带=%d" % (
                k, tag, len(d.get("门禁问题", [])), d.get("账条数", 0), len(d.get("名带", []))))
        else:
            print("  %-6s %s 无" % (k, tag))
