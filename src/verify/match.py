# -*- coding: utf-8 -*-
"""族内匹配:GT 采样 vs 管线折线,产出 found/missing/extra/bridged/uncovered 五类账目。

全部在扫描系计算(GT samples_warp 系;管线矫正系折线由 score_vs_gt 先经 H_rect_to_src 回映射)。

配对语义(反放水的关键):
- GT×管线 折线级**独占**贪心配对——平行双线相距仅 8px(<detect_tau),无独占时缺线会被
  邻线顶替漏判;每条管线折线至多归一条 GT 线,每条 GT 线至多认一条管线折线;
- GT 线"找到" = 配对成功且其墨采样 ≥95% 距配对线 ≤detect_tau;
- 管线折线"多余" = 未配对且自身点位贴不上任何 GT 墨采样(占比 <extra_frac)——
  未配对但贴线的是合法碎段(分段绘制),不算多余;真正的多余线由"贴不上墨"暴露;
- "断口桥接" = 任一管线点落入 GT 断口扫描系四边形(与配对无关,含未配对碎段)。
"""
import cv2
import numpy as np

from src.verify.polyline_metrics import dev_stats, points_to_polyline_dist


def _family_lines(gt, role):
    return [ln for ln in gt["lines"] if ln["role"] == role]


def _ink_samples(line):
    smp = np.asarray(line["samples_warp"], np.float64)
    brk = np.asarray(line["samples_in_break"], bool)
    return smp[~brk]


def _in_quads(pts, quads) -> np.ndarray:
    """pts (n,2) 是否落入任一四边形(pointPolygonTest)。"""
    hit = np.zeros(len(pts), bool)
    for quad in quads:
        qp = np.asarray(quad, np.float32).reshape(-1, 1, 2)
        for i, (x, y) in enumerate(pts):
            if not hit[i] and cv2.pointPolygonTest(qp, (float(x), float(y)), False) >= 0:
                hit[i] = True
    return hit


def _greedy_pairs(dmat, tau):
    """距离矩阵独占贪心配对,返回 {i: j}。距离 >tau 的候选不入对。"""
    pairs = {}
    used_i, used_j = set(), set()
    order = np.argsort(dmat, axis=None)
    for flat in order:
        d = float(dmat.reshape(-1)[flat])
        if d > tau or not np.isfinite(d):
            break
        i, j = divmod(int(flat), dmat.shape[1])
        if i not in used_i and j not in used_j:
            pairs[i] = j
            used_i.add(i)
            used_j.add(j)
    return pairs


def match_family(gt, role, polys, th) -> dict:
    """polys: 该族管线折线列表 (n_i,2) 扫描系。返回该族完整判分账目。"""
    lines = _family_lines(gt, role)
    gt_ink = [_ink_samples(ln) for ln in lines]
    all_ink = (np.vstack([s for s in gt_ink if len(s)])
               if any(len(s) for s in gt_ink) else np.zeros((0, 2)))
    pipe_pts = [np.asarray(p, np.float64).reshape(-1, 2) for p in polys]

    # 配对距离矩阵:GT 墨采样到管线折线的中位距离;并存每对的 found_frac
    n_i, n_j = len(lines), len(pipe_pts)
    dmat = np.full((n_i, n_j), np.inf)
    fmat = np.zeros((n_i, n_j))
    for i, ink in enumerate(gt_ink):
        if not len(ink):
            continue
        for j, pp in enumerate(pipe_pts):
            if not len(pp):
                continue
            d = points_to_polyline_dist(ink, pp)
            dmat[i, j] = float(np.median(d))
            fmat[i, j] = float((d <= th.detect_tau).mean())

    pairs = _greedy_pairs(dmat, th.detect_tau) if n_i and n_j else {}

    out = {"role": role, "lines": [], "missing": [], "extras": [],
           "bridged_samples": 0, "uncovered": []}

    for i, (ln, ink) in enumerate(zip(lines, gt_ink)):
        rec = {"line_id": ln["line_id"], "n_ink": int(len(ink))}
        j = pairs.get(i)
        if j is None or not len(ink):
            rec["found_frac"] = 0.0
            rec["found"] = False
            rec["dev"] = dev_stats(np.array([], np.float64))
            rec["n_uncovered"] = int(len(ink))
            out["missing"].append(ln["line_id"])
            for x, y in (ink if len(ink) else []):
                out["uncovered"].append(
                    {"line_id": ln["line_id"], "x": float(x), "y": float(y)})
        else:
            d = points_to_polyline_dist(ink, pipe_pts[j])
            near = d[d <= th.detect_tau]
            rec["found_frac"] = float(len(near) / len(ink))
            rec["found"] = rec["found_frac"] >= th.match_min_found_frac
            rec["dev"] = dev_stats(near)          # 几何层只统计近距采样
            miss_mask = d > th.detect_tau
            rec["n_uncovered"] = int(miss_mask.sum())
            if not rec["found"]:
                out["missing"].append(ln["line_id"])
            for x, y in ink[miss_mask]:           # 账外删除采样留坐标供裁片
                out["uncovered"].append(
                    {"line_id": ln["line_id"], "x": float(x), "y": float(y)})
        out["lines"].append(rec)

    # 断口桥接:任一管线点落入该族断口四边形(与配对无关)
    for pp in pipe_pts:
        for ln in lines:
            if ln["breaks_scan_quad"]:
                out["bridged_samples"] += int(_in_quads(pp, ln["breaks_scan_quad"]).sum())

    # 多余线:未配对且贴不上任何 GT 墨采样(贴线的未配对折线=合法碎段)。
    # 记录折线中位点坐标,供裁片定位(破损 GT 场景下违规表现为多余线而非账外删除)。
    for j, pp in enumerate(pipe_pts):
        if j in set(pairs.values()) or not len(pp) or not len(all_ink):
            continue
        d_near = np.min([points_to_polyline_dist(pp, s) for s in gt_ink if len(s)], axis=0)
        if float((d_near <= th.detect_tau).mean()) < th.extra_frac:
            mid = pp[len(pp) // 2]
            out["extras"].append({"index": j, "x": float(mid[0]), "y": float(mid[1])})
    return out
