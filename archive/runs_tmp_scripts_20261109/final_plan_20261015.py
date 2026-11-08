# -*- coding: utf-8 -*-
"""① 1032/1042 行带数 vs v7 行数(对齐偏移);② 门禁账本 PROVEN-DEAD;③ 模板脚本存在性。"""
import json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
TR = R/"runs"/"table_reconstruct"
from openpyxl import load_workbook
wb = load_workbook(R/"runs"/"全量整合_合订表_v7.xlsx")
print("##### 1) 行带数 vs v7 行数")
for k in ["1015","1019","1023","1032","1042"]:
    rd = json.load(open(TR/f"钻孔柱状图{k}_行判定.json", encoding="utf-8"))
    hm = json.load(open(TR/f"钻孔柱状图{k}_表头映射.json", encoding="utf-8"))
    data = [r for r in rd["rows"] if min(p[1] for p in r["poly"]) >= hm["band"][1]]
    ws = wb[k]
    print(f"  {k}: 行判定数据带={len(data)}  v7 行={ws.max_row-1}  差={len(data)-(ws.max_row-1)}")

print()
print("##### 2) 门禁账本 PROVEN-DEAD")
p = R/"memory-bank"/"gate_ledger.md"
if p.exists():
    t = p.read_text(encoding="utf-8", errors="replace")
    print("  长度:", len(t))
    for ln in t.splitlines():
        if "PROVEN-DEAD" in ln or "PROVEN_DEAD" in ln or "已证死" in ln:
            print("   ", ln.strip()[:200])
else:
    print("  不存在:", p)

print()
print("##### 3) 关键脚本存在性")
for f in ["runs/tmp/修1033列界_20261012.py", "src/tools/audit_deliverable.py",
          "src/tools/audit_invariants.py", "src/table/header_assign.py",
          "src/table/delivery_gate.py", "src/table/era_chars.py",
          "runs/tmp/合成总表_20261011.py", "src/table/finalize_tables.py"]:
    q = R/f
    print(f"  {'OK ' if q.exists() else '缺 '} {f}  {q.stat().st_size if q.exists() else 0}B")
