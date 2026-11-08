# -*- coding: utf-8 -*-
"""render:画出的线在采样点上必须有墨,断口必须白,底必须白。

判据说明:断口区域(全版式所有断口,含他线断口波及)严格 =255;
非断口采样点只验"有墨"(≤200)——交叉处后画的线可能更淡(淡行线盖墨列线),
灰度保真由判分器几何层兜底,此处判"画没画"不判"画多黑"。
"""
import numpy as np

from src.synth.layout import make_layout, point_in_breaks, sample_polyline
from src.synth.render import render_clean


def test_lines_dark_breaks_white_background_white(small_spec):
    lay = make_layout(np.random.default_rng(3), small_spec)
    img = render_clean(lay)
    assert img.shape == (1200, 800) and img.dtype == np.uint8
    assert (img[5, 5] == 255)  # 无人区=纸白
    h, w = img.shape
    checked = 0
    for ln in lay.lines:
        (x0, y0), (x1, y1) = ln.polyline[0], ln.polyline[-1]
        vertical = y1 != y0
        length = (y1 - y0) if vertical else (x1 - x0)
        for s in range(0, int(length) - 1, 37):
            x, y = (x0, y0 + s) if vertical else (x0 + s, y0)
            if not (0 <= x < w and 0 <= y < h):
                continue
            v = img[y, x]
            if point_in_breaks(lay, x, y):
                assert v == 255, (ln.line_id, s, v)
            else:
                assert v <= 200, (ln.line_id, s, v)
            checked += 1
    assert checked > 100


def test_band_dark(small_spec):
    lay = make_layout(np.random.default_rng(3), small_spec)
    img = render_clean(lay)
    x0, x1 = lay.blocks[0].geometry
    assert (img[600, (x0 + x1) // 2] <= 60)
