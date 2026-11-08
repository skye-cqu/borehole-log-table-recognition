# -*- coding: utf-8 -*-
import json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活\runs\table_整合_全量_20261011")
rep = json.load(open(R / "交付门禁_报告.json", encoding="utf-8"))
print("type:", type(rep).__name__)
if isinstance(rep, dict):
    print("keys:", list(rep.keys())[:20])
    for k, v in list(rep.items())[:6]:
        print(" ", k, "->", json.dumps(v, ensure_ascii=False)[:400])
elif isinstance(rep, list):
    print("len:", len(rep))
    print(json.dumps(rep[:3], ensure_ascii=False)[:1500])
