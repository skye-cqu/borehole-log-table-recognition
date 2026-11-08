# -*- coding: utf-8 -*-
"""对比 runs/tmp/_t2before 与当前 runs/table_reconstruct 的表头映射,列出差异。"""
import json, sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
B = R/"runs/tmp/_t2before"; A = R/"runs/table_reconstruct"
n = 0; diff = []
for f in sorted(B.glob("*_表头映射.json")):
    stem = f.name[:-len("_表头映射.json")]
    a = A/f.name
    if not a.exists(): continue
    n += 1
    o = json.loads(f.read_text(encoding="utf-8")); w = json.loads(a.read_text(encoding="utf-8"))
    d = []
    for k in ("header_src", "sep_x_band", "n_sep", "ok"):
        if o.get(k) != w.get(k): d.append((k, o.get(k), w.get(k)))
    for k in ("keep", "columns", "drop_columns"):
        ko = [(c["name"], c["left_sep"], c["right_sep"]) for c in (o.get(k) or [])]
        kw = [(c["name"], c["left_sep"], c["right_sep"]) for c in (w.get(k) or [])]
        if ko != kw: d.append((k, ko, kw))
    if (o.get("warnings") or []) != (w.get("warnings") or []):
        d.append(("warnings", o.get("warnings"), w.get("warnings")))
    if d: diff.append((stem, d))
print("对比 = %d 张, 有差异 = %d 张" % (n, len(diff)))
for stem, d in diff:
    print("\n=== %s ===" % stem)
    for k, o, w in d:
        print("  %s:" % k)
        print("    旧 =", o)
        print("    新 =", w)
