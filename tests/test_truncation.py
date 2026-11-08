# -*- coding: utf-8 -*-
"""扫描左缘截断登记(1032 专项):判据来自原图像素,不靠数值猜测。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np

from src.table.truncation import (CUT_INK_MIN, column_frame_present, cut_ink,
                                  depth_chain_evidence, scan_left_cut)


def _fake_gray(rows):
    """rows = [(y0,y1,是否有贴边墨)] → 合成灰度图(宽 120,左缘 0..5 是裁切线)。"""
    H = max(b for _, b, _ in rows) + 20
    g = np.full((H, 120), 255, np.uint8)
    for y0, y1, cut in rows:
        g[y0 + 4:y1 - 4, 40:90] = 40          # 数字本体
        if cut:
            g[y0 + 4:y1 - 4, 0:4] = 40        # 贴边残笔画
    return g


def test_cut_ink_只数贴边墨():
    """贴边墨 = 裁切线左侧 x<CUT_EDGE_W 内的暗像素;离边的数字本体不算。"""
    g = np.full((100, 120), 255, np.uint8)
    g[10:40, 40:90] = 40                       # 只有本体
    assert cut_ink(g, 10, 40, 0, 100) == 0
    g[10:40, 0:4] = 40                         # 加贴边残笔画
    assert cut_ink(g, 10, 40, 0, 100) > 0


def test_scan_left_cut_按行给判定():
    """逐行判:贴边墨 >= CUT_INK_MIN 记截断,否则干净。"""
    g = _fake_gray([(100, 200, True), (200, 300, False), (300, 400, True)])
    out = scan_left_cut(g, [100, 200, 300, 400], 0, 100)
    assert [o["截断"] for o in out] == [True, False, True]
    assert all(o["贴边墨"] >= CUT_INK_MIN for o in out if o["截断"])
    assert all(o["贴边墨"] < CUT_INK_MIN for o in out if not o["截断"])


def test_scan_left_cut_跳过太薄的行():
    """行高不足 MIN_ROW_H 的格不判(分不清是数字还是格线)。"""
    g = _fake_gray([(100, 106, True)])
    out = scan_left_cut(g, [100, 106], 0, 100)
    assert out == []


def test_depth_chain_证据链只认小数位一致():
    """数值侧旁证:读串是推算值的"小数位一致、整数位丢失"时算支持截断。

    这不是主判据(有巧合,如 14.39 vs 4.39 小数位也一致),只作像素判定的交叉印证。
    """
    # 首行没有上一行可比,不产证据(链式旁证天然从第二行起)
    rows = [(4, 55.17, 46.76), (5, 9.14, 3.97), (6, 0.84, 41.7), (7, 14.39, 3.55)]
    ev = depth_chain_evidence(rows)
    assert len(ev) == 3
    assert ev[0]["推算"] == 59.14 and ev[0]["支持"] is True    # 9.14 vs 59.14
    assert ev[1]["推算"] == 50.84 and ev[1]["支持"] is True    # 0.84 vs 50.84
    # 14.39 vs 4.39 小数位也一致,属巧合——所以它只能是旁证,不能当主判据
    assert ev[2]["推算"] == 4.39
    assert all("推算" in e and "差" in e for e in ev)

def test_column_frame_present_整列裁切():
    """1032 实测:深度列左框整条不存在,全图没有一列暗色占比 >0.5。

    这是整列级判据(比逐行数贴边墨稳):原图有框线时该列暗占比接近 1;
    整列被裁掉时只剩零散噪点(实测 0.05~0.08)。
    """
    g = np.full((1000, 200), 255, np.uint8)
    assert column_frame_present(g, [100, 900], 0) is False
    g[:, 0:3] = 40                              # 加上一条贯穿竖线
    assert column_frame_present(g, [100, 900], 0) is True
    g[:, 0:3] = 255
    g[100:900, 0:3] = 40
    g[100:900, 0:3][::7] = 255                  # 只剩 86% 的断续墨,仍算有
    assert column_frame_present(g, [100, 900], 0) is True
