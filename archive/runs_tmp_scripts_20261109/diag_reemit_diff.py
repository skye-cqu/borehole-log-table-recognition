# -*- coding: utf-8 -*-
"""识读窗修复重跑校验(2026-11-03)v2:新还原(20261103) vs 存量(20261023)。
数值感知比较(float(x)==float(y) 视为同值,int/float 字符串化不算变化)。
预期: 仅倾角列实质变化(含杂→纯为主);其余列零实质变化。
"""
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.table.finalize_tables import column_roles  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

NUMRE = re.compile(r"^-?\d+(\.\d+)?°?$")


def same_val(a, b):
    if str(a) == str(b):
        return True
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return False


res = {}
for new_p in sorted(paths.REEMIT_DIR_20261103.glob("钻孔柱状图*_还原.xlsx")):
    stem = new_p.name.replace("_还原.xlsx", "")
    old_p = paths.REEMIT_DIR_20261023 / new_p.name
    if not old_p.exists():
        continue
    nw = list(load_workbook(new_p).active.iter_rows(values_only=True))
    od = list(load_workbook(old_p).active.iter_rows(values_only=True))
    rn, ro = column_roles(nw[0]), column_roles(od[0])
    colchg = {}
    for cidx in range(len(nw[0])):
        n_diff = sum(1 for r in range(1, min(len(nw), len(od)))
                     if not same_val(nw[r][cidx], od[r][cidx]))
        if n_diff:
            colchg[str(nw[0][cidx])] = n_diff
    cd, co = rn.get("dip"), ro.get("dip")
    dip = None
    if cd is not None and co is not None:
        j2p = p2j = p2p = 0
        for r in range(1, min(len(nw), len(od))):
            a = "" if nw[r][cd] is None else str(nw[r][cd]).strip()
            b = "" if od[r][co] is None else str(od[r][co]).strip()
            if a == b:
                continue
            ap, bp = bool(NUMRE.match(a or "~")), bool(NUMRE.match(b or "~"))
            if ap and not bp:
                j2p += 1
            elif bp and not ap:
                p2j += 1
            elif ap and bp:
                p2p += 1
        dip = {"含杂→纯": j2p, "纯→含杂": p2j, "纯值变": p2p}
    res[stem] = {"列实质变化": colchg, "dip": dip}
p = paths.RUNS_DIR / "tmp" / "diag_reemit_diff.json"
p.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
tot = {"含杂→纯": 0, "纯→含杂": 0, "纯值变": 0}
for stem, rec in res.items():
    d = rec.get("dip")
    if d:
        for k in tot:
            tot[k] += d[k]
    print(stem[-4:], rec["列实质变化"], rec.get("dip", ""))
print("合计 dip:", tot)
print("→", p)
