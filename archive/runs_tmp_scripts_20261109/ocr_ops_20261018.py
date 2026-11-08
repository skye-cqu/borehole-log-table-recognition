# -*- coding: utf-8 -*-
"""判名口径的表头 OCR 可靠性:不看"逐字全对",看 match_name 是否落到正确列名。"""
import json, sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
from src.table.header_assign import match_name
A = paths.RUNS_DIR / "table_reconstruct"
tot = ok = 0
bad = []
for f in sorted(A.glob("*_表头映射.json")):
    w = json.loads(f.read_text(encoding="utf-8"))
    stem = f.name[:-len("_表头映射.json")]
    for k, v in (w.get("label_verify") or {}).items():
        if k not in ("地质时代","煤层标志层号","深度","层厚","采长","倾角","真厚","柱状","岩性描述"): continue
        tot += 1
        got = match_name(v or "")
        if got == k: ok += 1
        else: bad.append((stem[-4:], k, v, got))
print("表头判名: %d/%d = %.1f%%" % (ok, tot, ok/tot*100))
print("\n判错的样本:")
for b in bad: print("  %s %-6s OCR=%-14r 判成=%s" % b)
