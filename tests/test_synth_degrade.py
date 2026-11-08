# -*- coding: utf-8 -*-
"""warp:GT 点经同一位移场映射后,必须落在弯曲图的黑线上(往返自检)。"""
import numpy as np

from src.synth.degrade import WarpParams, apply_warp, warp_point, warp_polyline
from src.synth.layout import make_layout, point_in_breaks, sample_polyline
from src.synth.render import render_clean


def test_warp_point_matches_remap(small_spec):
    lay = make_layout(np.random.default_rng(5), small_spec)
    img = render_clean(lay)
    wp = WarpParams(amp1=14, wl1=500.0, ph1=0.3, amp2=5, wl2=170.0, ph2=1.1, tilt=8.0)
    warped = apply_warp(img, wp)
    h, w = warped.shape
    checked = 0
    for ln in lay.lines:
        if ln.breaks:
            continue
        for (x, y) in sample_polyline(list(ln.polyline), step=20):
            wx, wy = warp_point(x, y, wp, img.shape)
            ix, iy = int(round(wx)), int(round(wy))
            if not (0 <= ix < w and 0 <= iy < h):
                continue  # 出画布的 GT 点(如小样装饰框)不参与自检
            if point_in_breaks(lay, x, y):
                continue  # 他线断口置白波及处不判墨
            v = warped[iy, ix]
            assert v <= 200, (ln.line_id, x, y, wx, wy, v)
            checked += 1
    assert checked > 100


def test_warp_polyline_equals_map_points(small_spec):
    wp = WarpParams(amp1=10, wl1=400.0, ph1=0.0, amp2=0, wl2=100.0, ph2=0.0, tilt=0.0)
    pts = [(100, 0), (100, 300)]
    out = warp_polyline(pts, wp, (1200, 800))
    for (px, py), (qx, qy) in zip(pts, out):
        assert (qx, qy) == warp_point(px, py, wp, (1200, 800))


def test_zero_warp_is_identity():
    wp = WarpParams(0, 100.0, 0.0, 0, 100.0, 0.0, 0.0)
    assert warp_point(123, 456, wp, (1200, 800)) == (123.0, 456.0)


def test_photometric_deterministic_and_soft(small_spec):
    from src.synth.degrade import PhotoParams, apply_photometric
    lay = make_layout(np.random.default_rng(5), small_spec)
    img = render_clean(lay)
    pp = PhotoParams(blur_sigma=1.0, noise_sigma=4.0, bleed=True, lighting=True)
    out1 = apply_photometric(img, np.random.default_rng(9), pp)
    out2 = apply_photometric(img, np.random.default_rng(9), pp)
    assert np.array_equal(out1, out2)            # 同 seed 确定性
    assert out1.dtype == np.uint8
    assert out1.std() > img.std() or out1.mean() < img.mean()  # 确实变了
    # 结构仍可辨:列线采样点仍显著暗于背景中位
    col = [ln for ln in lay.lines if ln.line_id == "col_0"][0]
    vals = [out1[y, x] for x, y in sample_polyline(list(col.polyline), step=60)]
    assert np.median(vals) < 160
