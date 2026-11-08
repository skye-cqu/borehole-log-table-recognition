# -*- coding: utf-8 -*-
"""时代列门禁测试:G1 墨迹收支(线带墨单独立账)与 G3 名带区间/字高检查(纯函数)。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from src.tools.audit_era_column import (check_bands_order, check_box_heights,
                                        check_cross_charts, check_grammar,
                                        check_ink_accounting)


def test_ink_accounting_and_order():
    ink = np.zeros((100, 50), bool)
    ink[10:30, 10:40] = True                     # 唯一墨=一个字块
    line_mask = np.zeros((100, 50), bool)
    r = check_ink_accounting(ink, line_mask, boxes=[(10, 30)], pad=2)
    assert r["残墨率"] == 0.0
    line_mask[20, 10:40] = True                  # 行线吃掉字中部墨
    r2 = check_ink_accounting(ink, line_mask, boxes=[(10, 30)], pad=2)
    assert r2["线带墨"] > 0 and abs(r2["残墨率"]) < 1e-9   # 线带墨单独立账,不进残墨
    bands = [{"name": "第四系", "rows": [2, 3, 4]}, {"name": "龙潭组", "rows": [6, 7]}]
    assert check_bands_order(bands) == []
    assert check_bands_order(
        [{"name": "a", "rows": [6, 7]}, {"name": "b", "rows": [2, 3]}])[0]["问题"] == "乱序"


def test_bands_overlap_and_dup():
    probs = check_bands_order([{"name": "a", "rows": [2, 3, 8]},
                               {"name": "b", "rows": [3, 4]}])
    kinds = {p["问题"] for p in probs}
    assert "区间重叠" in kinds and "覆盖行重复" in kinds


def test_box_heights():
    ok = check_box_heights([(100, 150), (300, 350)], min_h=15, max_h=260)
    assert ok == []
    bad = check_box_heights([(100, 150), (300, 350), (400, 420)], min_h=30, max_h=260)
    assert len(bad) == 1 and bad[0]["问题"] == "字高越界"


def test_cross_charts_substitution():
    assert check_grammar("第四系")[0] == "valid"
    assert check_grammar("龙潭组上段")[0] == "valid"
    assert check_grammar("酒")[0] == "invalid"       # 单字(1016 实测误读)
    assert check_grammar("山")[0] == "invalid"
    assert check_grammar("画")[0] == "invalid"
    a = {"1016": ["第四系", "龙潭组上段"], "1022": ["第四系", "龙潭组上段"]}
    assert check_cross_charts(a) == []
    b = {"1016": ["第四系", "龙潭组上段"], "1022": ["第四系", "龙酒组上段"]}
    subs = check_cross_charts(b)
    assert subs and "潭/酒" in subs[0]["差异"]
