# -*- coding: utf-8 -*-
"""GT 判分采样:双坐标逐点对应、断口标记与渲染置白几何互逆、断口四边形落账。"""
import cv2
import numpy as np

from src.synth.degrade import WarpParams
from src.synth.layout import make_layout
from src.synth.make_gt import build_gt


def _gt(small_spec):
    lay = make_layout(np.random.default_rng(11), small_spec)
    wp = WarpParams(amp1=6, wl1=300.0, ph1=0.5, amp2=2, wl2=90.0, ph2=0.0, tilt=4.0)
    return lay, build_gt(seed=11, lay=lay, warp_params=wp, photo_params=None,
                         shape=(small_spec.height, small_spec.width))


def test_samples_correspond(small_spec):
    lay, gt = _gt(small_spec)
    for ln, gl in zip(lay.lines, gt["lines"]):
        s_i, s_w, brk = (gl["samples_ideal"], gl["samples_warp"], gl["samples_in_break"])
        assert len(s_i) == len(s_w) == len(brk) >= 2
        assert tuple(s_i[0]) == ln.polyline[0] and tuple(s_i[-1]) == ln.polyline[-1]
        assert all(b in (0, 1) for b in brk)


def test_in_break_flag_matches_render_white(small_spec):
    from src.synth.layout import point_in_breaks
    lay, gt = _gt(small_spec)
    for gl in gt["lines"]:
        for (x, y), b in zip(gl["samples_ideal"], gl["samples_in_break"]):
            assert b == (1 if point_in_breaks(lay, x, y) else 0)


def test_break_quads_cover_break_span(small_spec):
    lay, gt = _gt(small_spec)
    n_quads = 0
    for gl in gt["lines"]:
        assert len(gl["breaks_scan_quad"]) == len(gl["breaks_ideal"])
        for quad in gl["breaks_scan_quad"]:
            assert len(quad) == 4
            pts = np.array(quad, np.float32).reshape(-1, 1, 2)
            assert cv2.contourArea(pts) > 0
            n_quads += 1
    assert n_quads > 0   # 小样 break_prob=1.0,必有断口
