# -*- coding: utf-8 -*-
"""GT:双坐标折线、断口、单元格(含 rowspan)与落盘一致性。"""
import json

import numpy as np

from src.synth.degrade import WarpParams
from src.synth.layout import make_layout
from src.synth.make_gt import build_gt, save_gt


def test_gt_structure_and_warp_consistency(small_spec, tmp_path):
    lay = make_layout(np.random.default_rng(11), small_spec)
    wp = WarpParams(amp1=6, wl1=300.0, ph1=0.5, amp2=2, wl2=90.0, ph2=0.0, tilt=4.0)
    shape = (small_spec.height, small_spec.width)
    gt = build_gt(seed=11, lay=lay, warp_params=wp, photo_params=None, shape=shape)
    assert gt["schema"] == "synth_gate_gt_v1" and gt["seed"] == 11
    assert len(gt["cells"]) == 3 * 3 - 1   # 3行x3列,地质列 rowspan 合并 1 处
    for ln in gt["lines"]:
        assert len(ln["polyline_warp"]) == len(ln["polyline_ideal"])
    col0 = [l for l in gt["lines"] if l["line_id"] == "col_0"][0]
    assert col0["polyline_warp"] == warp_check(col0["polyline_ideal"], wp, shape)
    # 落盘往返
    p = save_gt(gt, tmp_path)
    assert json.loads(p.read_text(encoding="utf-8")) == gt


def warp_check(pts, wp, shape):
    from src.synth.degrade import warp_polyline
    return [list(q) for q in warp_polyline(pts, wp, shape)]
