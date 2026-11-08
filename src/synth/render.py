# -*- coding: utf-8 -*-
"""把矢量版式画成干净灰度图(理想帧)。只画 GT 里有的元素——画与账一致。"""
import cv2
import numpy as np

from src.synth.layout import LineSpec, SynthLayout


def _draw_line(img: np.ndarray, ln: LineSpec) -> None:
    pts = np.array(ln.polyline, np.int32).reshape(-1, 1, 2)
    cv2.polylines(img, [pts], isClosed=False, color=int(ln.gray),
                  thickness=int(ln.thickness), lineType=cv2.LINE_8)


def _paint_breaks_white(img: np.ndarray, ln: LineSpec) -> None:
    (x0, y0), (x1, y1) = ln.polyline[0], ln.polyline[-1]
    vertical = y1 != y0
    half = ln.thickness // 2 + 1
    for s0, s1 in ln.breaks:
        for s in range(int(s0) - half, int(s1) + half + 1):
            x, y = (x0, y0 + s) if vertical else (x0 + s, y0)
            if 0 <= y < img.shape[0] and 0 <= x < img.shape[1]:
                cv2.circle(img, (x, y), half, 255, -1)


def render_clean(lay: SynthLayout) -> np.ndarray:
    img = np.full((lay.spec.height, lay.spec.width), 255, np.uint8)
    for blk in lay.blocks:
        if blk.kind == "band":
            x0, x1 = blk.geometry
            img[:, x0:x1 + 1] = blk.gray
        elif blk.kind == "rect_outline":
            x0, y0, x1, y1 = blk.geometry
            cv2.rectangle(img, (x0, y0), (x1, y1), int(blk.gray), int(blk.thickness))
    for ln in lay.lines:
        _draw_line(img, ln)
    for ln in lay.lines:
        if ln.breaks:
            _paint_breaks_white(img, ln)
    return img
