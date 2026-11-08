# -*- coding: utf-8 -*-
"""与参考表对比工具测试:单元格规范化/比对 + 像素区间行对齐 + 整合回写标黄。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.table.compare_ref import cell_diff, compare_chart, norm_cell, pair_rows


def test_norm_cell():
    assert norm_cell(" 12.28 ") == "12.28"
    assert norm_cell("0°") == "0"
    assert norm_cell("１２.２８") == "12.28"        # 全角→半角
    assert norm_cell(None) is None and norm_cell("") is None
    assert norm_cell("表 土 夹矸") == "表土夹矸"      # 空白差异视为相等


def test_cell_diff_文本列标点归一():
    # 参考表描述列用空格/点号风格,我方用全角标点——内容同不算 diff(实测占16%假阳)
    assert cell_diff("泥岩：深灰色，岩石松软", "泥岩.深灰色 岩石松软", text=True) == "equal"
    assert cell_diff("煤：黑色，块状", "煤.黑色 块状", text=True) == "equal"
    # 文字差异仍 diff(黄铁矿结核 vs 黄铁结核)
    assert cell_diff("夹顺层黄铁矿结核", "夹顺层黄铁结核", text=True) == "diff"
    # 数值列不受影响(小数点不能去)
    assert cell_diff("12.28", "1228", text=False) == "diff"
    assert cell_diff("12.28", "12.28", text=True) == "equal"


def test_cell_diff():
    assert cell_diff(12.28, "12.28") == "equal"
    assert cell_diff(12.28, "12.281") == "equal"     # 数值容差 0.005
    assert cell_diff("31.5", "3.15") == "diff"       # 丢小数点型错误必须现形
    assert cell_diff("表土", "表士") == "diff"
    assert cell_diff(None, "第四系") == "ours_empty"
    assert cell_diff("第四系", "") == "theirs_empty"
    assert cell_diff("", None) == "equal"


def test_pair_rows():
    ours = [(100, 200), (200, 300), (300, 400)]
    ref = [(102, 198), (300, 400)]
    assert pair_rows(ours, ref) == [(0, 0), (2, 1)]   # 互相最佳+过半才配
    # 我方一刀 vs 参考两刀(切分不同):互不半覆,不配
    ours2 = [(100, 300)]
    ref2 = [(100, 190), (195, 300)]
    assert pair_rows(ours2, ref2) == []
    # 嵌套大偏移:重叠不过半不配
    assert pair_rows([(0, 100)], [(90, 200)]) == []


def test_red_mark_字级红标():
    from openpyxl.cell.rich_text import CellRichText
    from src.table.compare_ref import red_mark
    # 我方多一字:只标那一个字(用户指令:一句话一个字不一样只标那个字)
    rt = red_mark("飞仙关组二至一段", "飞仙关组二至段")
    assert isinstance(rt, CellRichText) and str(rt) == "飞仙关组二至一段"
    reds = [str(b) for b in rt if not isinstance(b, str)]
    assert reds == ["一"], reds
    # 单字替换:标被换的字
    rt2 = red_mark("夹顺层黄铁矿结核", "夹顺层黄铁结核")
    assert str(rt2) == "夹顺层黄铁矿结核"
    reds2 = [(str(b), b.font.color.rgb) for b in rt2 if not isinstance(b, str)]
    assert reds2 == [("矿", "00FF0000")] or reds2 == [("矿", "FFFF0000")], reds2
    # 无差异不标
    assert red_mark("相同", "相同") is None
    # 我方缺字:插入点邻字标红定位,文本不增删
    rt3 = red_mark("夹顺层黄铁结核", "夹顺层黄铁矿结核")
    assert str(rt3) == "夹顺层黄铁结核"
    assert len([b for b in rt3 if not isinstance(b, str)]) == 1
    assert str([b for b in rt3 if not isinstance(b, str)][0]) in "铁结"


def test_compare_chart_红字与账(tmp_path):
    import csv
    from openpyxl import Workbook, load_workbook
    # 我方表:表头+2数据行(行区间 100-200 / 200-300)
    wb = Workbook()
    ws = wb.active
    ws.append(["地质时代", "煤层/标志层号", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述"])
    ws.append(["第四系", "1", 12.28, 12.28, "0", "0°", "", "表土"])
    ws.append(["第四系", "", 12.83, 0.55, "3", "3°", "3", "粉砂质泥岩"])
    wb.save(tmp_path / "a_整合.xlsx")
    # 参考表:22列,y区间同系;第二行层厚不同(0.56)、第三行描述不同
    rb = Workbook()
    rs = rb.active
    hdr = (["序号", "y_top", "y_bottom", "row_height", "地质时代", "煤层/标志层号",
            "深度(m)", "层厚(m)", "采长(m)", "倾角", "真厚(m)", "柱状", "岩性描述"]
           + ["裁"] * 9)
    rs.append(hdr)
    rs.append([1, 100, 200, 100, "", "1", "12.28", "12.28", "0", "0", "", "", "表土"])
    rs.append([2, 200, 300, 100, "", "", "12.83", "0.56", "3", "3", "3", "", "泥岩"])
    rb.save(tmp_path / "a_ref.xlsx")
    rep = compare_chart("a", tmp_path, tmp_path, ref_suffix="_ref.xlsx",
                        row_ivs={0: (100, 200), 1: (200, 300)})
    assert rep["配对行"] == 2 and rep["diff"] == 2 and rep["标黄"] == 2
    wb2 = load_workbook(tmp_path / "a_整合.xlsx", rich_text=True)

    def _red(c):
        f = wb2.active.cell(row=c[0], column=c[1]).font
        col = f.color.rgb if f.color else None
        return isinstance(col, str) and col.endswith("FF0000")   # 红=字体色

    assert _red((3, 4))                                 # 层厚(数值列)整格红字
    from openpyxl.cell.rich_text import CellRichText
    v_desc = wb2.active.cell(row=3, column=8).value     # 描述列=字级红标(只有"泥岩"差异段红)
    assert str(v_desc) == "粉砂质泥岩"
    reds = [(str(b), str(b.text)) for b in v_desc if not isinstance(b, str)]
    assert reds and all(t in "粉砂质泥岩" for _, t in reds) and len(str(v_desc)) > len(reds)
    assert not _red((2, 4))                             # 相等格不动
    # 复跑幂等:先制造残留黄底,重跑须清底再打黄字
    from openpyxl.styles import PatternFill
    wb3 = load_workbook(tmp_path / "a_整合.xlsx")
    wb3.active.cell(row=2, column=4).fill = PatternFill("solid", start_color="FFFF00")
    from openpyxl.styles import Font
    wb3.active.cell(row=2, column=4).font = Font(color="FFFF00")   # 残留黄字
    wb3.active.cell(row=2, column=8).font = Font(color="FF0000")   # 残留红字(上轮 diff 本轮 equal)
    wb3.save(tmp_path / "a_整合.xlsx")
    compare_chart("a", tmp_path, tmp_path, ref_suffix="_ref.xlsx",
                  row_ivs={0: (100, 200), 1: (200, 300)})
    wb4 = load_workbook(tmp_path / "a_整合.xlsx")
    c_equal = wb4.active.cell(row=2, column=4)
    assert not (isinstance(c_equal.fill.start_color.rgb, str)
                and c_equal.fill.start_color.rgb.endswith("FFFF00"))   # 残留黄底被清
    for cc in (c_equal, wb4.active.cell(row=2, column=8)):
        assert not (cc.font.color and isinstance(cc.font.color.rgb, str)
                    and cc.font.color.rgb.endswith(("FFFF00", "FF0000")))  # 残留黄/红字被清
    rows = list(csv.DictReader(open(tmp_path / "a_对比账.csv", encoding="utf-8-sig")))
    assert len(rows) == 4                                # 2 diff + 2 theirs_empty 记账
    assert rows[2]["我方值"] == "0.55" and rows[2]["参考值"] == "0.56"
    assert rep["ours_empty"] + rep["theirs_empty"] == 2   # 时代列单方缺只记账
