# -*- coding: utf-8 -*-
"""构造错例必须被抓、完美管线必须过——判分器反放水的单测证据(goal 判定 3 的判分器侧)。"""
import numpy as np

from src.synth.degrade import WarpParams
from src.synth.layout import make_layout
from src.synth.make_gt import build_gt
from src.verify.gate_config import DEFAULT_THRESHOLDS as TH
from src.verify.match import match_family


def _gt(small_spec):
    lay = make_layout(np.random.default_rng(11), small_spec)
    wp = WarpParams(amp1=6, wl1=300.0, ph1=0.5, amp2=2, wl2=90.0, ph2=0.0, tilt=4.0)
    return build_gt(seed=11, lay=lay, warp_params=wp, photo_params=None,
                    shape=(small_spec.height, small_spec.width))


def _perfect(gt):
    """完美管线:输出=GT 墨采样(断口内无墨——断口处置白是 GT 语义)。

    返回 (折线列表, 每条线的墨采样);断口测试需要原始采样时用第二条返回值。
    """
    polys = []
    for ln in gt["lines"]:
        if ln["role"] != "column":
            continue
        smp = np.asarray(ln["samples_warp"], np.float64)
        brk = np.asarray(ln["samples_in_break"], bool)
        polys.append(smp[~brk])
    return polys


def test_perfect_pipeline_all_found_no_extra(small_spec):
    gt = _gt(small_spec)
    res = match_family(gt, "column", _perfect(gt), TH)
    assert res["missing"] == [] and res["extras"] == []
    assert res["bridged_samples"] == 0 and res["uncovered"] == []
    assert all(r["found"] for r in res["lines"])
    assert all(r["dev"]["p95"] <= TH.dev_tau for r in res["lines"])


def test_missing_line_is_caught(small_spec):
    gt = _gt(small_spec)
    polys = _perfect(gt)[1:]                      # 抽掉一条列线
    res = match_family(gt, "column", polys, TH)
    assert len(res["missing"]) == 1
    assert res["uncovered"]                       # 该线墨采样转账外删除


def test_extra_line_is_caught(small_spec):
    gt = _gt(small_spec)
    # x=460:距 col_2(380±8)与 col_3(540±8)最近墨采样均 >40px,远离 detect_tau
    polys = _perfect(gt) + [np.array([[460.0, y] for y in range(0, 500, 10)], np.float64)]
    res = match_family(gt, "column", polys, TH)
    assert len(res["extras"]) == 1


def test_constant_x_instead_of_warp_blows_p95(small_spec):
    gt = _gt(small_spec)
    target = [ln for ln in gt["lines"] if ln["role"] == "column"][0]
    x = target["polyline_ideal"][0][0]
    polys = [np.array([[float(x), y] for _, y in target["samples_ideal"]], np.float64)]
    res = match_family(gt, "column", polys, TH)
    line = [r for r in res["lines"] if r["line_id"] == target["line_id"]][0]
    assert (not line["found"]) or line["dev"]["p95"] > TH.dev_tau


def test_bridged_break_is_caught(small_spec):
    gt = _gt(small_spec)
    # 完美管线但在每个断口四边形里塞一个点(模拟直线桥接穿断口)
    polys = []
    for ln in gt["lines"]:
        if ln["role"] != "column":
            continue
        smp = [list(p) for p in ln["samples_warp"]]
        for quad in ln["breaks_scan_quad"]:
            smp.append([sum(p[0] for p in quad) / 4, sum(p[1] for p in quad) / 4])
        polys.append(np.array(smp, np.float64))
    res = match_family(gt, "column", polys, TH)
    assert res["bridged_samples"] >= 1


def test_faint_loss_is_missing_not_crash(small_spec):
    """淡线整条丢失=missing(装饰框/淡线必错图的结构层判据)。"""
    gt = _gt(small_spec)
    res = match_family(gt, "column", _perfect(gt)[:2], TH)
    assert len(res["missing"]) >= 1
