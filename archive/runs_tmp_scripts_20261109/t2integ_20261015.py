# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")

p = R/"runs/table_整合_全量_20261016/钻孔柱状图1042_整合.xlsx"
ws = load_workbook(p).active
print("== 1042 整合表 dims=%s ==" % ws.dimensions)
hdr = [ws.cell(row=1,column=c).value for c in range(1, ws.max_column+1)]
print("表头:", hdr)
print()
for r in range(2, 14):
    print("  r%-3d %s" % (r, [ws.cell(row=r,column=c).value for c in range(1, ws.max_column+1)]))

print()
print("== 参考表(真值) 对照 ==")
ref = R/"runs/参考表_1015-1044_20261011/1015-1044/钻孔柱状图1042_llm_corrected.xlsx"
w2 = load_workbook(ref).active
print("参考表头:", [w2.cell(row=1,column=c).value for c in range(1,14)])
for r in range(2, 10):
    print("  r%-3d %s" % (r, [w2.cell(row=r,column=c).value for c in range(5,14)]))

print()
v = json.loads((R/"runs/tmp/t1_违规明细_20261015.json").read_text(encoding="utf-8"))
print("== t1 违规明细 顶层类型:", type(v).__name__)
if isinstance(v, dict): print("   keys:", list(v.keys())[:10])
rows = v if isinstance(v, list) else v.get("rows") or v.get("明细") or []
print("   条目数:", len(rows))
if rows: print("   样本:", json.dumps(rows[0], ensure_ascii=False)[:300])
c1042 = [x for x in rows if "1042" in json.dumps(x, ensure_ascii=False)]
print("   1042 条目:", len(c1042))
for x in c1042[:8]:
    print("     ", json.dumps(x, ensure_ascii=False)[:220])
