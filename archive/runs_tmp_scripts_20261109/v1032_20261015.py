# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
p = R/"runs"/"table_整合_全量_20261011"/"钻孔柱状图1032_验收.json"
print("1032 验收.json 存在:", p.exists())
if p.exists():
    d = json.load(open(p, encoding="utf-8"))
    print("  键:", sorted(d.keys()))
    print("  error:", d.get("error"))
    print("  名带数:", len(d.get("名带", [])), " 合并组:", len(d.get("合并组", [])))
    print("  门禁问题:", len(d.get("门禁问题", [])))
print()
# 各图验收 json 是否有 error
print("30 图验收 json 的 error 字段:")
for k in range(1015, 1045):
    q = R/"runs"/"table_整合_全量_20261011"/f"钻孔柱状图{k}_验收.json"
    if q.exists():
        d = json.load(open(q, encoding="utf-8"))
        e = d.get("error")
        if e: print("   %d ERROR: %s" % (k, e))
print("  (只列有 error 的)")
print()
# 是否 finalize 有 padding
import re
t = (R/"src"/"table"/"finalize_tables.py").read_text(encoding="utf-8")
for m in re.finditer(r".*(pad|padding|8\b.*列|len\(row\)|max_column).*", t):
    ln = t[:m.start()].count("\n")+1
    s = m.group(0).strip()
    if s and ("pad" in s or "len(row)" in s or "max_column" in s):
        print("  L%-5d %s" % (ln, s[:120]))
