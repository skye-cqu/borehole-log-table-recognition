# -*- coding: utf-8 -*-
"""记分卡:三族汇总、pass/fail、MD 渲染、落盘;矫正映射回映射的正确性。"""
import json

import numpy as np

from src.synth.degrade import WarpParams
from src.synth.layout import make_layout
from src.synth.make_gt import build_gt
from src.verify.gate_config import DEFAULT_THRESHOLDS as TH
from src.verify.score_vs_gt import apply_h_rect_to_src, render_md, score_seed


def _gt(small_spec):
    lay = make_layout(np.random.default_rng(11), small_spec)
    wp = WarpParams(amp1=6, wl1=300.0, ph1=0.5, amp2=2, wl2=90.0, ph2=0.0, tilt=4.0)
    return build_gt(seed=11, lay=lay, warp_params=wp, photo_params=None,
                    shape=(small_spec.height, small_spec.width))


def _ink(ln):
    smp = np.asarray(ln["samples_warp"], np.float64)
    brk = np.asarray(ln["samples_in_break"], bool)
    return smp[~brk]


def _pipeline_perfect(gt):
    def fam(role):
        return [_ink(ln) for ln in gt["lines"] if ln["role"] == role]
    sides = [_ink(ln) for ln in gt["lines"] if ln["role"] == "frame_side"]
    tb = [_ink(ln) for ln in gt["lines"] if ln["role"] == "frame_tb"]
    return {"columns": fam("column"),
            "sides": {"left": sides[0], "right": sides[-1],
                      "top": tb[0], "bottom": tb[-1]}}


def test_apply_h_rect_to_src_identity_and_shift():
    ident = np.eye(3)
    assert apply_h_rect_to_src(ident, [(3, 4)]) == [(3.0, 4.0)]
    h = np.array([[1, 0, 10], [0, 1, -5], [0, 0, 1]], np.float64)
    assert apply_h_rect_to_src(h, [(1, 1)]) == [(11.0, -4.0)]


def test_score_seed_perfect_pass(small_spec):
    gt = _gt(small_spec)
    card = score_seed(gt, _pipeline_perfect(gt), TH)
    assert card["pass"] is True
    for fam in ("columns", "sides", "frame_tb"):
        assert card["families"][fam]["missing"] == []
        assert card["families"][fam]["extras"] == []
        assert card["families"][fam]["bridged_samples"] == 0


def test_score_seed_missing_fails_with_detail(small_spec):
    gt = _gt(small_spec)
    pipe = _pipeline_perfect(gt)
    pipe["columns"] = pipe["columns"][1:]
    card = score_seed(gt, pipe, TH)
    assert card["pass"] is False
    assert card["families"]["columns"]["missing"]
    assert card["fail_reasons"]


def test_render_md_and_roundtrip(small_spec, tmp_path):
    gt = _gt(small_spec)
    card = score_seed(gt, _pipeline_perfect(gt), TH)
    md = render_md(card)
    assert "PASS" in md and "columns" in md
    p = tmp_path / "card.json"
    p.write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")
    assert json.loads(p.read_text(encoding="utf-8"))["pass"] is True
