# -*- coding: utf-8 -*-
import json
from pathlib import Path
from openpyxl import load_workbook
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
print("B还原 行数 vs 整合 行数 vs v7 行数")
wb7 = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx")
for k in ["1015","1019","1023","1032","1042"]:
    stem = f"钻孔柱状图{k}"
    b = R/"runs"/"table_reconstruct_重出_20261005_项④行线补全"/f"{stem}_还原.xlsx"
    i = R/"runs"/"table_整合_全量_20261011"/f"{stem}_整合.xlsx"
    nb = load_workbook(b).active.max_row-1 if b.exists() else None
    ni = load_workbook(i).active.max_row-1 if i.exists() else None
    n7 = wb7[k].max_row-1
    print("  %s  B还原=%-4s 整合=%-4s v7=%-4s  整合-B=%s" % (k, nb, ni, n7, (ni-nb) if (nb is not None and ni is not None) else "?"))
# 1032 校正账
import csv
p = R/"runs"/"table_整合_全量_20261011"/"钻孔柱状图1032_校正账.csv"
if p.exists():
    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    print("\n1032 校正账 条数=%d" % len(rows))
    from collections import Counter
    print("  动作分布:", Counter(r.get("动作") or r.get("列") or "?" for r in rows).most_common(12))
    for r in rows[:8]: print("   ", json.dumps(r, ensure_ascii=False)[:200])
