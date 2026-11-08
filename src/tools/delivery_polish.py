# -*- coding: utf-8 -*-
"""交付润色:列宽 + 岩性描述换行 + 冻结表头(用户 2026-10-28 问"为什么岩性描述
一列的内容占好多列"——数据只在 H 列,无列宽无换行时 Excel 溢出显示到邻格)。
处理 FINALIZE_FULL_DIR 全部整合 xlsx,幂等可重跑。列宽按角色:
描述 62(换行,左上对齐),时代 16,层号 12,其余 9。用法:
  python src/tools/delivery_polish.py [图号...]   (无参数=全量)
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from openpyxl import load_workbook
from openpyxl.styles import Alignment
from openpyxl.utils import get_column_letter

from src.core import paths
from src.table.finalize_tables import column_roles

WIDTH = {"era": 16, "layer": 12, "desc": 62, "depth": 9, "thick": 9,
         "length": 9, "dip": 9, "true_thick": 9}
_WRAP = Alignment(wrap_text=True, vertical="top", horizontal="left")


def polish(stem):
    f = paths.FINALIZE_FULL_DIR / f"{stem}_整合.xlsx"
    wb = load_workbook(f)
    ws = wb.active
    data = list(ws.iter_rows(values_only=True))
    roles = column_roles(data[0] if data else [])
    n_set = 0
    for role, w in WIDTH.items():
        c = roles.get(role)
        if c is None:
            continue
        ws.column_dimensions[get_column_letter(c + 1)].width = w
        n_set += 1
    _d = roles.get("desc")
    n_wrap = 0
    if _d is not None:
        for row in ws.iter_rows(min_row=2, min_col=_d + 1, max_col=_d + 1):
            c = row[0]
            if c.__class__.__name__ != "MergedCell":
                c.alignment = _WRAP
                n_wrap += 1
    ws.freeze_panes = "A2"
    wb.save(f)
    return stem, True, f"列宽{n_set} 换行{n_wrap}格"


def main():
    want = {s if s.startswith("钻孔柱状图") else f"钻孔柱状图{s}" for s in sys.argv[1:]}
    stems = sorted(want) if want else sorted(
        p.name[:-len("_整合.xlsx")] for p in paths.FINALIZE_FULL_DIR.glob("*_整合.xlsx"))
    bad = 0
    for s in stems:
        try:
            _, ok, info = polish(s)
            print(s, info)
        except Exception as e:  # noqa: BLE001
            bad += 1
            print(s, "FAIL", repr(e)[:120])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
