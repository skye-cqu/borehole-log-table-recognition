# -*- coding: utf-8 -*-
import json
from pathlib import Path
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
wb = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)
def txt(v):
    if v is None: return ""
    from openpyxl.cell.rich_text import CellRichText, TextBlock
    if isinstance(v, str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b, TextBlock) else str(b) for b in v)
    return str(v)
for name, n in [("1015", 8), ("1023", 10), ("1026", 8), ("1032", 8)]:
    ws = wb[name]
    print("#####", name)
    for r in range(1, min(ws.max_row, n)+1):
        print(f" r{r:>3}| " + " | ".join(txt(ws.cell(row=r, column=c).value)[:18].ljust(18) for c in range(1, ws.max_column+1)))
    print()
# 1023 表头映射
hm = json.load(open(R/"runs"/"table_reconstruct"/"钻孔柱状图1023_表头映射.json", encoding="utf-8"))
print("1023 keep:", [(c["name"], round(c["x_in_band"][0],1), round(c["x_in_band"][1],1)) for c in hm["keep"]])
print("1023 sep_x_band:", hm["sep_x_band"])
print("1023 warnings:", hm["warnings"], "ok:", hm["ok"])
