# -*- coding: utf-8 -*-
"""layout:布局推导与断口的确定性生成。"""
import numpy as np

from src.synth.layout import make_layout, sample_polyline


def test_vertical_line_count_and_positions(small_spec):
    lay = make_layout(np.random.default_rng(7), small_spec)
    # 左框 + 2 内部列线 + 右框 = 4 条竖线
    assert len(lay.col_xs) == 4
    assert lay.col_xs[1] - lay.col_xs[0] == 160  # gap[0]
    by_id = {ln.line_id: ln for ln in lay.lines}
    for i, x in enumerate(lay.col_xs):
        ln = by_id[f"col_{i}"]
        assert ln.polyline[0][0] == x
        assert ln.role == ("frame_side" if i in (0, len(lay.col_xs) - 1) else "column")


def test_roles_and_gray(small_spec):
    lay = make_layout(np.random.default_rng(7), small_spec)
    roles = {ln.role for ln in lay.lines}
    assert {"column", "row", "frame_tb", "frame_side", "deco"} <= roles
    faint = [ln for ln in lay.lines if ln.gray == small_spec.FAINT_GRAY]
    # 淡线须过管线 5t 墨闸(<180,30张真图线芯最淡≈100~130 实测推得 FAINT_GRAY=130),
    # 又须比正常墨(INK_GRAY=60)淡
    assert faint and all(small_spec.INK_GRAY < ln.gray < 180 for ln in faint)


def test_breaks_inside_line_and_deterministic(small_spec):
    lay1 = make_layout(np.random.default_rng(7), small_spec)
    lay2 = make_layout(np.random.default_rng(7), small_spec)
    assert [(ln.line_id, ln.breaks) for ln in lay1.lines] == \
           [(ln.line_id, ln.breaks) for ln in lay2.lines]
    for ln in lay1.lines:
        (x0, y0), (x1, y1) = ln.polyline[0], ln.polyline[-1]
        length = abs(y1 - y0) if y1 != y0 else abs(x1 - x0)
        for s0, s1 in ln.breaks:
            assert 0 <= s0 < s1 <= length


def test_sample_polyline_steps():
    pts = sample_polyline([(10, 0), (10, 100)], step=25)
    assert pts[0] == (10, 0) and pts[-1] == (10, 100)
    assert len(pts) == 5
