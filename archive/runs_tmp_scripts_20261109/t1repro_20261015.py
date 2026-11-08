# -*- coding: utf-8 -*-
"""T1 复现:旧口径(硬编码列号) vs 新口径(按表头名) 逐图违规数对比。"""
import importlib.util, sys, json, subprocess
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from openpyxl import load_workbook
from src.core import paths

# 旧口径:从 git HEAD 取原文件
old_src = subprocess.run(["git","show","HEAD:src/table/delivery_gate.py"],
    capture_output=True, text=True, cwd=str(R), encoding="utf-8").stdout
op = R/"runs"/"tmp"/"_old_gate_20261015.py"
op.write_text(old_src, encoding="utf-8")
spec = importlib.util.spec_from_file_location("oldgate", op)
OLD = importlib.util.module_from_spec(spec); sys.modules["oldgate"] = OLD
spec.loader.exec_module(OLD)

from src.table import delivery_gate as NEW

D = paths.FINALIZE_FULL_DIR
print("%-6s %-8s %-8s %-6s" % ("图", "旧口径", "新口径", "差值"))
tot_o = tot_n = 0
rows = []
for k in range(1015, 1045):
    stem = f"钻孔柱状图{k}"
    p = D/f"{stem}_整合.xlsx"
    ws = load_workbook(p, rich_text=True).active
    o = len(OLD.scan_sheet(ws))
    n = len(NEW.scan_sheet(ws))
    tot_o += o; tot_n += n
    rows.append((k, o, n))
    if o != n or o > 0:
        print("%-6d %-8d %-8d %+d" % (k, o, n, n - o))
print()
print("合计: 旧=%d 新=%d (差 %+d)" % (tot_o, tot_n, tot_n - tot_o))
print()
# 只看三张特殊图
print("== 三张特殊图 ==")
for k in (1019, 1032, 1042):
    ws = load_workbook(D/f"钻孔柱状图{k}_整合.xlsx", rich_text=True).active
    print("  %d: 旧=%d 新=%d" % (k, len(OLD.scan_sheet(ws)), len(NEW.scan_sheet(ws))))
print()
# 真实违规明细
print("== 修正后仍存在的违规(按图) ==")
detail = {}
for k in range(1015, 1045):
    stem = f"钻孔柱状图{k}"
    ws = load_workbook(D/f"{stem}_整合.xlsx", rich_text=True).active
    bad = NEW.scan_sheet(ws)
    if bad:
        hdr = [ws.cell(row=1,column=c).value for c in range(1, ws.max_column+1)]
        detail[k] = [{"行": r, "列": hdr[c-1], "值": s[:40]} for r, c, s in bad]
        print("  %d: %d 条" % (k, len(bad)))
print()
print("总计 %d 条" % sum(len(v) for v in detail.values()))
(R/"runs"/"tmp"/"t1_违规明细_20261015.json").write_text(
    json.dumps({str(k): v for k, v in detail.items()}, ensure_ascii=False, indent=1), encoding="utf-8")
print("明细 -> runs/tmp/t1_违规明细_20261015.json")
