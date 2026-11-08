# -*- coding: utf-8 -*-
import json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
TR = R/"runs"/"table_reconstruct"
hm = json.load(open(TR/"钻孔柱状图1042_表头映射.json", encoding="utf-8"))
print("##### 1042 表头映射")
print("  sep_x_band:", [round(v,1) for v in hm["sep_x_band"]])
print("  columns(全):")
for c in hm["columns"]:
    print("     %-14s x=%s" % (c.get("name"), [round(v,1) for v in c.get("x_in_band",[])]))
print("  drop_columns:")
for c in hm["drop_columns"]:
    print("     %s" % json.dumps({k:v for k,v in c.items() if k in ("name","x_in_band","reason")}, ensure_ascii=False))
print("  keep:", [(c["name"], round(c["x_in_band"][0]), round(c["x_in_band"][1])) for c in hm["keep"]])
print()
print("##### 1042 列结构定稿 真厚/柱状 细节")
d = json.load(open(TR/"钻孔柱状图1042_列结构定稿.json", encoding="utf-8"))
for c in d["columns"]:
    if c.get("name") in ("真厚","柱状","倾角","岩性描述"):
        print("  %-8s x_mid=%-7s y=%s n_seg=%d src=%s" % (
            c.get("name"), c.get("x_at_mid"), c.get("y"), len(c.get("segment_ids",[])), c.get("src")))
print()
print("##### 参考表 1042 列序(确认真厚位置)")
from openpyxl import load_workbook
wr = load_workbook(R/"runs"/"参考表_1015-1044_20261011"/"1015-1044"/"钻孔柱状图1042_llm_corrected.xlsx").active
print("  ", [wr.cell(row=1,column=c).value for c in range(1, 14)])
