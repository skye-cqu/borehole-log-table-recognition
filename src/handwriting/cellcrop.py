# -*- coding: utf-8 -*-
"""逐格裁片与读格(数据集无关):从原图灰度图裁单元格并做带盒过滤的 RapidOCR 读数。

几何来源由调用方注入(本项目=表头映射 keep 的 x_in_band + 行区间缓存 row_ivs),
本模块只认 (x0,x1,y0,y1) 与原图数组。

实测教训(2026-11-05, 1015 深度列):
  - keep 的 x_in_band 是表头分隔线位置;手写字会溢出列界('164.28' 的 1 顶在列线上),
    裁窗必须外扩(左~25px 右~60px),否则掐头去尾;
  - 外扩会串入邻列/序号列的盒 → 按盒中心 x 过滤回列区间;
  - 一格拆多盒('421'+'.15')先拼串试解析,失败再合并盒区域重识别;
  - 窗口宁大勿溢,靠盒过滤收敛——desc 越线=邻带笔画污染的教训反用。
"""
import re

_NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def crop_window(gray, x0, x1, y0, y1, pad_l=25, pad_r=60, inset_y=3):
    """行 y 区间 × 列 x 区间 → 外扩裁窗(整数边界)。"""
    a = max(0, int(x0) - pad_l)
    b = min(gray.shape[1], int(x1) + pad_r)
    c = max(0, int(y0) + inset_y)
    d = min(gray.shape[0], int(y1) - inset_y)
    if b - a < 8 or d - c < 8:
        return None
    return gray[c:d, a:b]


def _box_center_x(box, ax):
    return sum(p[0] for p in box) / 4.0 + ax


def read_cell_cands(gray, x0, x1, y0, y1, ocr,
                    pad_l=25, pad_r=60, center_lo=2, center_hi=38):
    """读一格 → 可解析候选文本列表(有序、去重)。

    盒级三分类(绝对 x):完全在 [x0+center_lo, x1+center_hi] 内=收;
    跨阈值=只重识别列侧子区域;在外=丢。候选来自:逐盒文本、连续盒拼串、
    保留盒覆盖区域整幅重识别——序号字形物理跨列线('5'右缘越过分隔线)
    几何甩不掉,交给上层的算术门在候选里仲裁,多候选过门=歧义不采。
    """
    win = crop_window(gray, x0, x1, y0, y1, pad_l=pad_l, pad_r=pad_r)
    if win is None:
        return []
    ax = max(0, int(x0) - pad_l)
    lo, hi = x0 + center_lo, x1 + center_hi
    res, _ = ocr(win)
    frags = []                     # (bl, br, text)
    for box, t, _conf in (res or []):
        xs = sorted(p[0] for p in box)
        bl, br = xs[0] + ax, xs[-1] + ax
        if br < lo or bl > hi:
            continue
        if bl < lo <= br or bl <= hi < br:
            cut = lo if bl < lo <= br else hi
            sub = win[:, max(0, int(cut - ax) - 2):int(br - ax) + 2] \
                if bl < lo <= br else \
                win[:, max(0, int(bl - ax) - 2):int(cut - ax) + 2]
            r2, _ = ocr(sub)
            t2 = "".join(tt for _, tt, _ in (r2 or [])).strip()
            if t2:
                t = t2
        frags.append((bl, br, t.strip()))
    frags.sort()
    cands = []
    if not frags:
        return cands
    n = len(frags)
    for i in range(n):                       # 连续盒拼串(含单盒)
        for j in range(i + 1, min(n, i + 4) + 1):
            s = "".join(t for _, _, t in frags[i:j]).replace(" ", "")
            if _NUM_RE.fullmatch(s) and s not in cands:
                cands.append(s)
    if len(cands) < 2 or True:               # 整幅重识别兜底(覆盖断盒)
        lx = max(0, int(frags[0][0] - ax) - 2)
        rx = min(win.shape[1], int(frags[-1][1] - ax) + 2)
        res2, _ = ocr(win[:, lx:rx])
        s2 = "".join(tt for _, tt, _ in (res2 or [])).strip().replace(" ", "")
        if s2 and _NUM_RE.fullmatch(s2) and s2 not in cands:
            cands.append(s2)
    return cands


def read_cell_text(gray, x0, x1, y0, y1, ocr,
                   pad_l=8, pad_r=8, center_lo=-30, center_hi=60):
    """读一格文本(desc 类宽格):裁窗→盒过滤→列内盒文本按序拼接。

    与数值口径不同:不做数字解析/候选仲裁,只要列区间内的全部盒文本;
    窗口外扩小(文本格列界可靠),盒过滤界放宽(字可贴线)。
    返回拼接文本(可能为空串)。
    """
    win = crop_window(gray, x0, x1, y0, y1, pad_l=pad_l, pad_r=pad_r)
    if win is None:
        return ""
    ax = max(0, int(x0) - pad_l)
    lo, hi = x0 + center_lo, x1 + center_hi
    res, _ = ocr(win)
    frags = []
    for box, t, _conf in (res or []):
        xs = sorted(p[0] for p in box)
        bl, br = xs[0] + ax, xs[-1] + ax
        if br < lo or bl > hi:
            continue
        frags.append((bl, t.strip()))
    frags.sort()
    return " ".join(t for _, t in frags)


def read_cell(gray, x0, x1, y0, y1, ocr, want="number"):
    """read_cell_cands 的单值口径包装:返回 (首选可解析文本, norm|None)。"""
    cands = read_cell_cands(gray, x0, x1, y0, y1, ocr)
    if not cands:
        return "", None
    return cands[0], _parse(cands[0])


def _parse(s):
    m = _NUM_RE.search(s.replace(" ", ""))
    if not m:
        return None
    try:
        return float(m.group(0))
    except ValueError:
        return None
