# -*- coding: utf-8 -*-
"""未提交的 col_segments.py 改动是否是 T3/T4 的上游依赖?
检查:(a) ext_conn 是否已出现在产物 json;(b) line_parts 是否被 header_assign 用于 sep_pts。"""
import json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
TR = R/"runs"/"table_reconstruct"
print("##### (a) ext_conn 在产物中的出现情况")
hits = 0
for p in sorted(TR.glob("*_分割线.json")):
    d = json.load(open(p, encoding="utf-8"))
    for ln in d.get("lines", []):
        if ln.get("ext_conn"):
            hits += 1
            print("  %s kind=%s side=%s ext_conn=%d" % (p.name, ln.get("kind"), ln.get("side"), len(ln["ext_conn"])))
print("  含 ext_conn 的线数 =", hits)
print()
print("##### (b) 未提交改动的关键新符号是否被引用")
import subprocess
out = subprocess.run(["git","diff","--","src/table/col_segments.py"], capture_output=True, text=True, cwd=str(R), encoding="utf-8").stdout
for sym in ["ext_conn", "def _bridges", "axis=1", "horizontal", "line_jumps", "drop_points"]:
    print("  %-16s 在 diff 中: %s" % (sym, sym in out))
