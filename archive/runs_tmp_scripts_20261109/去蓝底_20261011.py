# -*- coding: utf-8 -*-
"""去 Agnes 描述校正蓝底标记(用户裁决 2026-10-11:不要蓝底)。
只清 D9E1F2 底色,文字/其他格式/红字不动;溯源在校正账(描述列 1293 条)。
教训吸取:必须 rich_text=True 载入,否则 rich 红字保存时丢失。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from openpyxl import load_workbook
from openpyxl.styles import PatternFill
from src.core import paths

NOFILL = PatternFill(fill_type=None)
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--only", type=int, default=None)
args = ap.parse_args()
n_ok = 0
for k in range(1015, 1045):
    if k in (1019, 1032) or (args.only is not None and k != args.only):
        continue
    p = paths.FINALIZE_FULL_DIR / f"钻孔柱状图{k}_整合.xlsx"
    wb = load_workbook(p, rich_text=True)
    ws = wb.active
    n = 0
    for row in ws.iter_rows(min_row=2):
        for c in row:
            rgb = getattr(getattr(c.fill, "start_color", None), "rgb", None)
            if isinstance(rgb, str) and rgb.endswith("D9E1F2"):
                c.fill = NOFILL
                n += 1
    if n:
        wb.save(p)
    n_ok += n
print("清蓝底格:", n_ok)
