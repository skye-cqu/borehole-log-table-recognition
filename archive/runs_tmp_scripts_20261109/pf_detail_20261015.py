# -*- coding: utf-8 -*-
import sys, json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.table import era_chars as E

print("阈值: PF1_MIN_COV=%s PF2_MIN_CONTACT=%s PF3_MIN_GAP=%s" % (
    E.PF1_MIN_COV, E.PF2_MIN_CONTACT, E.PF3_MIN_GAP))
print()
print("图    PF1     PF2     n_era_full n_era_partial PF3违规数 ok    era列有内容?")
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
def txt(v):
    if v is None: return ""
    if isinstance(v,str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)
wb = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)
for k in ["1017","1019","1020","1023","1025","1028","1030","1032","1042"]:
    stem = f"钻孔柱状图{k}"
    hm, rd = E._load_inputs(stem)
    x_mid = sum(rd["table_x"])/2.0
    rd["rows"] = [r for r in rd["rows"] if E.row_y(r, x_mid) >= hm["band"][1]]
    if "sep_pts" not in hm:
        print("%-5s sep_pts 缺失 -> 结构性拒裁" % k); continue
    rep = E.preflight_checks(hm, rd)
    ws = wb[k]
    nonempty = sum(1 for r in range(2, ws.max_row+1) if txt(ws.cell(row=r,column=1).value).strip())
    print("%-5s %-7s %-7s %-10s %-14s %-9s %-5s %d/%d" % (
        k, rep["PF1_列界覆盖率"], rep["PF2_时代界行接触率"],
        rd.get("n_era_full"), rd.get("n_era_partial"),
        len(rep["PF3_行序违规"]), rep["ok"], nonempty, ws.max_row-1))
