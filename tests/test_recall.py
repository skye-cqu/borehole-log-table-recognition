# -*- coding: utf-8 -*-
"""Step 0 noise 再召回判据单测。"""
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.table.column_fit import recall_noise


def test_recall_noop_for_non_noise(make_line):
    """非 noise 段不被改动。"""
    lines = [make_line(label="high", line_id=0), make_line(label="suspect", line_id=1)]
    out, stats = recall_noise(lines)
    assert out[0]["label"] == "high"
    assert out[1]["label"] == "suspect"
    assert stats["recall_count"] == 0
    assert stats["misabsorb_none"] == 0


def test_recall_none_direction_never_recalled(make_line):
    """direction==none 的 noise 绝不被召回（误吸检查）。"""
    lines = [make_line(label="noise", direction="none", length=200.0,
                       direct_ratio=1.0, midx=100.0, midy=100.0, line_id=0)]
    out, stats = recall_noise(lines)
    assert out[0]["label"] == "noise"
    assert stats["recall_count"] == 0
    assert stats["misabsorb_none"] == 0


def test_recall_short_noise_not_recalled(make_line):
    """长度不足的 noise 不召回（< RECALL_MIN_LEN）。"""
    lines = [make_line(label="noise", direction="vertical", length=20.0,
                       direct_ratio=1.0, midx=100.0, midy=100.0, line_id=0)]
    out, stats = recall_noise(lines)
    assert out[0]["label"] == "noise"
    assert stats["recall_count"] == 0


def test_recall_near_high_trajectory(make_line):
    """靠近 high 轨迹、方向明确、长度/几何合格的 noise 被召回为 high。"""
    lines = [
        make_line(label="high", direction="vertical", length=200.0,
                  direct_ratio=1.0, midx=100.0, midy=50.0, line_id=0),
        make_line(label="noise", direction="vertical", length=80.0,
                  direct_ratio=0.9, midx=102.0, midy=150.0, line_id=1),
    ]
    out, stats = recall_noise(lines)
    assert out[1]["label"] == "high"
    assert stats["recall_count"] == 1
    # 几何不动
    assert out[1]["points"] == lines[1]["points"]


def test_recall_far_noise_not_recalled(make_line):
    """远离任何 high 轨迹的 noise 不召回（位置判据不满足）。"""
    lines = [
        make_line(label="high", direction="vertical", length=200.0,
                  direct_ratio=1.0, midx=100.0, midy=50.0, line_id=0),
        make_line(label="noise", direction="vertical", length=80.0,
                  direct_ratio=0.9, midx=500.0, midy=150.0, line_id=1),
    ]
    out, stats = recall_noise(lines)
    assert out[1]["label"] == "noise"
    assert stats["recall_count"] == 0


def test_recall_struct_signal_crossing(make_line):
    """位置不满足但 crossing_count>0 的结构信号可补足召回。"""
    lines = [
        make_line(label="high", direction="horizontal", length=200.0,
                  direct_ratio=1.0, midx=50.0, midy=100.0, line_id=0),
        make_line(label="noise", direction="horizontal", length=60.0,
                  direct_ratio=0.8, midx=300.0, midy=100.0,
                  crossing_count=2, line_id=1),
    ]
    out, stats = recall_noise(lines)
    # 位置远（midy 相同但 midx 远），靠 crossing 结构信号 + 长度/几何补足 4 信号
    assert out[1]["label"] == "high"
    assert stats["recall_count"] == 1
