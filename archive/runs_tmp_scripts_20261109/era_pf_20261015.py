# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.table import era_chars

print("##### 1) 9 图 preflight 拒裁原因")
for k in ["1017","1019","1020","1023","1025","1028","1030","1032","1042"]:
    stem = f"钻孔柱状图{k}"
    hm_p = R/"runs"/"table_reconstruct"/f"{stem}_表头映射.json"
    hm = json.load(open(hm_p, encoding="utf-8"))
    has = "sep_pts" in hm
    try:
        rep = era_chars.preflight(stem)
        print("  %s sep_pts=%-5s ok=%-5s PF1=%s PF2=%s 原因=%s" % (
            k, has, rep.get("ok"), rep.get("PF1_列界覆盖率"), rep.get("PF2_时代界行接触率"),
            rep.get("原因", "")))
    except Exception as e:
        print("  %s sep_pts=%-5s preflight 异常: %s: %s" % (k, has, type(e).__name__, str(e)[:90]))

print()
print("##### 2) era_chars 产物目录命名(取一例)")
d = R/"runs"/"era_chars_20261010"/"钻孔柱状图1033"
print("  ", [p.name for p in sorted(d.glob("*"))] if d.exists() else "无")

print()
print("##### 3) 1042 倾角列可疑小角值")
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
def txt(v):
    if v is None: return ""
    if isinstance(v,str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)
ws = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)["1042"]
hdr = [txt(ws.cell(row=1,column=c).value) for c in range(1, ws.max_column+1)]
ci = hdr.index("倾角")+1
for r in range(2, ws.max_row+1):
    v = txt(ws.cell(row=r, column=ci).value).strip()
    if v and (v.rstrip("°").replace(".","").isdigit() and float(v.rstrip("°")) < 15):
        print("   行%-4d 倾角=%-6s 深度=%-9s 层厚=%-8s" % (r, v,
            txt(ws.cell(row=r,column=hdr.index("深度")+1).value),
            txt(ws.cell(row=r,column=hdr.index("层厚")+1).value)))
