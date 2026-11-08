# -*- coding: utf-8 -*-
"""点→折线距离(段投影)与偏差统计。"""
import numpy as np

from src.verify.polyline_metrics import dev_stats, points_to_polyline_dist


def test_distance_to_vertical_segment():
    poly = np.array([[10, 0], [10, 100]], np.float64)
    q = np.array([[10, 50], [15, 50], [10, -5], [0, 0]], np.float64)
    d = points_to_polyline_dist(q, poly)
    assert np.allclose(d, [0, 5, 5, 10])


def test_distance_to_bend_uses_projection():
    poly = np.array([[0, 0], [10, 0], [10, 10]], np.float64)
    q = np.array([[5, -3], [13, 5]], np.float64)
    d = points_to_polyline_dist(q, poly)
    assert np.allclose(d, [3, 3])


def test_dev_stats_percentiles():
    d = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 100], np.float64)
    s = dev_stats(d)
    assert s["p50"] == 4.5 and abs(s["p95"] - 58.6) < 1e-9 and s["max"] == 100
    empty = dev_stats(np.array([], np.float64))
    assert empty == {"p50": None, "p95": None, "max": None, "n": 0}
