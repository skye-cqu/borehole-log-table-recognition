# -*- coding: utf-8 -*-
"""B 列(煤层标志层号)rowspan 合并落地汇总:各图合并区数、乱码旗、值搬移账。"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from openpyxl import load_workbook

from src.core import paths

OUT = paths.RUNS_DIR / "table_整合_全量_20261011"
rows_out = []
tot_merge = tot_garble = 0
for f in sorted(p for p in OUT.glob("*_整合.xlsx") if not p.name.startswith("~$")):
    stem = f.name.replace("_整合.xlsx", "")
    wb = load_workbook(f)
    ws = wb.active
    merges = sorted((str(r) for r in ws.merged_cells.ranges if str(r).startswith("B")),
                    key=lambda s: int(s.split(":")[0][1:]))
    # 乱码旗
    vj = OUT / f"{stem}_验收.json"
    garbles = []
    if vj.exists():
        d = json.loads(vj.read_text(encoding="utf-8"))
        for fl in d.get("门禁问题", []):
            if fl.get("列") == "煤层标志层号":
                garbles.append(f"{fl.get('行')}:{fl.get('问题','').split(':')[-1]}")
    # 多格顶值核对:每合并区左上非空
    empty_tops = [m for m in merges
                  if ws.cell(row=int(m.split(":")[0][1:]), column=2).value in (None, "")]
    rows_out.append((stem, len(merges), len(garbles), ";".join(garbles[:4]),
                     "有!" if empty_tops else ""))
    tot_merge += len(merges)
    tot_garble += len(garbles)

w = csv.writer(open(paths.RUNS_DIR / "tmp" / "_B列合并汇总.csv", "w", newline="", encoding="utf-8-sig"))
w.writerow(["图", "B列合并区数", "乱码旗数", "乱码明细(前4)", "空顶值"])
w.writerows(rows_out)
print(f"合计: 合并区 {tot_merge} 个 / 乱码旗 {tot_garble} 个 / 图 {len(rows_out)} 张")
for r in rows_out:
    if r[1] or r[2]:
        print(f"  {r[0][-4:]}: 合并{r[1]:3d} 乱码{r[2]} {r[3]} {r[4]}")
