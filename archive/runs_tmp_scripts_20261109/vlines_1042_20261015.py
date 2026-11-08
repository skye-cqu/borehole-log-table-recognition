# -*- coding: utf-8 -*-
import json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
TR = R/"runs"/"table_reconstruct"
for nm in ["钻孔柱状图1042_全竖线判定.json", "钻孔柱状图1042_列结构定稿.json", "钻孔柱状图1042_分割线.json"]:
    p = TR/nm
    d = json.load(open(p, encoding="utf-8"))
    print("="*70); print(nm, "type:", type(d).__name__)
    if isinstance(d, dict):
        for k, v in d.items():
            s = json.dumps(v, ensure_ascii=False)
            print(f"  {k}: {s[:420]}")
    else:
        print(json.dumps(d, ensure_ascii=False)[:1500])
    print()
