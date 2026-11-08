# -*- coding: utf-8 -*-
"""层号/倾角列合并单元格落地(用户 2026-10-11 质询"合并单元格呢"):
原图行界在该列区间无薄横线=原图同一格(合并区),值随段占整段高度。
证据:runs/tmp/两列行线缺失_20261011.json(逐界像素判定)+ runs/tmp/眼验_1015_*.png。
规则:无线连通段含值行才合并(空段不动);段内多值行=漏检嫌疑,值取首行+记账。
1019(旧版映射)/1032(整图列错位)跳过。"""
import csv
import json
import sys
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from openpyxl import load_workbook
from src.core import paths
from src.table.finalize_tables import flags_wireless, value_merge_spans

ap = argparse.ArgumentParser()
ap.add_argument("--only", type=int, default=None)
_args = ap.parse_args()
flags_by_stem = json.load(open(ROOT / "runs/tmp/两列行线缺失_20261011.json", encoding="utf-8"))
if _args.only is not None:
    flags_by_stem = {f"钻孔柱状图{_args.only}": flags_by_stem[f"钻孔柱状图{_args.only}"]}
COL = {"层号": 2, "倾角": 6}
tot = {"合并区": 0, "多值段": 0}
ledger = []
for stem, res in flags_by_stem.items():
    k = int(stem.replace("钻孔柱状图", ""))
    p = paths.FINALIZE_FULL_DIR / f"{stem}_整合.xlsx"
    wb = load_workbook(p, rich_text=True)  # 不加则 rich 红字保存时丢失
    ws = wb.active
    n_data = ws.max_row - 1
    for tag, col in COL.items():
        # json 语义: True=有线,None=存疑 → 转 value_merge_spans 的无线语义
        flags = flags_wireless(res[tag]["flags"][: n_data - 1])
        val_rows = set()
        for i in range(n_data):
            v = ws.cell(row=i + 2, column=col).value
            if v is not None and str(v).strip():
                val_rows.add(i)
        for a, b in value_merge_spans(flags, val_rows):
            inside = [v for v in val_rows if a <= v <= b]
            if len(inside) > 1:
                tot["多值段"] += 1
                ledger.append({"图": stem, "列": tag, "段": f"{a+2}-{b+2}",
                               "值行数": len(inside), "依据": "段内多值,疑线漏检,值取首行"})
            ws.merge_cells(start_row=a + 2, start_column=col, end_row=b + 2, end_column=col)
            ws.cell(row=a + 2, column=col).alignment = ws.cell(row=a + 2, column=col).alignment.copy(vertical="center")
            tot["合并区"] += 1
    wb.save(p)
print("合并区合计:", tot)
out = ROOT / "runs/table_整合_全量_20261011/两列合并账_20261011.csv"
with open(out, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, fieldnames=["图", "列", "段", "值行数", "依据"])
    w.writeheader()
    w.writerows(ledger)
print("多值段账:", out, len(ledger), "条")
