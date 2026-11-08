# -*- coding: utf-8 -*-
"""交付级整表门禁测试:列合法性规则表与全表扫描(805 格系统性违规的检测层)。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openpyxl import Workbook, load_workbook

from src.table.delivery_gate import scan_sheet


def _mk(ws_rows, merged=None, tmp_path=None, name="t.xlsx"):
    wb = Workbook()
    ws = wb.active
    ws.append(["地质时代", "煤层/标志层号", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述"])
    for r in ws_rows:
        ws.append(r)
    for m in (merged or []):
        ws.merge_cells(m)
    p = tmp_path / name
    wb.save(p)
    return load_workbook(p).active


def test_scan_sheet_报出各类违规(tmp_path):
    ws = _mk([
        ["飞仙关组二至一段", "1", 12.28, 12.28, 0, "5°", 3, "表土"],      # 全合法
        ["3.7", "1", 12.83, 0.55, 3, "。9", "MOLO", "粉砂质泥岩"],        # 时代/倾角/真厚违规
        ["大隆组", "", "355.95 357.47", 1.52, 3, "4°", "0.7!", "泥岩"],   # 深度双数串+真厚幻读
        ["长兴组", "三上", 13.0, 0.17, "", "4°", "", ""],
    ], tmp_path=tmp_path)
    bad = scan_sheet(ws)
    got = {(r, c, s) for r, c, s in bad}
    assert (3, 1, "3.7") in got                       # 时代列数字
    assert (3, 6, "。9") in got                       # 倾角句号
    assert (3, 7, "MOLO") in got                      # 真厚字母
    assert (4, 3, "355.95 357.47") in got             # 深度双数串
    assert (4, 7, "0.7!") in got                      # 真厚幻读感叹号
    assert (2, 6, "5°") not in got and (5, 2, "三上") not in got   # 合法不报
    assert len(bad) == 5


def test_scan_sheet_合并区非首格与空格合法(tmp_path):
    ws = _mk([["飞仙关组", "1", 1, 1, 1, "5°", 1, "x"], [None, None, 2, 1, 1, "5°", 1, "y"]],
             merged=["A2:A3"], tmp_path=tmp_path)
    assert scan_sheet(ws) == []                        # A3=MergedCell(None) 合法


def test_scan_sheet_rich_text值参与判定(tmp_path):
    from openpyxl.cell.rich_text import CellRichText, TextBlock
    from openpyxl.cell.text import InlineFont
    wb = Workbook()
    ws = wb.active
    ws.append(["地质时代", "煤层/标志层号", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述"])
    ws.append(["第四系", "1", 1, 1, 1, "5°", 1, ""])
    c = ws.cell(row=2, column=8)
    c.value = CellRichText("泥岩", TextBlock(InlineFont(color="FFFF0000"), "灰"), "岩")
    ws.cell(row=3, column=6).value = "。8"
    p = tmp_path / "r.xlsx"
    wb.save(p)
    ws2 = load_workbook(p, rich_text=True).active
    bad = scan_sheet(ws2)
    assert [(r, c) for r, c, _ in bad] == [(3, 6)]     # 描述 rich 合法不误报


def test_classify_按内容分流_无整图豁免():
    """归类只看**内容**(粘连串 vs 符号幻读),不再看图号。

    旧口径把 1019/1032/1042 的任何违规一律标成"错位专项",导致 1032 的 329 条
    假违规与 16 条真违规混为一谈(2026-10-15 修正)。图的专项归属改用 specialty_of()。
    """
    from src.table.delivery_gate import classify, specialty_of
    assert classify("钻孔柱状图1018", 6, "。9") == "符号幻读"
    assert classify("钻孔柱状图1037", 3, "355.95 357.47") == "粘连专项"
    assert classify("钻孔柱状图1035", 5, "3.20 4.06") == "粘连专项"
    assert classify("钻孔柱状图1043", 3, "51-11") == "符号幻读"
    # 特殊图不再被整图豁免:同一条粘连串在 1032 上照样按内容归为"粘连专项"
    assert classify("钻孔柱状图1032", 1, "355.95 357.47", "depth") == "粘连专项"
    assert classify("钻孔柱状图1032", 1, "。9", "depth") == "符号幻读"
    assert classify("钻孔柱状图1042", 6, "g°", "dip") == "符号幻读"
    assert classify("钻孔柱状图1019", 1, "3.7", "era") == "符号幻读"
    # 专项归属与内容归类正交
    for k in (1019, 1032, 1042):
        assert specialty_of(f"钻孔柱状图{k}") == "错位专项"
    assert specialty_of("钻孔柱状图1018") is None


def test_header_roles_按表头名解析():
    """列规则必须按**表头名**取,不能按列号(1032 六列/1042 七列)。"""
    from src.table.delivery_gate import header_roles
    assert header_roles(["深度", "层厚", "采长", "倾角", "真厚", "岩性描述"]) == {
        1: "depth", 2: "thick", 3: "length", 4: "dip", 5: "true_thick", 6: "desc"}
    assert header_roles(["地质时代", "煤层标志层号", "深度", "层厚", "采长",
                         "倾角", "岩性描述"]) == {
        1: "era", 2: "layer", 3: "depth", 4: "thick", 5: "length",
        6: "dip", 7: "desc"}
    # 别名:'煤层/标志层号' 与 '煤层标志层号' 同义
    assert header_roles(["地质时代", "煤层/标志层号", "深度"]) == {
        1: "era", 2: "layer", 3: "depth"}
    # 1023 原图手绘表头确为"层厚"在前 —— 按名解析必须如实映射,不得"纠正"
    assert header_roles(["地质时代", "煤层标志层号", "层厚", "深度", "采长",
                         "倾角", "真厚", "岩性描述"])[3] == "thick"


def test_header_roles_无法映射即报错_不静默跳过():
    """表头名映射不到规则必须抛错 —— 静默跳过正是 491 条虚高违规的成因。"""
    import pytest
    from src.table.delivery_gate import header_roles
    with pytest.raises(ValueError):
        header_roles(["地质时代", "深度", "莫名其妙的列"])
    with pytest.raises(ValueError):
        header_roles([None, None])


def test_decide_仲裁四分支():
    from src.table.delivery_gate import decide
    assert decide("", None, 3) == ("清空", None, "格内无墨")
    assert decide(None, "1", 3) == ("清空", None, "格内无墨")
    # 像素合法→替换(倾角补°)
    assert decide("21.1", None, 6) == ("替换", "21.1°", "像素读数合法")
    assert decide("21.1°", None, 6) == ("替换", "21.1°", "像素读数合法")
    assert decide("355.95", None, 3) == ("替换", "355.95", "像素读数合法")
    assert decide("三上", None, 2) == ("替换", "三上", "像素读数合法")
    # 像素非法但 Agnes 合法→替换
    assert decide("。9", "20.9°", 6) == ("替换", "20.9°", "像素非法,Agnes读数合法")
    assert decide("3.7", "龙潭组", 1) == ("替换", "龙潭组", "像素非法,Agnes读数合法")
    # 双非法→清空记账
    assert decide("MOLO", "XYZ", 7) == ("清空", None, "双引擎均非法,清空记账")
    assert decide("。", None, 8) == ("清空", None, "双引擎均非法,清空记账")


def test_decide_归一化去空格():
    from src.table.delivery_gate import decide
    assert decide("21.1 °", None, 6) == ("替换", "21.1°", "像素读数合法")
    assert decide(" 4 ", None, 6) == ("替换", "4°", "像素读数合法")


def test_decide_数值列缺首位须第二引擎():
    """打印数值一律带前导0(0.23/0.60 像素实证);像素读 '.00' = OCR 丢首位残墨
    (1015 r48 原图眼验:'。'前有退化数字,B 读 ':.00')。缺首位读数经 NUM_RE 判非法
    →Agnes 独立读出合法值才替换,否则清空记账,不冒 0.0 顶格风险。"""
    from src.table.delivery_gate import decide
    assert decide(".00", "2.00", 5) == ("替换", "2.00", "像素非法,Agnes读数合法")
    assert decide(".00", None, 5) == ("清空", None, "双引擎均非法,清空记账")
    assert decide(".00", ".00", 5) == ("清空", None, "双引擎均非法,清空记账")
    assert decide(".00", "UNKNOWN", 5) == ("清空", None, "双引擎均非法,清空记账")
    assert decide(".5", "0.5", 7) == ("替换", "0.5", "像素非法,Agnes读数合法")
    # 非数值列/正常读数不受影响
    assert decide("泥岩", None, 8) == ("替换", "泥岩", "像素读数合法")


def test_main_违规退出1_干净退出0(tmp_path, monkeypatch, capsys):
    from src.table import delivery_gate as dg
    ws = _mk([["3.7", "1", 1, 1, 1, "。9", 1, "x"]], tmp_path=tmp_path, name="钻孔柱状图1015_整合.xlsx")
    monkeypatch.setattr(dg.paths, "FINALIZE_FULL_DIR", tmp_path)
    assert dg.main([]) == 1
    rep = tmp_path / "交付门禁_报告.json"
    import json as _json
    data = _json.loads(rep.read_text(encoding="utf-8"))
    assert len(data["符号幻读"]) == 2 and data["粘连专项"] == []
    # 干净目录
    import shutil
    d2 = tmp_path / "clean"
    d2.mkdir()
    shutil.copy(tmp_path / "钻孔柱状图1015_整合.xlsx", d2 / "钻孔柱状图1015_整合.xlsx")
    wb = dg.load_workbook(d2 / "钻孔柱状图1015_整合.xlsx")
    ws2 = wb.active
    ws2.cell(row=2, column=1).value = "第四系"
    ws2.cell(row=2, column=6).value = "5°"
    wb.save(d2 / "钻孔柱状图1015_整合.xlsx")
    monkeypatch.setattr(dg.paths, "FINALIZE_FULL_DIR", d2)
    assert dg.main([]) == 0


def test_num_截断数非法_点后无位():
    """B 目录 OCR 丢小数位读数('1.'/'0.')是截断数,gate 必须拦(1034/1035 实锤 22 格);
    整数与小数合法。"""
    from src.table import delivery_gate as dg
    assert dg._num("1.") is False
    assert dg._num(".5") is False
    assert dg._num("2") is True
    assert dg._num("2.50") is True


def test_decide_截断数像素读数走第二引擎():
    """像素读出截断数('1.')→ 非法 → Agnes 合法值替换;Agnes 也截断 → 清空记账。"""
    from src.table import delivery_gate as dg
    assert dg.decide("1.", "1.53", 7) == ("替换", "1.53", "像素非法,Agnes读数合法")
    assert dg.decide("1.", None, 7) == ("清空", None, "双引擎均非法,清空记账")
    assert dg.decide("2.", "2.", 7) == ("清空", None, "双引擎均非法,清空记账")
