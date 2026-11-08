# -*- coding: utf-8 -*-
"""1032 深度截断的正确检验:去小数点后做"数字后缀"匹配。
若原读数是链值的数字后缀 => 前导位被扫描左缘切掉(数据物理缺失),而非 OCR 误读。"""
import re
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")

def txt(v):
    if v is None: return ""
    if isinstance(v,str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)

ws = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)["1032"]
def num(s):
    t = str(s).strip().replace("D","0").replace("O","0").replace(" ","")
    m = re.fullmatch(r"-?\d+(?:\.\d+)?", t)
    return float(m.group()) if m else None
def digits(s):
    t = str(s).strip().replace("D","0").replace("O","0").replace(" ","")
    m = re.fullmatch(r"-?\d+(?:\.\d+)?", t)
    return m.group().replace(".","").lstrip("-") if m else None

cur = num(txt(ws.cell(row=2,column=1).value))
suf = 0; tot = 0; bad = []; lost = []
for r in range(3, ws.max_row+1):
    t = num(txt(ws.cell(row=r,column=2).value))
    if t is None or cur is None: continue
    want = round(cur + t, 2)
    d_raw = digits(txt(ws.cell(row=r,column=1).value))
    d_want = f"{want:.2f}".replace(".","")
    tot += 1
    if d_raw and d_want.endswith(d_raw) and len(d_raw) >= 2:
        suf += 1; lost.append(len(d_want)-len(d_raw))
    else:
        bad.append((r, txt(ws.cell(row=r,column=1).value), f"{want:.2f}", d_raw, d_want))
    cur = want
print(f"可比行={tot}  原读数是链值数字后缀={suf} ({suf/max(1,tot):.0%})")
from collections import Counter
print("  丢失位数分布:", dict(sorted(Counter(lost).items())))
print(f"  不吻合 {len(bad)} 条,前 18:")
for b in bad[:18]: print("   行%-4s 原读=%-8s 链值=%-9s 原数字=%-6s 链数字=%s" % b)
