# -*- coding: utf-8 -*-
"""1042: _分割线.json 真实结构 + 709 链为何被丢。"""
import json, sys
import numpy as np
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths

sp = json.loads((paths.RUNS_DIR/"table_reconstruct"/"钻孔柱状图1042_分割线.json").read_text(encoding="utf-8"))
ln0 = sp["lines"][7]
print("== lines[7] 的键 ==", list(ln0.keys()))
print(json.dumps({k: (v if not isinstance(v, list) else "<list len %d>" % len(v)) for k, v in ln0.items()},
                 ensure_ascii=False, indent=1)[:1200])
print()
print("== 全部 11 条的摘要 ==")
for i, ln in enumerate(sp["lines"]):
    ks = {k: (len(v) if isinstance(v, list) else v) for k, v in ln.items()}
    print("[%2d] %s" % (i, json.dumps(ks, ensure_ascii=False)[:260]))
print()
print("== ends_report ==")
print(json.dumps(sp.get("ends_report"), ensure_ascii=False)[:1500])
