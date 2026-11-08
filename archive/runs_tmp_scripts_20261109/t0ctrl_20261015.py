# -*- coding: utf-8 -*-
"""T0 受控回归:同一批图,旧代码 vs 新代码,都 use_agnes=False,产物各写临时目录,逐格对比。
旧代码从 HEAD 取出,monkeypatch paths.FINALIZE_FULL_DIR 重定向输出。"""
import importlib.util, shutil, sys
from pathlib import Path
R = Path(r"D:\Skye\Documents\Work\高维智矿\7.13杂活")
sys.path.insert(0, str(R))
from src.core import paths
from openpyxl import load_workbook

OLD_SRC = R/"runs"/"tmp"/"_old_finalize_20261015.py"
spec = importlib.util.spec_from_file_location("oldfin", OLD_SRC)
OLD = importlib.util.module_from_spec(spec); sys.modules["oldfin"] = OLD
spec.loader.exec_module(OLD)
from src.table import finalize_tables as NEW

DO = R/"runs"/"tmp"/"_t0old"; DN = R/"runs"/"tmp"/"_t0new"
for d in (DO, DN):
    shutil.rmtree(d, ignore_errors=True); d.mkdir(parents=True, exist_ok=True)

FIGS = ["1015","1017","1019","1023","1030","1035","1037","1044"]
def cells(p):
    ws = load_workbook(p).active
    return [[ws.cell(row=r, column=c).value for c in range(1, ws.max_column+1)]
            for r in range(1, ws.max_row+1)]

print("图     旧        新       形状        差异格")
bad = []
for k in FIGS:
    stem = f"钻孔柱状图{k}"
    # 旧:monkeypatch 输出目录
    paths.FINALIZE_FULL_DIR = DO
    try:
        OLD.finalize(stem, use_agnes=False)
        oe = None
    except Exception as e:
        oe = "%s: %s" % (type(e).__name__, str(e)[:60])
    paths.FINALIZE_FULL_DIR = R/"runs"/"table_整合_全量_20261011"
    try:
        NEW.finalize(stem, use_agnes=False, out_dir=DN)
        ne = None
    except Exception as e:
        ne = "%s: %s" % (type(e).__name__, str(e)[:60])
    if oe or ne:
        print("  %-5s 旧err=%s 新err=%s" % (k, oe, ne)); bad.append(k); continue
    co, cn = cells(DO/f"{stem}_整合.xlsx"), cells(DN/f"{stem}_整合.xlsx")
    same_shape = (len(co)==len(cn) and len(co[0])==len(cn[0]))
    if not same_shape:
        print("  %-5s %dx%d     %dx%d    形状不同!" % (k, len(co), len(co[0]), len(cn), len(cn[0])))
        bad.append(k); continue
    diff = [(r+1,c+1,co[r][c],cn[r][c]) for r in range(len(co))
            for c in range(len(co[0])) if co[r][c]!=cn[r][c]]
    print("  %-5s OK        OK       %dx%d      %d" % (k, len(cn), len(cn[0]), len(diff)))
    for d in diff[:6]:
        print("        r%d c%d 旧=%r 新=%r" % d)
    if diff: bad.append(k)
print()
print("有差异或出错的图: %s" % (bad or "无 —— 旧新完全等价"))
