# -*- coding: utf-8 -*-
import json, collections
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
rep = json.load(open(R/"runs"/"table_整合_全量_20261011"/"交付门禁_报告.json", encoding="utf-8"))
for cat, items in rep.items():
    print("=====", cat, len(items))
    by = collections.Counter(i["图"] for i in items)
    print("  按图:", dict(by))
    for i in items[:40]:
        print("   ", i["图"], "行", i["行"], i["列"], repr(i["值"]))
