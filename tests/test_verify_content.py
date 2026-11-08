# -*- coding: utf-8 -*-
"""内容互证解析:OCR 单元格数字提取、倾角解析、层厚=深度差/真厚=层厚×cos倾角 判定。"""
import openpyxl

from src.verify.content_check import check_rows, parse_dip, parse_numbers


def test_parse_numbers_basic_and_ocr_space_split():
    assert parse_numbers(None) == []
    assert parse_numbers(13) == [13.0]
    assert parse_numbers("82.18") == [82.18]
    assert parse_numbers("3. 88") == [3.88]          # OCR 把一个数拆成两段
    assert parse_numbers("7 .97") == [7.97]
    assert parse_numbers("136.75 137.00") == [136.75, 137.00]   # 一格多子层
    assert parse_numbers("3.70 1.30 3.60") == [3.7, 1.3, 3.6]
    assert parse_numbers("C") == []                  # OCR 垃圾
    assert parse_numbers("5-7") == []                # 区间/含连字符:不可解析
    assert parse_numbers("1.4 49 0.60") == [1.4, 49.0, 0.6]     # 垃圾数字保留,由配对计数暴露


def test_parse_dip_forms():
    assert parse_dip(None) is None
    assert parse_dip(8) == 8.0
    assert parse_dip("4") == 4.0
    assert parse_dip("4°") == 4.0
    assert parse_dip("5 D") == 5.0                   # D=度 的 OCR 形态
    assert parse_dip("5 5") is None                  # 歧义(度分?)不参与互证


def test_check_rows_first_layer_from_surface():
    rows = [{"d": [13.0], "t": [13.0], "z": [13.0], "dip": None}]
    res = check_rows(rows)
    assert res["layers_checked"] == 1
    assert res["errors"] == []
    assert res["dip_checked"] == 0


def test_check_rows_relation_and_violation():
    rows = [
        {"d": [10.0], "t": [10.0], "z": [10.0], "dip": None},       # 表层:深度-0
        {"d": [25.0, 40.0], "t": [15.0, 15.02], "z": [14.98, 14.9], "dip": 3.0},
        {"d": [60.0], "t": [30.0], "z": [29.0], "dip": None},       # 层厚差 5 => 违规
    ]
    res = check_rows(rows)
    assert res["layers_checked"] == 4
    viol = [e for e in res["errors"] if e["abs"] > 0.11]
    assert len(viol) == 1 and viol[0]["row"] == 2 and viol[0]["abs"] == 10.0
    # 真厚=层厚*cos(倾角):15*cos3°=14.979 vs 14.98 → 过;15*cos3° vs 14.9 → 0.079
    assert res["dip_checked"] == 2


def test_check_rows_unpaired_row_no_cascade():
    rows = [
        {"d": [10.0, 20.0], "t": [10.0], "z": [], "dip": None},     # 计数不齐:不配对
        {"d": [30.0, 50.0], "t": [10.0, 20.0], "z": [], "dip": None},  # j=0 用上行末深度=20
    ]
    res = check_rows(rows)
    assert res["unpaired_rows"] == 1
    assert res["layers_checked"] == 2            # 第二行 j=0:20→30 差10 vs 层厚10;j=1:30→50 差20
    assert res["errors"] == []


def test_check_rows_structural_non_monotone_isolated():
    rows = [
        {"d": [10.0, 20.0], "t": [10.0, 10.0], "z": [], "dip": None},
        {"d": [25.0, 3.0], "t": [5.0, 9.9], "z": [], "dip": None},   # 3<25:OCR 截断('329.79'→'3')
        {"d": [30.0, 50.0], "t": [10.0, 20.0], "z": [], "dip": None},  # j=0 用 20(未被 3 污染)
    ]
    res = check_rows(rows)
    assert res["structural_rows"] == 1
    assert res["layers_checked"] == 5            # 首行 2 + 损伤行 j=0(合法)+ 末行 2
    gross = [e for e in res["errors"] if e["abs"] > 0.11]
    assert gross == []                            # 截断行不产生违规,也不污染深度梯


def test_load_rows_shifted_marker_rows(tmp_path):
    """煤层标志层号行:层号占 C、深度在 D、层厚在 E——按位移识别还原。"""
    from src.verify.depth_thickness_report import load_rows
    p = tmp_path / "钻孔柱状图9999_还原.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["地质时代", "煤层标志层号", "深度", "层厚", "采长", "倾角", "真厚", "岩性描述"])
    ws.append([None, None, 300, 300, None, None, 300, "表土"])          # 常规行:深度在 C
    ws.append([None, "中", 15, "304.40 306.00", "1.60 1.20", None, None, "煤"])  # 位移行
    ws.append([None, None, "308.00", "2.00", None, None, "1.98", "砂"])          # 常规行
    wb.save(p)
    rows = load_rows(p)
    assert rows[0] == {"d": [300.0], "t": [300.0], "z": [300.0], "dip": None}
    assert rows[1] == {"d": [304.4, 306.0], "t": [1.6, 1.2], "z": [], "dip": None}
    assert rows[2] == {"d": [308.0], "t": [2.0], "z": [1.98], "dip": None}
