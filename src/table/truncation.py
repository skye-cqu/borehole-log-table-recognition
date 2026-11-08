# -*- coding: utf-8 -*-
"""扫描左缘截断登记(1032 专项,用户 2026-10-20 裁决"登记为不可恢复 + 逐行标注截断")。

为什么需要:1032 的深度列左半格被扫描裁掉,每个数字最左侧的笔画都不在图上
(59.14 只剩 9.14、50.84 只剩 0.84、54.09 只剩 4.09)。裁片与逐行像素都证实:
数字墨在 x=0 处被切断,原图没有那一位。这类缺口**不可从原图恢复**——不能靠
层厚反推去"补"一位(那是发明数据,违反约束2 的数据源神圣)。

本模块只做两件事,都不改数值:
  1. 逐行给像素判定:该格数字是否贴在裁切边上(贴边墨量 >= CUT_INK_MIN);
  2. 给出数值侧旁证(读串与层厚推算值的关系),供人复核,不作主判据。
标注由 src/tools/mark_truncation.py 落到 Excel(橙色底 + 批注),数值原样不动。
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

if str(Path(__file__).resolve().parents[2]) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

CUT_EDGE_W = 3      # 裁切边判定宽度 px(图像最左 x<3):1032 实测残笔画全在 x=0..2
CUT_INK_MIN = 8     # 贴边墨像素下限(该行内 x<3 的暗像素数)
MIN_ROW_H = 12      # 行高下限 px,更薄的不判(分不清数字与格线)
INK_THR = 150       # 暗色阈值(与全仓二值口径一致)


def cut_ink(gray, y0, y1, x0, x1):
    """该行内贴裁切边的暗像素数(裁切边 = 图像最左 x0..x0+CUT_EDGE_W)。

    只数最左那几列:1032 的深度格左半被裁掉后,剩下的数字笔画直接压在 x=0..2 上;
    而表格自己的格线在 x=64..105 一带,离裁切边 60px 以上,不会被算进来。
    """
    a, b = max(0, int(y0)), min(gray.shape[0], int(y1))
    if b - a < 4:
        return 0
    sub = gray[a:b, max(0, int(x0)):max(0, int(x0)) + CUT_EDGE_W]
    if sub.size == 0:
        return 0
    return int((sub < INK_THR).sum())


def column_frame_present(gray, ys, x, frac_min=0.5):
    """x 处是否存在一条贯穿表高的竖框线(暗色占比 >= frac_min)。

    1032 实测:深度列左框整条不存在(全图 x 方向没有任何一列的暗色占比 >0.5,
    x=0..12 只有 0.05~0.08 的零散墨)——深度格左半被扫描裁掉,前导位不可恢复。
    这是**整列级**证据,比逐行数贴边墨稳:逐行判会被扫描噪点(每行 0~140 px)带偏。
    """
    a, b = max(0, int(ys[0])), min(gray.shape[0], int(ys[-1]))
    if b - a < 100:
        return False
    sub = gray[a:b, max(0, int(x) - 1):int(x) + 3]
    if sub.size == 0:
        return False
    return bool((sub < INK_THR).mean(axis=0).max() >= frac_min)


def scan_left_cut(gray, ys, x0, x1):
    """逐行判"数字是否被裁切边切断"。ys=行界 y 序列(升序),返回逐行清单。

    只判行高 >= MIN_ROW_H 的格;行内贴边墨 >= CUT_INK_MIN 记截断。
    这是纯像素判据:贴边墨存在 = 该格内容确实被切掉了左半,与 OCR 读数无关。
    """
    out = []
    for i in range(len(ys) - 1):
        a, b = int(ys[i]), int(ys[i + 1])
        if b - a < MIN_ROW_H:
            continue
        ink = cut_ink(gray, a + 4, b - 4, x0, x1)
        out.append({"行": i, "y0": a, "y1": b, "贴边墨": ink,
                    "截断": bool(ink >= CUT_INK_MIN)})
    return out


def depth_chain_evidence(rows):
    """数值侧旁证:读到的深度是否"小数位与推算值一致、整数位缺失"。

    rows=[(xlsx行号, 深度, 层厚), ...](按行序)。推算值 = 上一行深度 + 本行层厚。
    返回逐条 {行, 读, 层厚, 推算, 差, 支持};支持=小数位一致而整数位不同(前缀丢失)。
    这是**旁证不是主判据**:实测有巧合(1032 行7 读 14.39、推算 4.39,小数位也一致),
    所以标注必须由像素判据决定,这里只供人复核。
    """
    out, prev = [], None
    for no, d, thk in rows:
        if not isinstance(d, (int, float)) or not isinstance(thk, (int, float)):
            prev = d if isinstance(d, (int, float)) else prev
            continue
        if prev is None:
            prev = d
            continue
        exp = round(prev + thk, 2)
        diff = round(d - exp, 2)
        sd = ("%.2f" % d).split(".")[-1]
        se = ("%.2f" % exp).split(".")[-1]
        out.append({"行": no, "读": d, "层厚": thk, "推算": exp, "差": diff,
                    "支持": bool(abs(diff) >= 0.02 and sd == se)})
        prev = d
    return out