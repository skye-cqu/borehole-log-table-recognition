# -*- coding: utf-8 -*-
"""碎片拼接（merge_fragments）单测：端点连通 + 共线判断 + 并查集。"""
import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.table.column_fit import merge_fragments


def _mk(seg_id, direction, x0, y0, x1, y1, label="high", angle=None):
    """构造一条线段 dict（方向明确、几何可控）。"""
    bbox = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
    pts = [[int(x0), int(y0)], [int(x1), int(y1)]]
    if angle is None:
        angle = 90.0 if direction == "vertical" else 0.0
    return {
        "id": seg_id,
        "label": label,
        "direction": direction,
        "length": float(np.hypot(x1 - x0, y1 - y0)),
        "direct_ratio": 1.0,
        "angle": angle,
        "pca_angle": angle,
        "bbox": bbox,
        "midx": float((x0 + x1) / 2),
        "midy": float((y0 + y1) / 2),
        "points": pts,
    }


# ---------------- 端到端拼接 ----------------
def test_sequential_fragments_merge():
    """同一列线的顺序碎片（端点相接）应合并为一条线。"""
    a = _mk(0, "vertical", 100, 100, 100, 200)
    b = _mk(1, "vertical", 101, 200, 100, 300)   # 端点 (100,200)-(101,200) 相距 1px
    merged = merge_fragments([a, b])
    assert len(merged) == 1
    assert set(merged[0]["member_ids"]) == {0, 1}


def test_gap_over_60px_not_merge():
    """端点主轴间距 > MERGE_MAIN_GAP(60px) 的碎片不应合并（真断口）。"""
    a = _mk(0, "vertical", 100, 100, 100, 200)
    b = _mk(1, "vertical", 100, 280, 100, 380)   # 主轴间距 80px > 60px
    merged = merge_fragments([a, b])
    assert len(merged) == 2


def test_competitive_matching_nearest_wins():
    """竞争性匹配：两个前驱竞争同一后继时，垂直偏移更小者胜出。

    模拟 x=281 内部线与 x=301 分隔线竞争 x=302.5 后继的场景：
    近者(x=301, 偏移1.5)应胜出，远者(x=281, 偏移21.5)链条断开。
    """
    a = _mk(0, "vertical", 281, 1000, 281, 13868)     # 内部线（终点 y=13868）
    b = _mk(1, "vertical", 301, 1000, 301, 13868)     # 分隔线（终点 y=13868, 距后继近）
    c = _mk(2, "vertical", 302, 13868, 302, 15000)    # 被竞争的后继（起点 y=13868）
    merged = merge_fragments([a, b, c])
    # b 和 c 应合并（偏移 1px），a 独立
    b_line = [ml for ml in merged if 1 in ml["member_ids"]]
    assert len(b_line) == 1
    assert set(b_line[0]["member_ids"]) == {1, 2}
    a_line = [ml for ml in merged if 0 in ml["member_ids"]]
    assert len(a_line) == 1
    assert a_line[0]["num_members"] == 1


# ---------------- 平行线段不合并 ----------------
def test_overlapping_parallel_fragments_not_merge():
    """平行但相邻的线段（不同列线，间距 20-40px）不应合并。

    旧判据"重叠即合并"会在碎片密集区把相邻列线误并成贯穿全表的巨型线。
    """
    a = _mk(0, "vertical", 281, 13000, 281, 15000)
    b = _mk(1, "vertical", 310, 13500, 310, 15500)  # 平行、y 重叠、x 差 29px
    merged = merge_fragments([a, b])
    assert len(merged) == 2


def test_tilted_sequential_fragments_merge():
    """倾斜列线的顺序碎片（连接处偏移 <25px）应合并。"""
    a = _mk(0, "vertical", 443, 100, 443, 4258)
    b = _mk(1, "vertical", 455, 4277, 455, 5901)  # 连接处 x 差 12px, y 间距 19px
    merged = merge_fragments([a, b])
    assert len(merged) == 1
    assert set(merged[0]["member_ids"]) == {0, 1}


def test_far_parallel_fragments_not_merge():
    """平行但相距 >50px 的碎片（不同列线）不应合并。"""
    a = _mk(0, "vertical", 281, 100, 281, 300)
    b = _mk(1, "vertical", 345, 150, 345, 350)  # x 差 64px > 50px
    merged = merge_fragments([a, b])
    assert len(merged) == 2


# ---------------- 不参与的类型 ----------------
def test_suspect_not_participating():
    """suspect 段不参与拼接，即使端点与 high 段相接。"""
    a = _mk(0, "vertical", 100, 100, 100, 200, label="high")
    b = _mk(1, "vertical", 100, 200, 100, 300, label="suspect")
    merged = merge_fragments([a, b])
    assert len(merged) == 1
    assert merged[0]["member_ids"] == [0]


def test_direction_none_not_participating():
    """direction==none 的段永不参与拼接。"""
    a = _mk(0, "vertical", 100, 100, 100, 200)
    b = _mk(1, "none", 100, 200, 100, 300)
    merged = merge_fragments([a, b])
    assert len(merged) == 1
    assert merged[0]["member_ids"] == [0]


def test_cross_direction_not_merge():
    """纵向与横向段不合并（按方向分流）。"""
    v = _mk(0, "vertical", 100, 100, 100, 300)
    h = _mk(1, "horizontal", 50, 200, 300, 200)
    merged = merge_fragments([v, h])
    assert len(merged) == 2
    axes = {ml["axis"] for ml in merged}
    assert axes == {"vertical", "horizontal"}


# ---------------- 链式传递 ----------------
def test_chain_connectivity():
    """A-B 相接、B-C 相接但 A-C 相距远，三者应通过传递合并为一条线。"""
    a = _mk(0, "vertical", 100, 100, 100, 200)
    b = _mk(1, "vertical", 100, 200, 100, 300)   # 接 A
    c = _mk(2, "vertical", 100, 300, 100, 400)   # 接 B，A-C 相距 200px
    merged = merge_fragments([a, b, c])
    assert len(merged) == 1
    assert set(merged[0]["member_ids"]) == {0, 1, 2}


# ---------------- 合并线几何 ----------------
def test_merged_line_geometry():
    """合并后的线应覆盖成员的主轴全范围（y_span/bbox）。"""
    a = _mk(0, "vertical", 100, 100, 100, 200)
    b = _mk(1, "vertical", 100, 200, 100, 500)
    merged = merge_fragments([a, b])
    assert len(merged) == 1
    ml = merged[0]
    assert ml["bbox"][1] == 100.0
    assert ml["bbox"][3] == 500.0
    assert ml["y_span"] == 400.0
    # 轨迹应覆盖 [100, 500]
    ys = [p[1] for p in ml["trajectory"]]
    assert min(ys) <= 105.0 and max(ys) >= 495.0


# ---------------- 真实数据 ----------------
def test_real_1015_no_giant_line(sample_data):
    """1015 真实数据：不应出现成员数 >500 的巨型合并线（过度合并已修复）。"""
    lines = sample_data["lines"]
    merged = merge_fragments(lines)
    giants = [ml for ml in merged if ml["num_members"] > 500]
    assert not giants, f"存在巨型合并线: {[(ml['id'], ml['num_members']) for ml in giants]}"


def test_real_1015_sequential_chains_merge(sample_data):
    """1015 真实数据：同一列线的顺序碎片应合并成较长的线。"""
    lines = sample_data["lines"]
    merged = merge_fragments(lines)
    mv = [ml for ml in merged if ml["axis"] == "vertical"]
    # 应有至少 10 条 y_span > 5000 的合并线（列线碎片链）
    long_lines = [ml for ml in mv if ml["y_span"] > 5000]
    assert len(long_lines) >= 10, f"长合并线只有 {len(long_lines)} 条"


def test_real_1015_merge_reduces_count(sample_data):
    """1015 真实数据：合并后线数显著减少，且大部分段被并入多成员线。"""
    lines = sample_data["lines"]
    merged = merge_fragments(lines)
    n_vertical_in = sum(1 for l in lines
                        if l.get("direction") == "vertical" and l.get("label") != "suspect")
    n_merged_v = sum(1 for ml in merged if ml["axis"] == "vertical")
    assert n_merged_v < n_vertical_in / 2, \
        f"纵向合并线 {n_merged_v} 应明显少于输入段 {n_vertical_in}"
    # 大部分段应被合并进多成员线（单例多为文字笔画噪声）
    n_in_multi = sum(ml["num_members"] for ml in merged
                     if ml["axis"] == "vertical" and ml["num_members"] > 1)
    assert n_in_multi > n_vertical_in * 0.6, \
        f"仅 {n_in_multi/n_vertical_in*100:.0f}% 的输入段被合并"
