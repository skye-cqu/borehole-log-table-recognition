# -*- coding: utf-8 -*-
import json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
TR = R/"runs"/"table_reconstruct"
for k in ["1042", "1032", "1019", "1023"]:
    p = TR/f"钻孔柱状图{k}_列结构定稿.json"
    if not p.exists(): print(f"{k}: 无 列结构定稿"); continue
    d = json.load(open(p, encoding="utf-8"))
    cols = d.get("columns", [])
    print(f"##### {k}  列结构定稿 columns={len(cols)}  missing={d.get('missing')!r}")
    for c in cols:
        print(f"   idx={c.get('index')} {c.get('name'):<12} x_mid={c.get('x_at_mid')} y={c.get('y')} src={str(c.get('src'))[:34]}")
    print(f"   frames={[(f.get('side'), f.get('x_at_mid')) for f in d.get('frames',[])]}")
    cont = d.get("content", [])
    print(f"   content={[(c.get('src'), c.get('x_at_mid')) for c in cont]}")
    print()
