# -*- coding: utf-8 -*-
"""段拼接（_stitch_segments/_stitch_lines）单测：同线顺序段合 1、同线 y 重叠段合并、
真平行双线分离、跨缺口同线桥接、异线跳变不桥、suspect 不参与。"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.table.column_fit import _stitch_segments


def _mk(seg_id, x0, y0, x1, y1, direction="vertical", label="high"):
    """构造一条线段 dict（纵向为主；points/bbox 与真实候选一致）。"""
    bbox = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
    pts = [[int(x0), int(y0)], [int(x1), int(y1)]]
    return {
        "id": seg_id,
        "label": label,
        "direction": direction,
        "length": 100.0,
        "direct_ratio": 1.0,
        "angle": 90.0 if direction == "vertical" else 0.0,
        "pca_angle": 90.0 if direction == "vertical" else 0.0,
        "bbox": bbox,
        "midx": float((x0 + x1) / 2),
        "midy": float((y0 + y1) / 2),
        "points": pts,
    }


def _wrap(lines):
    """把 line dict 包装成 _stitch_segments 期望的成员格式 [{"line": m}]。"""
    return [{"line": ln} for ln in lines]


def test_same_line_sequential_segments_stitch():
    """同一条竖直线的顺序碎片（x 一致、y 相接）应拼接为一条轨迹。"""
    a = _mk(0, 100, 100, 100, 400)
    b = _mk(1, 100, 400, 100, 800)   # 端点相接，x 相同
    traj = _stitch_segments(_wrap([a, b]), "vertical")
    assert len(traj) >= 2
    ys = [p[1] for p in traj]
    xs = [p[0] for p in traj]
    assert min(ys) <= 100.0 and max(ys) >= 800.0   # 端点闭合覆盖两段全范围
    assert all(abs(x - 100.0) < 1e-6 for x in xs)  # 轨迹贴合 x=100


def test_parallel_overlapping_segments_not_stitch():
    """平行且 y 重叠的两条线（x 差远超容差）不应拼接成一条（取最长 run）。"""
    a = _mk(0, 100, 100, 100, 2000)   # 主线
    b = _mk(1, 260, 300, 260, 1500)   # 平行线，x 差 160px >> BRIDGE_PERP_TOL(100)
    traj = _stitch_segments(_wrap([a, b]), "vertical")
    assert len(traj) >= 2
    xs = [p[0] for p in traj]
    # 应只沿主线（x≈100）走，不被平行线带偏
    assert all(abs(x - 100.0) < 5.0 for x in xs)


def test_overlap_same_line_merged():
    """同一条渐倾列线的相邻碎片段（y 轻微重叠、off 差 <= 容差）应合并为一条。

    这是方案 A 判据精确化的核心场景：1015 x_ref=801 簇 off 771->879 连续渐变，
    y 有重叠但属于同一条线，旧判据（y 重叠必拆）会开出多条假 lane。
    """
    # 两段 y 重叠（a 贯穿 100-2000，b 从 900-1700，x 差 10px 在容差内）
    a = _mk(0, 100, 100, 100, 2000)
    b = _mk(1, 110, 900, 110, 1700)   # 与 a y 重叠，off 差 10px < 容差
    traj = _stitch_segments(_wrap([a, b]), "vertical")
    ys = [p[1] for p in traj]
    # 应合并为一条贯穿全高的轨迹
    assert min(ys) <= 100.0 + 1e-6
    assert max(ys) >= 2000.0 - 1e-6


def test_true_parallel_split():
    """真正平行双线（y 全程重叠、off 差 > 容差）应拆为两条轨迹（_stitch_lines 多 lane）。"""
    from src.table.column_fit import _stitch_lines
    a = _mk(0, 100, 100, 100, 2000)   # 主线 x=100
    b = _mk(1, 300, 100, 300, 2000)   # 平行线 x=300，off 差 200px > 容差(100)
    lines = _stitch_lines(_wrap([a, b]), "vertical")
    # 两条 y 全程重叠但 x 明显不同的真线应各自成 lane
    assert len(lines) == 2
    for t in lines:
        xs = [p[0] for p in t]
        assert min(xs) == max(xs)  # 每条 lane 轨迹 x 恒定（垂直）


def test_large_gap_bridged():
    """同一列线的大断口（gap <= BRIDGE_MAX_GAP，x 差小）应被线性桥接。"""
    a = _mk(0, 100, 100, 100, 400)
    b = _mk(1, 100, 900, 100, 1300)   # y 断口 500px，x 相同
    traj = _stitch_segments(_wrap([a, b]), "vertical")
    ys = [p[1] for p in traj]
    xs = [p[0] for p in traj]
    assert max(ys) >= 1300.0
    # 断口内应有插值点（不跳变），且 x 保持 100
    assert any(400.0 < y < 900.0 for y in ys)
    assert all(abs(x - 100.0) < 1e-6 for x in xs)


def test_over_gap_bridged_same_line_trend():
    """断口 gap > BRIDGE_MAX_GAP 但两侧同线趋势一致（x 相同/渐倾连续）应被桥接。

    方案 A 目标：跨大断口的同一条渐倾列线（如 1035 col1 的 y4467-8403 断口）
    应缝合为一条贯穿全高轨迹，而不是只取最长 run。
    """
    a = _mk(0, 100, 100, 100, 400)
    b = _mk(1, 100, 1500, 100, 1900)  # y 断口 1100px > 500px，但 x 相同（同线）
    traj = _stitch_segments(_wrap([a, b]), "vertical")
    ys = [p[1] for p in traj]
    xs = [p[0] for p in traj]
    # 同线趋势一致：轨迹应覆盖两 run 全范围且 x 保持 100
    assert min(ys) <= 100.0 + 1e-6
    assert max(ys) >= 1900.0 - 1e-6
    assert all(abs(x - 100.0) < 1e-6 for x in xs)


def test_parallel_overlap_not_bridged():
    """真正平行双线（y 重叠且 off 差超容差）不应被桥接成一条。"""
    a = _mk(0, 100, 100, 100, 1900)   # 主线 x=100 贯穿
    b = _mk(1, 300, 400, 300, 1600)   # 平行线 x=300，off 差 200px > 容差
    traj = _stitch_segments(_wrap([a, b]), "vertical")
    ys = [p[1] for p in traj]
    xs = [p[0] for p in traj]
    # 主线（最长 lane）应沿 x=100，不被平行线带偏
    assert min(ys) <= 100.0 + 1e-6
    assert max(ys) >= 1900.0 - 1e-6
    assert all(abs(x - 100.0) < 5.0 for x in xs)


def test_suspect_not_stitched():
    """suspect 段不参与拼接。"""
    a = _mk(0, 100, 100, 100, 400)
    b = _mk(1, 100, 400, 100, 800, label="suspect")
    traj = _stitch_segments(_wrap([a, b]), "vertical")
    assert max(p[1] for p in traj) <= 400.0 + 1e-6
