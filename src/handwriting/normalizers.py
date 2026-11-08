# -*- coding: utf-8 -*-
"""通用规范化工具(数据集无关):文本口径与数值解析。

norm_text 与 compare_ref.norm_cell 同口径(全角→半角、去 ° ℃/空白),
数值判定用宽松 float 解析——规则与校验器共用,保证"改"与"查"一把尺子。
"""
_HALF = {chr(c): chr(c - 0xFEE0) for c in range(0xFF01, 0xFF5F)}

# 描述类文本比对剔除的标点(与 compare_ref._PUNCT 同口径:排版差异不算分歧)
PUNCT = "，。：；、,.:;·()（）-—_'\" 　/"


def norm_text(v):
    """格值→规范化字符串:全角转半角、去 ° ℃/空白;空返回 ""。"""
    s = "" if v is None else str(v).strip()
    if not s:
        return ""
    s = "".join(_HALF.get(ch, ch) for ch in s)
    s = s.replace("°", "").replace("℃", "")
    return "".join(s.split())


def norm_desc(v):
    """描述类文本比对口径:norm_text 后再剔标点(字差才算分歧)。"""
    return "".join(ch for ch in norm_text(v) if ch not in PUNCT)


def parse_num(v):
    """宽松数值解析:可析返回 float,否则 None。"""
    try:
        return float(norm_text(v))
    except (TypeError, ValueError):
        return None
