# -*- coding: utf-8 -*-
"""T0 回归:重构前后 unstuck_chain/drop_header_rows 在 30 张 B 目录表上必须逐字节等价。
旧实现从 git HEAD(0ff6e43) 取出,以独立模块加载,避免污染。"""
import json, subprocess, sys, importlib.util
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))

# 取 HEAD 版 finalize_tables.py 的旧实现
old_src = subprocess.run(["git","show","HEAD:src/table/finalize_tables.py"],
                         capture_output=True, text=True, cwd=str(R), encoding="utf-8").stdout
assert "def unstuck_chain" in old_src, "旧源码未取到"
op = R/"runs"/"tmp"/"_old_finalize_20261015.py"
op.write_text(old_src, encoding="utf-8")

from src.core import paths
from src.table import finalize_tables as NEW

def load_old():
    spec = importlib.util.spec_from_file_location("oldfin", op)
    m = importlib.util.module_from_spec(spec)
    sys.modules["oldfin"] = m
    spec.loader.exec_module(m)
    return m
OLD = load_old()

from openpyxl import load_workbook
diff = 0; n = 0
for k in range(1015, 1045):
    p = paths.REEMIT_DIR_20261005B / f"钻孔柱状图{k}_还原.xlsx"
    if not p.exists():
        print("  缺", k); continue
    ws = load_workbook(p).active
    data = [list(r) for r in ws.iter_rows(values_only=True)]
    rb = [float(i) for i in range(len(data)-1)] + [float(len(data)-1)]
    n += 1
    try:
        o = OLD.unstuck_chain([list(r) for r in data], list(rb))
        oo = "ok"
    except Exception as e:
        o, oo = None, "%s: %s" % (type(e).__name__, str(e)[:40])
    # 新版:表头可解析则用 roles,否则回退(与旧一致)
    roles = NEW.column_roles(data[0])
    if "depth" not in roles:
        roles = None
    try:
        nw = NEW.unstuck_chain([list(r) for r in data], list(rb), roles)
        nn = "ok"
    except Exception as e:
        nw, nn = None, "%s: %s" % (type(e).__name__, str(e)[:40])
    if oo != "ok" or nn != "ok":
        print("  %d 旧=%s 新=%s" % (k, oo, nn)); diff += 1; continue
    same_data = o[0] == nw[0]
    same_b = o[1] == nw[1]
    same_ops = o[2] == nw[2]
    same_led = o[3] == nw[3]
    if not (same_data and same_b and same_ops and same_led):
        diff += 1
        print("  %d 不一致: data=%s bounds=%s ops=%s ledger=%s (列=%d)" % (
            k, same_data, same_b, same_ops, same_led, ws.max_column))
        if not same_ops:
            print("     旧ops=%s" % (o[2][:2],))
            print("     新ops=%s" % (nw[2][:2],))
print()
print("对比 %d 张,不一致 %d 张" % (n, diff))
