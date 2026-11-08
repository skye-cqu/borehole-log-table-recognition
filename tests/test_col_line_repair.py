# -*- coding: utf-8 -*-
"""col_line_repair 的 span 分组逻辑检查(最小,不碰文件)。"""
from src.table.col_line_repair import _spans


def test_gap_tolerates_small_holes():
    # True 之间 12px 以内的间断应被并成一个 span(GAP_TOL=12)
    flag = [False] * 50 + [True] * 80 + [False] * 12 + [True] * 80 + [False] * 50
    assert _spans(flag, 100) == [(50, 221)]


def test_gap_splits_on_big_holes_and_min_len():
    flag = [True] * 120 + [False] * 40 + [True] * 120 + [False] * 500 + [True] * 99
    # 间隔 40px > GAP_TOL → 分开;末段 99 < 100 丢弃
    assert _spans(flag, 100) == [(0, 119), (160, 279)]
