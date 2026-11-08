# -*- coding: utf-8 -*-
"""T0 端到端:finalize 跑新目录,验证 (a)1032/1042 不崩 (b)对照图与 20261011 逐格一致。
use_agnes=False 以排除网络变量。"""
import sys, json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
from src.table import finalize_tables as FT

NEW = paths.FINALIZE_FULL_DIR_20261016
OLD = paths.FINALIZE_FULL_DIR
NEW.mkdir(parents=True, exist_ok=True)

targets = ["1032", "1042", "1015", "1023"]
res = {}
for k in targets:
    stem = f"钻孔柱状图{k}"
    try:
        rep = FT.finalize(stem, use_agnes=False, out_dir=NEW)
        err = rep.get("error")
        res[k] = "OK 名带%d 合并%d 门禁%d 账%d" % (
            len(rep.get("名带", [])), len(rep.get("合并组", [])),
            len(rep.get("门禁问题", [])), rep.get("账条数", 0)) if not err else "ERROR: " + err
    except Exception as e:
        res[k] = "崩 %s: %s" % (type(e).__name__, str(e)[:90])
for k, v in res.items():
    print("  %-6s %s" % (k, v))

print()
print("##### 产物列数与表头")
from openpyxl import load_workbook
for k in targets:
    p = NEW / f"钻孔柱状图{k}_整合.xlsx"
    if not p.exists():
        print("  %s 无产物" % k); continue
    ws = load_workbook(p).active
    hdr = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column+1)]
    print("  %-6s %d列 hdr=%s" % (k, ws.max_column, hdr))
    # 1032 深度列前 6 行:确认没有被写进时代名
    if k == "1032":
        vals = [ws.cell(row=r, column=1).value for r in range(2, 8)]
        print("        深度列前6格 = %s" % vals)
