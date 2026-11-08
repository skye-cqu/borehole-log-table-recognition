# -*- coding: utf-8 -*-
"""GT 组装:每条线/每个格子在理想帧与弯曲帧双坐标落账;断口按弧长;画与账一致。"""
import json

from src.synth.degrade import WarpParams, warp_polyline
from src.synth.layout import SynthLayout, point_in_breaks, sample_polyline

SCHEMA = "synth_gate_gt_v1"


def _break_quads(ln, warp_params, shape):
    """每个断口的置白矩形四角,理想系→弯曲系。判分器在扫描系用 pointPolygonTest 查断口。

    沿线方向外扩 2×half、横向 half——与 layout.point_in_breaks / render 置白几何同一约定。
    """
    (x0, y0), (x1, y1) = ln.polyline[0], ln.polyline[-1]
    vertical = y1 != y0
    half = ln.thickness // 2 + 1
    quads = []
    for s0, s1 in ln.breaks:
        b0, b1 = int(s0) - 2 * half, int(s1) + 2 * half
        if vertical:
            rect = [(x0 - half, y0 + b0), (x0 + half, y0 + b0),
                    (x0 + half, y0 + b1), (x0 - half, y0 + b1)]
        else:
            rect = [(x0 + b0, y0 - half), (x0 + b0, y0 + half),
                    (x0 + b1, y0 + half), (x0 + b1, y0 - half)]
        if warp_params is not None:
            rect = [list(q) for q in warp_polyline(rect, warp_params, shape)]
        quads.append([list(p) for p in rect])
    return quads


def _cell_poly(x0, y0, x1, y1, step=100.0):
    top = sample_polyline([(x0, y0), (x1, y0)], step)[:-1]
    right = sample_polyline([(x1, y0), (x1, y1)], step)[:-1]
    bottom = sample_polyline([(x1, y1), (x0, y1)], step)[:-1]
    left = sample_polyline([(x0, y1), (x0, y0)], step)[:-1]
    return top + right + bottom + left


def build_gt(*, seed: int, lay: SynthLayout, warp_params: WarpParams | None,
             photo_params, shape: tuple[int, int]) -> dict:
    def wp_pts(pts):
        return [list(q) for q in (warp_polyline(pts, warp_params, shape)
                                  if warp_params else pts)]

    lines = []
    for ln in lay.lines:
        pts = list(ln.polyline)
        smp_i = sample_polyline(pts, step=20.0)
        smp_w = [list(q) for q in (warp_polyline(smp_i, warp_params, shape)
                                   if warp_params else smp_i)]
        in_break = [1 if point_in_breaks(lay, x, y) else 0 for x, y in smp_i]
        lines.append({
            "line_id": ln.line_id, "role": ln.role, "group": ln.group,
            "gray": ln.gray, "thickness": ln.thickness,
            "polyline_ideal": [list(p) for p in pts],
            "polyline_warp": wp_pts(pts),
            "breaks_ideal": [list(b) for b in ln.breaks],
            "samples_ideal": [list(p) for p in smp_i],
            "samples_warp": [list(q) for q in smp_w],
            "samples_in_break": in_break,
            "breaks_scan_quad": _break_quads(ln, warp_params, shape),
        })
    # 单元格:列边界 x col_xs × 行边界 [header_bottom..y_bottom];地质列(第0列带)按 merge_spans 合并
    col_xs = list(lay.col_xs)
    row_ys = list(lay.row_ys)
    cells = []
    for ci in range(len(col_xs) - 1):
        ri = 0
        while ri < len(lay.spec.row_heights):
            # merge_spans 以(行,行)语义存地质列行组——v1 仅第0列,行组 (a,b)
            r1 = ri
            if ci == 0:
                grp = next(((a, b) for a, b in lay.spec.merge_spans if a == ri), None)
                if grp:
                    r1 = grp[1]
            x0, x1 = col_xs[ci], col_xs[ci + 1]
            y0, y1 = row_ys[ri], row_ys[r1 + 1]
            poly = _cell_poly(x0, y0, x1, y1)
            cells.append({
                "cell_id": f"r{ri}_c{ci}" if ri == r1 else f"r{ri}-r{r1}_c{ci}",
                "col_span": [ci, ci + 1], "row_span": [ri, r1 + 1],
                "poly_ideal": [list(p) for p in poly],
                "poly_warp": wp_pts(poly),
            })
            ri = r1 + 1
    return {
        "schema": SCHEMA, "seed": seed,
        "image_size": [shape[0], shape[1]],
        "layout": {"col_xs": list(col_xs), "row_ys": list(row_ys),
                   "header_bottom": lay.header_bottom, "y_bottom": lay.y_bottom},
        "warp": None if warp_params is None else vars(warp_params),
        "photometric": None if photo_params is None else vars(photo_params),
        "lines": lines, "blocks": [vars(b) | {"geometry": list(b.geometry)}
                                   for b in lay.blocks],
        "cells": cells,
        "na_segments": [],
    }


def save_gt(gt: dict, out_dir) -> object:
    from pathlib import Path
    out = Path(out_dir) / f"synth_{gt['seed']:04d}_gt.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(gt, ensure_ascii=False), encoding="utf-8")
    return out
