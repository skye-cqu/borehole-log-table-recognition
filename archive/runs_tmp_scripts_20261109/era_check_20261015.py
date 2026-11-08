# -*- coding: utf-8 -*-
import json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
ERA = R/"runs"/"era_chars_20261010"
print("era_chars 目录内容:", [p.name for p in sorted(ERA.glob("*"))][:40])
print()
for k in ["1017","1019","1020","1023","1025","1028","1030","1032","1042"]:
    hits = list(ERA.glob(f"*{k}*"))
    if not hits:
        print(f"  {k}: 无产物"); continue
    for h in hits:
        if h.suffix == ".json":
            d = json.load(open(h, encoding="utf-8"))
            keys = {kk: d[kk] for kk in d if kk.startswith("PF") or kk in ("ok","bands","n_bands")}
            print(f"  {k} {h.name}: {json.dumps(keys, ensure_ascii=False)[:300]}")
