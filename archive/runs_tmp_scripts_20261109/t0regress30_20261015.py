# -*- coding: utf-8 -*-
"""T0 全量回归:30 张图,旧代码 vs 新代码,use_agnes=False,逐格对比。"""
import importlib.util, shutil, sys, json
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
from openpyxl import load_workbook

spec = importlib.util.spec_from_file_location("oldfin", R/"runs"/"tmp"/"_old_finalize_20261015.py")
OLD = importlib.util.module_from_spec(spec); sys.modules["oldfin"] = OLD
spec.loader.exec_module(OLD)
from src.table import finalize_tables as NEW

DO = R/"runs"/"tmp"/"_t0old"; DN = R/"runs"/"tmp"/"_t0new"
for d in (DO, DN):
    shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True, exist_ok=True)

def cells(p):
    ws = load_workbook(p).active
    return [[ws.cell(row=r, column=c).value for c in range(1, ws.max_column+1)]
            for r in range(1, ws.max_row+1)]

report = {"等价": [], "有差异": [], "旧崩新好": [], "其他": []}
for k in range(1015, 1045):
    stem = f"钻孔柱状图{k}"
    paths.FINALIZE_FULL_DIR = DO
    try:
        OLD.finalize(stem, use_agnes=False); oe = None
    except Exception as e:
        oe = "%s: %s" % (type(e).__name__, str(e)[:50])
    paths.FINALIZE_FULL_DIR = R/"runs"/"table_整合_全量_20261011"
    try:
        NEW.finalize(stem, use_agnes=False, out_dir=DN); ne = None
    except Exception as e:
        ne = "%s: %s" % (type(e).__name__, str(e)[:50])
    if oe and not ne:
        report["旧崩新好"].append({"图": k, "旧": oe})
        print("  %d 旧崩(%s) -> 新OK  [修复]" % (k, oe)); continue
    if ne:
        report["其他"].append({"图": k, "旧": oe, "新": ne})
        print("  %d 新err=%s 旧err=%s" % (k, ne, oe)); continue
    co, cn = cells(DO/f"{stem}_整合.xlsx"), cells(DN/f"{stem}_整合.xlsx")
    if len(co)!=len(cn) or len(co[0])!=len(cn[0]):
        report["有差异"].append({"图": k, "原因": "形状 %dx%d vs %dx%d" % (len(co),len(co[0]),len(cn),len(cn[0]))})
        print("  %d 形状不同" % k); continue
    diff = [(r+1,c+1,co[r][c],cn[r][c]) for r in range(len(co))
            for c in range(len(co[0])) if co[r][c]!=cn[r][c]]
    if diff:
        report["有差异"].append({"图": k, "差异格数": len(diff), "样例": diff[:3]})
        print("  %d 差异 %d 格: %s" % (k, len(diff), diff[:2]))
    else:
        report["等价"].append(k)
print()
print("等价 %d 张: %s" % (len(report["等价"]), report["等价"]))
print("有差异 %d 张: %s" % (len(report["有差异"]), [d["图"] for d in report["有差异"]]))
print("旧崩新好 %d 张: %s" % (len(report["旧崩新好"]), [d["图"] for d in report["旧崩新好"]]))
print("其他 %d 张: %s" % (len(report["其他"]), report["其他"]))
(R/"runs"/"tmp"/"t0_regress_30.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print("报告 -> runs/tmp/t0_regress_30.json")
