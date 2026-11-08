# -*- coding: utf-8 -*-
"""audit_deliverable 单测:哨兵残留、字母伪差、多值捆叠三类缺陷必须各被抓到。"""
import sys
from pathlib import Path

from openpyxl import Workbook

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.tools.audit_deliverable import audit


def _book(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["层厚", "采长", "倾角", "真厚", "岩性描述"])
    ws.append([1.20, 1.00, "8°", 1.19, "粉砂岩"])          # 正常
    ws.append(["@单", 0.45, "", 0.45, "煤"])               # 哨兵未展开(P0 事故形态)
    ws.append(["1.20 0.45", 1.60, "", 1.19, "泥岩、粉砂岩"])  # 一行捆两物理行(P1 症状)
    ws.append(["38.13 n 77", "", "", 0.30, "灰岩"])         # 数字被认成字母
    p = tmp_path / "钻孔柱状图9999_还原.xlsx"
    wb.save(p)
    return p


def test_audit_catches_three_defect_classes(tmp_path):
    r = audit(_book(tmp_path))
    assert r["数据行"] == 4
    assert r["哨兵"] == 1, r
    assert r["多值格"] == 2, r          # 捆叠格与字母伪差格都算多值
    assert r["非数值"] == 2, r          # 哨兵单独计一档,捆叠格与字母伪差格算非数值
    assert r["空值次"] > 0, r           # 空倾角、空采长计入空值次


def test_audit_passes_clean_sheet(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["层厚", "采长", "倾角", "真厚", "岩性描述"])
    ws.append([1.20, 1.00, "8°", 1.19, "粉砂岩"])
    p = tmp_path / "clean.xlsx"
    wb.save(p)
    r = audit(p)
    assert (r["哨兵"], r["多值格"], r["非数值"]) == (0, 0, 0), r
