# -*- coding: utf-8 -*-
"""track_group 单测（合成墨迹图）：同线碎片跨行线+断口归一条 Track、
邻线不吸、方向不符不接、输入线段冻结不变、跳距随倾角封顶。"""
import copy
import math
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.table.track_group import PARAMS, _max_jump, _dir_down, build_tracks


def _mk(seg_id, top, bot):
    """按 track_group 的段结构构造最小段 dict（两点 RDP）。"""
    top = np.asarray(top, float)
    bot = np.asarray(bot, float)
    return {
        "id": seg_id,
        "top": top,
        "bot": bot,
        "v_top": _dir_down(top, bot),
        "v_bot": _dir_down(bot, top),
        "orig_points": [[int(top[0]), int(top[1])], [int(bot[0]), int(bot[1])]],
    }


def _synth_ink():
    """160x640 合成墨迹：竖线 x=80（三段，含行线交叉与 30px 断口）、
    邻线 x=120（40px 外）、45° 斜线（方向不符）。"""
    img = np.full((640, 160), 255, np.uint8)
    cv2.line(img, (80, 20), (80, 246), 0, 3)      # F1
    cv2.line(img, (0, 251), (160, 251), 0, 3)     # 行线（横穿）
    cv2.line(img, (80, 255), (80, 298), 0, 3)     # F2
    # y 299..329 为断口（无墨）
    cv2.line(img, (82, 330), (78, 598), 0, 3)     # F3（微倾斜）
    cv2.line(img, (120, 250), (120, 400), 0, 3)   # DECOY 邻线
    cv2.line(img, (78, 615), (108, 645), 0, 3)    # SKEW 45° 斜线
    return img < 128


def _segments():
    return [
        _mk(1, (80, 20), (80, 246)),
        _mk(2, (80, 255), (80, 298)),
        _mk(3, (82, 330), (78, 598)),
        _mk(4, (120, 250), (120, 400)),
        _mk(5, (78, 615), (108, 645)),
    ]


def test_same_line_one_track():
    """同线三碎片（跨行线+跨断口）归同一条 Track；邻线/斜线不进。"""
    segs = _segments()
    tracks, unassigned = build_tracks(segs, _synth_ink(), PARAMS)
    main = next(t for t in tracks if 1 in t["segment_ids"])
    assert main["segment_ids"] == [1, 2, 3]
    assert not any(sid in main["segment_ids"] for sid in (4, 5))
    # 全部碎片都有归属（各自成 Track），且无重复归属
    flat = [sid for t in tracks for sid in t["segment_ids"]]
    assert sorted(flat) == [1, 2, 3, 4, 5]
    assert len(flat) == len(set(flat))
    assert unassigned == []


def test_cross_row_line_not_a_jump():
    """跨行线的相接碎片 gap_y=9、无死推（jump_px=0）。"""
    segs = _segments()
    tracks, _ = build_tracks(segs, _synth_ink(), PARAMS)
    main = next(t for t in tracks if 1 in t["segment_ids"])
    lk = main["links"][0]
    assert lk["from_id"] == 1 and lk["to_id"] == 2
    assert lk["gap_y"] == 9.0 and lk["jump_px"] == 0


def test_gap_jump_evidence():
    """断口以死推跳接：跳距≈断口宽、横向 ≤ tol_land、方向差小。"""
    segs = _segments()
    tracks, _ = build_tracks(segs, _synth_ink(), PARAMS)
    main = next(t for t in tracks if 1 in t["segment_ids"])
    lk = main["links"][1]
    assert lk["from_id"] == 2 and lk["to_id"] == 3
    assert 20 <= lk["jump_px"] <= 34
    assert lk["land_lateral_px"] <= PARAMS["tol_land"]
    assert lk["dir_diff_deg"] <= PARAMS["dir_tol_deg"]


def test_skew_not_attached():
    """45° 斜线方向不符（>dir_tol），绝不接进主 Track。"""
    segs = _segments()
    tracks, _ = build_tracks(segs, _synth_ink(), PARAMS)
    main = next(t for t in tracks if 1 in t["segment_ids"])
    assert 5 not in main["segment_ids"]


def _canonical(segs):
    """numpy 数组转 list，便于逐字段比较。"""
    return [{k: (v.tolist() if isinstance(v, np.ndarray) else v)
             for k, v in s.items()} for s in segs]


def test_segments_frozen():
    """归组过程只读：输入段 dict 任何字段不得被修改。"""
    segs = _segments()
    before = _canonical(copy.deepcopy(segs))
    build_tracks(segs, _synth_ink(), PARAMS)
    assert _canonical(segs) == before


def test_max_jump_tilt_cap():
    """跳距封顶：倾角越大跳距越短，横向漂移 ≤ drift_max。"""
    rad = math.radians(10)
    d = np.array([math.sin(rad), math.cos(rad)])
    assert _max_jump(d, PARAMS) == int(PARAMS["drift_max"] / math.tan(rad))
    assert _max_jump(np.array([0.0, 1.0]), PARAMS) == PARAMS["gap_max"]
