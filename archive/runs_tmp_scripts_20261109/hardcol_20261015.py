# -*- coding: utf-8 -*-
"""硬编码列号缺陷类:扫 src/table 与 src/tools 里按整数下标取列的位置。"""
import re
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
pats = [
    (re.compile(r"row\[(\d)\]"), "row[i]"),
    (re.compile(r"data\[[^\]]+\]\[(\d)\]"), "data[..][i]"),
    (re.compile(r"cell\(row=[^,]+,column=(\d+)\)"), "cell(column=i)"),
    (re.compile(r"NUM\s*=\s*\(([\d,\s]+)\)"), "NUM=(...)"),
    (re.compile(r"vals\[(\d)\]"), "vals[i]"),
    (re.compile(r"^\s*(\d):\s*_", re.M), "RULES{i:...}"),
]
hits = {}
for p in sorted(list((R/"src"/"table").glob("*.py")) + list((R/"src"/"tools").glob("*.py"))):
    txt = p.read_text(encoding="utf-8", errors="replace")
    for rgx, tag in pats:
        for m in rgx.finditer(txt):
            ln = txt[:m.start()].count("\n") + 1
            hits.setdefault(p.name, []).append((ln, tag, m.group(0).strip()))
for name in sorted(hits, key=lambda n: -len(hits[n])):
    print("%-26s %d 处" % (name, len(hits[name])))
    for ln, tag, s in hits[name][:6]:
        print("      L%-5d %-14s %s" % (ln, tag, s[:50]))
