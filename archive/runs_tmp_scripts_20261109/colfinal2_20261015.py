# -*- coding: utf-8 -*-
import json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
TR = R/"runs"/"table_reconstruct"
for k in ["1032", "1019", "1023"]:
    p = TR/f"钻孔柱状图{k}_列结构定稿.json"
    if not p.exists(): print(f"{k}: 无 列结构定稿"); continue
    d = json.load(open(p, encoding="utf-8"))
    cols = d.get("columns", [])
    print("##### %s  columns=%d" % (k, len(cols)))
    print("   missing=%r" % d.get("missing"))
    for c in cols:
        print("   idx=%s %-12s x_mid=%s y=%s src=%s" % (
            c.get("index"), c.get("name"), c.get("x_at_mid"), c.get("y"), str(c.get("src"))[:40]))
    print("   frames=%s" % [(f.get("side"), f.get("x_at_mid")) for f in d.get("frames", [])])
    print("   content=%s" % [(c.get("src"), c.get("x_at_mid")) for c in d.get("content", [])])
    print()
