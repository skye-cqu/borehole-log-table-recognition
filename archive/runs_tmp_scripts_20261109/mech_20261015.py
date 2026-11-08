# -*- coding: utf-8 -*-
"""机制判别:1032 深度列 单格重读/agnes 读数 vs v7 值 —— 是 OCR 丢前导位还是裁片偏移。"""
import json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
TR = R/"runs"/"table_reconstruct"
for nm in ["钻孔柱状图1032_单格重读.json", "钻孔柱状图1032_agnes读数.json"]:
    p = TR/nm
    if not p.exists(): print(nm, "不存在"); continue
    d = json.load(open(p, encoding="utf-8"))
    print("="*66); print(nm, "type:", type(d).__name__, "len:", len(d) if hasattr(d,'__len__') else '-')
    if isinstance(d, dict):
        ks = list(d.keys())[:6]
        for k in ks:
            print("  key", k, "->", json.dumps(d[k], ensure_ascii=False)[:300])
    elif isinstance(d, list):
        for e in d[:6]:
            print("  ", json.dumps(e, ensure_ascii=False)[:300])
