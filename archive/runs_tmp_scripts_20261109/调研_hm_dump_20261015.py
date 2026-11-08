# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活\runs\table_reconstruct")
for stem in ["钻孔柱状图1032", "钻孔柱状图1042", "钻孔柱状图1033"]:
    hm = json.load(open(R / f"{stem}_表头映射.json", encoding="utf-8"))
    print("#####", stem, "keys:", list(hm.keys()))
    for k, v in hm.items():
        if k in ("sep_pts",):
            print(f"  {k}: {len(v) if hasattr(v,'__len__') else v} 项")
            continue
        print(f"  {k}: {json.dumps(v, ensure_ascii=False)[:600]}")
    print()
