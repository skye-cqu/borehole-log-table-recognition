# -*- coding: utf-8 -*-
"""v7 合订表客观审计:列结构/表头/时代列合并/数值自洽不变量。只读。"""
import json, re
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock

P = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活\runs\全量整合_合订表_v7.xlsx")
CANON = ["地质时代", "煤层标志层号", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述"]
wb = load_workbook(P, rich_text=True)

def txt(v):
    if v is None: return ""
    if isinstance(v, str): return v
    if isinstance(v, CellRichText):
        return "".join(b.text if isinstance(b, TextBlock) else str(b) for b in v)
    return str(v)

def fnum(s):
    s = str(s).strip()
    m = re.fullmatch(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None

print(f"{'图':>5} {'列数':>4} {'行数':>4} {'表头':<8} {'A列合并':>6} {'A列非空':>6} {'A列唯一':>6} | 不变量(深度逆序/层厚≠Δ深度/真厚>层厚/采长>层厚/倾角>90)")
rows_out = []
for name in wb.sheetnames:
    ws = wb[name]
    hdr = [txt(ws.cell(row=1, column=c).value) for c in range(1, ws.max_column + 1)]
    okh = "标准" if hdr == [c for c in CANON if c in hdr] else "异常"
    amerges = [str(m) for m in ws.merged_cells.ranges if m.min_col == 1]
    nrows = ws.max_row - 1
    # 列索引
    idx = {h: i + 1 for i, h in enumerate(hdr)}
    def col(h, r):
        c = idx.get(h)
        return txt(ws.cell(row=r, column=c).value) if c else ""
    era_vals = [col("地质时代", r) for r in range(2, ws.max_row + 1)]
    era_nonempty = [v for v in era_vals if v.strip()]
    era_uniq = len(set(era_nonempty))
    depths = [fnum(col("深度", r)) for r in range(2, ws.max_row + 1)]
    thicks = [fnum(col("层厚", r)) for r in range(2, ws.max_row + 1)]
    trues  = [fnum(col("真厚", r)) for r in range(2, ws.max_row + 1)]
    caich  = [fnum(col("采长", r)) for r in range(2, ws.max_row + 1)]
    dips   = [col("倾角", r) for r in range(2, ws.max_row + 1)]
    # 1 深度逆序
    rev = sum(1 for i in range(len(depths)-1) if depths[i] is not None and depths[i+1] is not None and depths[i+1] < depths[i] - 1e-9)
    # 2 层厚 = Δ深度 (相邻终深差);深度是终深(累计)
    dt = 0; tot = 0
    for i in range(len(depths)-1):
        if depths[i] is None or thicks[i] is None or depths[i+1] is None: continue
        tot += 1
        if abs((depths[i+1] - depths[i]) - thicks[i]) > 0.011: dt += 1
    # 3 真厚 > 层厚
    th = sum(1 for i in range(len(thicks)) if thicks[i] is not None and trues[i] is not None and trues[i] > thicks[i] + 0.011)
    # 4 采长 > 层厚
    cc = sum(1 for i in range(len(thicks)) if thicks[i] is not None and caich[i] is not None and caich[i] > thicks[i] + 0.011)
    # 5 倾角 > 90
    dd = 0
    for d in dips:
        m = re.fullmatch(r"(\d+(?:\.\d+)?)°", d.strip())
        if m and float(m.group(1)) > 90: dd += 1
    print(f"{name:>5} {ws.max_column:>4} {nrows:>4} {okh:<8} {len(amerges):>6} {len(era_nonempty):>6} {era_uniq:>6} | {rev}/{dt}/{th}/{cc}/{dd}  (Δ深度可比 {tot})")
    rows_out.append({"图": name, "列数": ws.max_column, "行数": nrows, "表头": hdr, "表头标准": okh == "标准",
                     "A列合并数": len(amerges), "A列非空": len(era_nonempty), "A列唯一值": era_uniq,
                     "深度逆序": rev, "层厚≠Δ深度": dt, "Δ深度可比": tot,
                     "真厚>层厚": th, "采长>层厚": cc, "倾角>90": dd})
json.dump(rows_out, open(Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")/"runs"/"tmp"/"审计_v7_20261015.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
