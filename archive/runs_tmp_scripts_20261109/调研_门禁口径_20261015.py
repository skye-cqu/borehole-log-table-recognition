# -*- coding: utf-8 -*-
"""① 1042/1032 表头带逐列量字墨块 x 区间(客观);② 用各表"真实表头名"重跑门禁规则。"""
import json, re
import cv2
import numpy as np
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.cell.rich_text import CellRichText, TextBlock
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")

def glyph_cols(gray, y0, y1, minw=6):
    """表头带内的字墨列区间(排除竖线)。"""
    band = gray[int(y0):int(y1)]
    colink = (band < 140).mean(axis=0)
    isglyph = colink > 0.03
    runs = []
    s = None
    for i, v in enumerate(isglyph):
        if v and s is None: s = i
        elif not v and s is not None:
            if i - s >= minw: runs.append((s, i))
            s = None
    if s is not None and len(isglyph) - s >= minw: runs.append((s, len(isglyph)))
    return runs

for stem in ["钻孔柱状图1042", "钻孔柱状图1032", "钻孔柱状图1023"]:
    hm = json.load(open(R/"runs"/"table_reconstruct"/f"{stem}_表头映射.json", encoding="utf-8"))
    gray = cv2.imread(str(R/"data"/"raw_images"/f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    b0, b1 = hm["band"]
    runs = glyph_cols(gray, b0+6, b1-6)
    print(f"##### {stem} band={hm['band']}")
    print("  字墨块 x 区间:", [(a,b) for a,b in runs])
    print("  映射 sep_x_band:", [round(v,1) for v in hm["sep_x_band"]])
    print()

# ---- 用真实表头名重跑门禁 ----
CANON = ["地质时代","煤层标志层号","深度","层厚","采长","倾角","真厚","岩性描述"]
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
LAYER = re.compile(r"^[0-9]+$|^[一二三四五六七八九十]+$|^[一二三四五六七八九十]\s*[上下]$|^十[一二三四五]$|^[0-9]+[上下]$")
DIP = re.compile(r"^\d+(\.\d+)?°$")
def _era(v):
    s = re.sub(r"\s+","",str(v)); return bool(s) and not re.search(r"[A-Za-z]",s) and bool(re.search(r"[\u4e00-\u9fff]",s))
def _desc(v):
    s = str(v).strip(); return not s or not re.match(r"^[。.,;:、]", s)
def _num(v): return bool(NUM_RE.fullmatch(str(v).strip()))
def _layer(v): return bool(LAYER.fullmatch(re.sub(r"\s","",str(v))))
def _dip(v): return bool(DIP.fullmatch(str(v).strip()))
RULES = {"地质时代":_era, "煤层标志层号":_layer, "煤层/标志层号":_layer, "深度":_num, "层厚":_num,
         "采长":_num, "倾角":_dip, "真厚":_num, "岩性描述":_desc}

wb = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx", rich_text=True)
def txt(v):
    if v is None: return ""
    if isinstance(v,str): return v
    if isinstance(v, CellRichText): return "".join(b.text if isinstance(b,TextBlock) else str(b) for b in v)
    return str(v)

print("===== 门禁:硬编码列名 vs 实际表头名 =====")
for name in wb.sheetnames:
    ws = wb[name]
    hdr = [txt(ws.cell(row=1,column=c).value) for c in range(1, ws.max_column+1)]
    hard = 0; real = 0; badreal = []
    for r in range(2, ws.max_row+1):
        for ci, h in enumerate(hdr, start=1):
            cell = ws.cell(row=r, column=ci)
            if cell.__class__.__name__ == "MergedCell": continue
            s = txt(cell.value).strip()
            if not s: continue
            hc = ["地质时代","煤层/标志层号","深度","层厚","采长","倾角","真厚","岩性描述"][ci-1] if ci <= 8 else None
            if hc and hc in RULES and not RULES[hc](s): hard += 1
            if h in RULES and not RULES[h](s):
                real += 1
                if len(badreal) < 6: badreal.append((r, h, s[:30]))
    flag = "  <== 差异大" if abs(hard-real) > 5 else ""
    print(f"  {name}: 硬编码口径违规={hard:>4}  真实表头口径违规={real:>4}{flag}")
    if badreal: print(f"        样例: {badreal}")
