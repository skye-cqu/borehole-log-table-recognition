# -*- coding: utf-8 -*-
import sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
d = R/"outputs"/"Excel交付_最终_20260915"
print("audit_deliverable.py 无参默认目录:", d)
print("  存在:", d.exists(), " xlsx 数:", len(list(d.glob("*.xlsx"))) if d.exists() else "-")
print("  -> 无参运行会静默审计 0 个文件(退出码 0,假绿)。验证链必须显式传目录。")
print()
print("现有整合目录:")
for p in [paths.FINALIZE_FULL_DIR, R/"runs"/"table_整合_全量_20261011"]:
    print("  %s  存在=%s  xlsx=%d" % (p, p.exists(), len(list(p.glob("*_整合.xlsx"))) if p.exists() else 0))
print()
print("v7 合订表:", (paths.RUNS_DIR/"全量整合_合订表_v7.xlsx").exists())
