# -*- coding: utf-8 -*-
"""row_line_detect 纯算法单测（合成图，无文件依赖）。"""
import numpy as np

from src.table.row_line_detect import (
    col_run_centers, nearest_per_col, projection_candidates, detrend,
    dp_refine, support_mask, extract_spans, trace_strip_lines)

BG, INK = 230, 80


def band(h=600, w=400):
    return np.full((h, w), BG, np.uint8)


def draw_rule(img, y, x0=0, x1=None, t=3):
    img[y:y + t, x0:img.shape[1] if x1 is None else x1] = INK


def gray_of(dark):
    return np.where(dark, INK, BG).astype(np.uint8)


def test_col_run_centers():
    d = np.zeros((5, 3), bool)
    d[1:3, 0] = True
    d[4, 2] = True
    c, ys, ln = col_run_centers(d)
    assert list(c) == [0, 2]
    assert ys[0] == 1.5 and ys[1] == 4.0
    assert list(ln) == [2, 1]


def test_nearest_per_col():
    cols = np.array([0, 0, 1, 3])
    ys = np.array([10.0, 30.0, 12.0, 50.0])
    c, dy = nearest_per_col(cols, ys, 20.0, 15)
    assert 0 in c.tolist() and 1 in c.tolist() and 3 not in c.tolist()
    assert dy[list(c).index(0)] == -10.0 and dy[list(c).index(1)] == -8.0


def test_projection_candidates_rules_vs_text():
    """规则线成候选；文字行（短笔画、行占比~0.2）不成为候选。"""
    img = band(600, 400)
    for y in (100, 200, 300):
        draw_rule(img, y)
    for x in range(0, 400, 20):
        img[400:430, x:x + 4] = INK  # 文字行模拟：竖笔画 pitch 20、宽 4
    cands = projection_candidates(img < 190, strip_w=400)
    vs = sorted(c['v'] for c in cands)
    assert len(vs) == 3
    for v, y in zip(vs, (100, 200, 300)):
        assert abs(v - y) <= 2
        assert next(c for c in cands if c['v'] == v)['thick'] == 3
    assert all(not 395 <= c['v'] <= 435 for c in cands)


def test_detrend_follows_tilt():
    """倾斜 0.06 px/px（≈3.4°）的行线：去倾趋势线误差 ≤4px。"""
    w = 400
    img = band(600, w)
    truth = np.array([151 + 0.06 * x for x in range(w)])
    for x in range(w):
        y = int(round(truth[x])) - 1
        img[y:y + 3, x] = INK
    xs = np.arange(w)
    y0, sup = detrend(img < 150, 163, xs)
    assert sup.any()
    assert np.abs(y0[sup] - truth[sup]).max() <= 4


def test_dp_follows_gentle_curve():
    """缓弯行线（全带宽 40px 正弦弯）：DP 路径误差 ≤4px。"""
    w = 800
    img = band(600, w)
    truth = np.array([301 + 20 * np.sin(2 * np.pi * x / 800) for x in range(w)])
    for x in range(w):
        y = int(round(truth[x])) - 1
        img[y:y + 3, x] = INK
    d = img < 150
    xs = np.arange(w)
    y0, _ = detrend(d, 301, xs)
    path = dp_refine(gray_of(d), y0, xs)
    assert np.abs(path - truth).max() <= 4


def test_dp_crosses_gap_and_support_splits():
    """80px 断口：DP 直穿且不跑偏；支持掩膜在断口断开 → 两个 span。"""
    w = 400
    img = band(600, w)
    draw_rule(img, 200)
    d = img < 150
    d[:, 150:230] = False
    xs = np.arange(w)
    y0, _ = detrend(d, 201, xs)
    path = dp_refine(gray_of(d), y0, xs)
    assert np.abs(path - 201.5).max() <= 4
    sup = support_mask(d, path, xs)
    assert not sup[155:225].any()
    assert sup[10:140].all() and sup[240:390].all()
    spans = extract_spans(xs, sup, path, d)
    assert len(spans) == 2
    assert spans[0]['u1'] <= 155 and spans[1]['u0'] >= 225


def test_partial_line_emits_single_span():
    """行线只存在左半带（rowspan 证据）：单 span，支持率 ≈0.4，不补造右半。"""
    w = 400
    img = band(600, w)
    draw_rule(img, 200, x1=160)
    d = img < 150
    xs = np.arange(w)
    cands = projection_candidates(d, strip_w=400)
    assert len(cands) == 1 and cands[0]['thick'] == 3
    lines, rejected = trace_strip_lines(d, gray_of(d), cands, n_cols=400, x0=0, v_off=0)
    assert len(lines) == 1 and not rejected
    ln = lines[0]
    assert ln['n_spans'] == 1
    sp = ln['spans'][0]
    assert sp['u0'] <= 5 and 150 <= sp['u1'] <= 165
    assert 0.3 <= ln['support_frac'] <= 0.5
