# -*- coding: utf-8 -*-
"""几何度量:点到折线的精确距离(段投影法,非端点近似)与偏差分位数。"""
import numpy as np


def points_to_polyline_dist(qpts, poly) -> np.ndarray:
    """qpts (n,2) 到折线 poly (m,2) 的最小距离,段投影法(向量化,返回 (n,))。"""
    q = np.asarray(qpts, np.float64).reshape(-1, 1, 2)
    p0 = np.asarray(poly[:-1], np.float64).reshape(1, -1, 2)
    v = np.asarray(poly[1:], np.float64).reshape(1, -1, 2) - p0
    vv = (v * v).sum(-1)                       # (1,m)
    vv[vv == 0] = 1e-12
    t = ((q - p0) * v).sum(-1) / vv            # (n,m)
    t = np.clip(t, 0.0, 1.0)
    proj = p0 + t[..., None] * v
    d = np.sqrt(((q - proj) ** 2).sum(-1))     # (n,m)
    return d.min(axis=1)


def dev_stats(d) -> dict:
    """距离数组的 p50/p95/max/n;空数组返回 None 值(调用方按缺检处理)。"""
    d = np.asarray(d, np.float64)
    if d.size == 0:
        return {"p50": None, "p95": None, "max": None, "n": 0}
    return {"p50": float(np.percentile(d, 50)), "p95": float(np.percentile(d, 95)),
            "max": float(d.max()), "n": int(d.size)}
