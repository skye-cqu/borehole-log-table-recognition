# -*- coding: utf-8 -*-
import json
from pathlib import Path
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")

print("##### 1) 1032 在各目录的表头")
dirs = [
    ("B目录(重出20261005B)", R/"runs"/"table_reconstruct_重出_20261005_项④行线补全"),
    ("table_reconstruct",    R/"runs"/"table_reconstruct"),
    ("整合全量",              R/"runs"/"table_整合_全量_20261011"),
]
for tag, d in dirs:
    hit = False
    for pat in ["钻孔柱状图1032_还原.xlsx", "钻孔柱状图1032_整合.xlsx"]:
        p = d/pat
        if p.exists():
            ws = load_workbook(p).active
            hdr = [ws.cell(row=1,column=c).value for c in range(1, ws.max_column+1)]
            print(f"  {tag:<22} {pat}: rows={ws.max_row} cols={ws.max_column} hdr={hdr}")
            hit = True
    if not hit:
        print(f"  {tag:<22} 无 1032 表")

print()
print("##### 2) 1019 表头映射 sep 归属 vs 实测真墨")
TR = R/"runs"/"table_reconstruct"
hm = json.load(open(TR/"钻孔柱状图1019_表头映射.json", encoding="utf-8"))
print("  sep_x_band:", [round(v,1) for v in hm["sep_x_band"]])
print("  keep:", [(c["name"], round(c["x_in_band"][0]), round(c["x_in_band"][1])) for c in hm["keep"]])
print("  实测真墨峰:", [249,258,326,386,404,448,574,660,746,826,904,1108,2437,2983,3049,3058])
print("  有 sep_pts 键:", "sep_pts" in hm)
