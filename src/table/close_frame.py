# -*- coding: utf-8 -*-
"""阶段6e：外框闭合（用户 2026-09-05 指示：按线条原趋势补全成闭合的面；
四角之间近似垂直，不得出现 30°/45° 突倾）。

输入 = {stem}_分割线.json（左右边界）+ {stem}_上下框.json（上下框链）。
左右边界重建三级机制（前轮 bridge_line 的端部裁除会截短强剪切边界的教训）：
  ① chain：边界自家 _orig_ids 免裁重链（1017/1022 实证：碎片本来就全，只是被裁）；
  ② split：锚点校验失败（顶框链端高度处边界 x 偏锚 >60px，1035 装饰框混轨）→
    自家碎片按"投影到锚点高度 ≤45px"分家重链；
  ③ walk：仍缺 → 从锚点角点沿墨迹行走补建（_peak_salient 显著性门槛，
    装饰框伴线 ~70px 在 ±40 窗外；墨迹断即停）。
边内剩余缺口按该边走廊趋势补全（trend）；四角按两侧端部稳健切线闭合至交点
（切线与边主线偏角 ≤30°、两切线夹角 65°~115°，单侧 ≤800px）。
趋势/闭合段全部落账 provenance 并在叠加图黄色显示，与既有墨迹线（蓝）区分。
1032 左边界物理裁失，以扫描边 x=0 闭合（provenance=scan_edge）。
输出 {stem}_闭合外框.json、{stem}_闭合外框叠加图.png(+预览)、闭合外框汇总.json。"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.table.frame_topbottom import _peak_salient  # noqa: E402

ANCHOR_TOL = 60.0     # 锚点校验容差（边界在链端高度处 x 距链端 x）
SPLIT_TOL = 45.0      # 分家容差（碎片投影 x 距锚）
TAN_MAX = math.tan(math.radians(30.0))   # 切线与边主线最大偏角 30°
ANG_LO, ANG_HI = 65.0, 115.0             # 角点两切线夹角允许范围
CLOSE_MAX = 800.0     # 单侧趋势闭合距离上限
GAP_MIN = 8.0
BAND = 400.0          # 走廊带宽（同前轮）
TAIL_DEV = 50.0       # 链尾伪端离群阈值
WALK_BAND = 250.0     # 墨迹行走步长
WALK_WIN = 40.0       # 行走窗口（首步标称±win，后续连续性±cont）


def robust_fit(pts, axis):
    """cross = k*axis + b 稳健拟合（MAD 去离群）。"""
    a = pts[:, axis].astype(float)
    c = pts[:, 1 - axis].astype(float)
    keep = np.ones(len(a), bool)
    k = b = 0.0
    for _ in range(3):
        if keep.sum() < 4:
            break
        k, b = np.polyfit(a[keep], c[keep], 1)
        res = np.abs(c - (k * a + b))
        mad = float(np.median(res[keep])) + 1e-6
        keep = res < max(50.0, 2.5 * mad)
    return float(k), float(b)


def end_tangent(gp, at_start, axis, span=600.0):
    """端部切线拟合；返回 (k, b, 摘除的离群尾点)。"""
    a = gp[:, axis]
    lo, hi = float(a.min()), float(a.max())
    sel = gp[a <= lo + span] if at_start else gp[a >= hi - span]
    if len(sel) < 6:
        sel = gp
    k, b = robust_fit(sel, axis)
    res = np.abs(sel[:, 1 - axis] - (k * sel[:, axis] + b))
    bad = res > TAIL_DEV
    dropped = sel[bad]
    if bad.any() and int((~bad).sum()) >= 6:
        k, b = robust_fit(sel[~bad], axis)
    return k, b, dropped


def corridor(pts, axis):
    """边自身走廊：轴向 400px 带中位 → 插值函数。"""
    a = pts[:, axis]
    lo, hi = float(a.min()), float(a.max())
    ca, cc = [], []
    v = lo
    while v < hi:
        sel = pts[(a >= v) & (a < v + BAND)]
        if len(sel) >= 4:
            ca.append(v + BAND / 2)
            cc.append(float(np.median(sel[:, 1 - axis])))
        v += BAND
    if not ca:
        m = float(np.median(pts[:, 1 - axis]))
        ca, cc = [lo, hi], [m, m]
    return lambda t: float(np.interp(t, ca, cc))


def trend_fill(pts, axis):
    """边内剩余缺口按走廊趋势补全。返回 (新点列, 补全段记录)。"""
    order = np.argsort(pts[:, axis])
    pts = pts[order]
    a = pts[:, axis]
    crv = corridor(pts, axis)
    fills = []
    keep = [pts[0]]
    for i in range(1, len(pts)):
        gap = a[i] - a[i - 1]
        if gap > GAP_MIN:
            v0, v1 = float(a[i - 1]), float(a[i])
            vs = np.arange(v0 + 40.0, v1, 80.0)
            add = np.zeros((len(vs), 2), float)
            add[:, axis] = vs
            add[:, 1 - axis] = [crv(v) for v in vs]
            fills.append({'prov': 'trend', 'axis_span': [round(v0), round(v1)],
                          'gap': round(float(gap)), 'pts': np.round(add, 1).tolist()})
            keep.extend(add)
        keep.append(pts[i])
    return np.asarray(keep, float), fills


def chain_ids(seg_v, ids):
    """碎片免裁重链：各自按 y 排序后按 y 序拼接（定稿碎片同线性已被锚点校验保证）。"""
    pieces = []
    for sid in ids:
        p = np.asarray(seg_v[sid], float)
        if len(p) >= 2:
            pieces.append(p[np.argsort(p[:, 1])])
    pieces.sort(key=lambda p: float(p[0, 1]))
    return np.vstack(pieces)


def x_at(gp, y):
    return float(np.interp(y, gp[:, 1], gp[:, 0]))


def split_by_anchor(seg_v, ids, tx, ty, y_lo, y_hi):
    """混轨分家：碎片中位 (x,y) 拟合全程走向，x 投影到锚点高度后距锚 ≤SPLIT_TOL 者
    重链；校验锚位与覆盖率。"""
    med = np.array([[float(np.median(seg_v[sid][:, 0])), float(np.median(seg_v[sid][:, 1]))]
                    for sid in ids])
    keep = list(ids)
    for _ in range(2):
        k, b = robust_fit(np.stack([med[ids.index(s)] for s in keep]), 1)
        sel = [sid for sid in keep
               if abs((med[ids.index(sid), 0] - (k * med[ids.index(sid), 1] + b))
                      - (tx - (k * ty + b))) <= SPLIT_TOL]
        if len(sel) == len(keep) or len(sel) < 3:
            break
        keep = sel
    if len(keep) < 3:
        return None
    gp = chain_ids(seg_v, keep)
    if abs(x_at(gp, ty) - tx) > SPLIT_TOL:
        return None
    span = float(gp[:, 1].max() - gp[:, 1].min())
    if span < 0.5 * (y_hi - y_lo):
        return None
    return gp


def walk_edge(o, start, y_stop, x_nom, downward,
              band_h=WALK_BAND, win=WALK_WIN, cont=WALK_WIN):
    """从锚点角点沿墨迹行走补建竖直边界：o=原图灰度（行=y、列=x），
    首步标称 x±win，后续连续性 ±cont，每带峰值须显著高出基线；
    断墨时回到标称位重锁至多 2 带，仍无墨即停（缺口交给趋势补全）。"""
    pts = []
    y_cur, x_cur = float(start[1]), float(start[0])
    first = True
    miss = 0
    while (y_stop - y_cur > GAP_MIN) if downward else (y_cur - y_stop > GAP_MIN):
        yt = min(y_stop, y_cur + band_h) if downward else max(y_stop, y_cur - band_h)
        if first:
            w0, w1, ref = int(x_nom - win), int(x_nom + win), x_nom
        else:
            w0, w1, ref = int(x_cur - cont), int(x_cur + cont), x_cur
        xi = _peak_salient(o, min(y_cur, yt), max(y_cur, yt), w0, w1, ref, cont)
        if xi is None and miss < 2 and not first:
            miss += 1
            y_cur, x_cur = yt, x_cur
            continue
        if xi is None:
            break
        pts.append((xi, yt))
        y_cur, x_cur = yt, xi
        first = False
        miss = 0
    if pts and abs(pts[-1][1] - y_stop) > 1.0:
        pts.append((pts[-1][0], y_stop))
    return np.array([[p[0], p[1]] for p in pts], float)


def trim_end(gp, at_start=False, dev=60.0, nfit=8, guard=2):
    """端部离群尾修剪（按点数取窗：边界碎片稀疏，px 窗会退化为单点）：
    端部 nfit+guard 点、排除最末 guard 点拟合，从端部剔出偏离 >dev 的点。
    返回 (修剪后 gp, 被剔点)。"""
    if len(gp) < nfit + guard + 2:
        return gp, np.zeros((0, 2))
    seg = gp[:nfit + guard] if at_start else gp[-(nfit + guard):]
    fit_seg = seg[guard:] if at_start else seg[:nfit]
    k, b = robust_fit(fit_seg, 1)
    res = np.abs(gp[:, 0] - (k * gp[:, 1] + b))
    bad = res > dev
    cut = None
    order = range(len(gp)) if at_start else range(len(gp) - 1, -1, -1)
    for i in order:
        if not bad[i]:
            cut = i
            break
    if cut is None:
        return gp, np.zeros((0, 2))
    if at_start:
        return gp[cut:], gp[:cut]
    return gp[:cut + 1], gp[cut + 1:]


def close_corner(sa, sb, enda, fwda, endb, fwdb, axis_a):
    """角闭合：两侧端部切线 → 偏角/夹角检查 → 交点 → 各侧沿切线补至交点。
    返回 (corner, 增段字典, 摘除尾点, note)。"""
    gp_a, gp_b = sa['pts'], sb['pts']
    axis_b = 1 - axis_a
    ka, ba, drop_a = end_tangent(gp_a, enda == 0, axis_a)
    kb, bb, drop_b = end_tangent(gp_b, endb == 0, axis_b)
    if abs(ka) > TAN_MAX:
        return None, {}, 'A 侧切线偏角 %.0f° 超 30°' % math.degrees(math.atan(abs(ka)))
    if abs(kb) > TAN_MAX:
        return None, {}, 'B 侧切线偏角 %.0f° 超 30°' % math.degrees(math.atan(abs(kb)))
    ang = math.degrees(abs(math.atan2(ka, 1.0) - math.atan2(1.0, kb)))
    if ang > 180.0:
        ang = 360.0 - ang
    if not (ANG_LO <= ang <= ANG_HI):
        return None, {}, '两切线夹角 %.0f° 超出 %.0f~%.0f' % (ang, ANG_LO, ANG_HI)
    if abs(1.0 - ka * kb) < 1e-6:
        return None, {}, '两切线近平行'
    xi = (kb * ba + bb) / (1.0 - ka * kb)
    inter = np.array([xi, ka * xi + ba], float)
    pa = gp_a[0] if enda == 0 else gp_a[-1]
    pb = gp_b[0] if endb == 0 else gp_b[-1]
    d_a = (float(inter[axis_a]) - float(pa[axis_a])) * fwda
    d_b = (float(inter[axis_b]) - float(pb[axis_b])) * fwdb
    if d_a > CLOSE_MAX:
        return None, {}, 'A 侧闭合距离 %.0f 超 %.0f' % (d_a, CLOSE_MAX)
    if d_b > CLOSE_MAX:
        return None, {}, 'B 侧闭合距离 %.0f 超 %.0f' % (d_b, CLOSE_MAX)
    adds = {}
    if d_a > GAP_MIN:
        adds['A'] = np.array([pa, inter], float)
    if d_b > GAP_MIN:
        adds['B'] = np.array([pb, inter], float)
    return (inter, adds), (drop_a, drop_b), \
        'd=%.0f/%.0f ang=%.0f' % (max(0.0, d_a), max(0.0, d_b), ang)


def process(stem):
    d = json.load(open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_分割线.json', encoding='utf-8'))
    tb = json.load(open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_上下框.json', encoding='utf-8'))
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f'{stem}.json', encoding='utf-8'))
    seg_v = {s['id']: np.asarray(s['points'], float) for s in cj['lines']
             if s['direction'] == 'vertical' and s['label'] == 'high'}
    hs_all = [np.asarray(s['points'], float) for s in cj['lines']
              if s['direction'] == 'horizontal' and s['label'] == 'high']

    def primary(kind):
        gs = tb[kind]['groups']
        if not gs:
            return None
        return max(gs, key=lambda g: float(np.ptp(np.asarray(g['pts'], float)[:, 0])))

    top_g, bot_g = primary('top'), primary('bottom')
    sides = {}
    for name in ('top', 'bottom'):
        g = {'top': top_g, 'bottom': bot_g}[name]
        sides[name] = None if g is None else \
            {'pts': np.asarray(g['pts'], float), 'segs': [{'prov': 'prior', 'n': len(g['pts'])}]}
    edge_lines = {l.get('side'): l for l in d['lines']
                  if l['kind'] == 'edge' and l.get('side') in ('left', 'right')}
    notes, rebuilt = [], []

    y_top = float(sides['top']['pts'][:, 1].min()) if sides['top'] is not None else None
    y_bot = float(sides['bottom']['pts'][:, 1].max()) if sides['bottom'] is not None else None
    ref = sides['top']['pts'] if sides['top'] is not None else None

    col_ms = sorted(float(np.median(np.asarray(c['pts'], float)[:, 0])) for c in d['lines']
                    if c['kind'] == 'column' and c.get('pts'))
    col_min = min(col_ms) if col_ms else None
    col_max = max(col_ms) if col_ms else None
    for name in ('left', 'right'):
        sides[name] = None
        # 锚点 = 顶/底链的西(东)端，须过列间距校验（左：锚在最西列以西 20~150px；
        # 右：锚在最东列以东 20~650px）。1042 实证：顶链西端可过冲到装饰框角，
        # 列间距规则把它排除，选底链端为锚。
        cands = []
        for ch in (sides['top'], sides['bottom']):
            if ch is None:
                continue
            r = ch['pts']
            i = int(np.argmin(r[:, 0])) if name == 'left' else int(np.argmax(r[:, 0]))
            cands.append((float(r[i, 0]), float(r[i, 1]), ch is sides['top']))
        if not cands:
            continue
        if name == 'left':
            ok = [c for c in cands if col_min is not None and 20.0 <= col_min - c[0] <= 150.0]
        else:
            ok = [c for c in cands if col_max is not None and 20.0 <= c[0] - col_max <= 650.0]
        side = None
        # 顶/底链端冲突（相距 >150px）：按列间距决策——左边界取距最西列更近的锚
        # （1042：底锚 gap=1 真边界 vs 顶锚 197 装饰框）；右边界取距最东列更远的锚
        # （1035：顶锚 gap=568 真边界 vs 底锚 98 墨迹渐断处）。装饰框永远在更外
        # 侧、列间距更大，两个方向都不会选中装饰框。
        if len(cands) == 2 and abs(cands[0][0] - cands[1][0]) > 150.0:
            if name == 'left':
                pick = min(range(2), key=lambda i: col_min - cands[i][0]) if col_min else 0
            else:
                pick = max(range(2), key=lambda i: cands[i][0] - col_max) if col_max else 0
            tx, ty, at_top = cands[pick]
            notes.append('%s 边界双锚冲突，按列间距取%s链端锚'
                         % (name, '顶' if at_top else '底'))
        elif ok:
            tx, ty, at_top = ok[0]
        else:
            tx, ty, at_top = cands[0]
        ln = edge_lines.get(name)
        ids0 = [sid for sid in ((ln.get('_orig_ids') or []) if ln is not None else [])
                if sid in seg_v and len(seg_v[sid]) >= 2]
        if len(ids0) >= 3:
            gp = chain_ids(seg_v, ids0)
            if abs(x_at(gp, ty) - tx) <= ANCHOR_TOL:
                side = {'pts': gp, 'segs': [{'prov': 'prior_chain', 'n': len(gp)}]}
            else:
                sub = split_by_anchor(seg_v, ids0, tx, ty, y_top, y_bot)
                if sub is not None:
                    side = {'pts': sub, 'segs': [{'prov': 'split', 'n': len(sub)}]}
                    notes.append('%s 边界混轨已按锚点分家重链' % name)
        if side is None and not (name == 'left' and tx <= 5.0):
            gray = cv2.imread(str(paths.RAW_DIR / f'{stem}.JPG'), cv2.IMREAD_GRAYSCALE)
            y_other = y_bot if at_top else y_top
            pts = walk_edge(gray, (tx, ty), y_other, tx, downward=at_top)
            walked = float(np.ptp(pts[:, 1])) if len(pts) else 0.0
            if walked >= 0.85 * abs(y_other - ty):
                side = {'pts': np.vstack([np.array([[tx, ty]], float), pts]),
                        'segs': [{'prov': 'ink_walk', 'n': len(pts) + 1}]}
                rebuilt.append(name)
                notes.append('%s 边界由%s链端锚墨迹行走补建 %d 步'
                             % (name, '顶' if at_top else '底', len(pts)))
        if side is None:
            if name == 'left' and tx <= 5.0:
                yt2 = float(np.interp(0.0, ref[:, 0], ref[:, 1]))
                yb2 = float(np.interp(0.0, sides['bottom']['pts'][:, 0], sides['bottom']['pts'][:, 1]))                     if sides['bottom'] is not None else yt2
                sides['left'] = {'pts': np.array([[0.0, yt2], [0.0, yb2]], float),
                                 'segs': [{'prov': 'scan_edge', 'n': 2}]}
                notes.append('左边界扫描裁失，以图像左缘闭合')
            else:
                notes.append('%s 边界无法重建' % name)
            continue
        # 端部离群尾修剪 + 墨迹行走延伸至表格上下界
        gp = np.asarray(side['pts'], float)
        gp = gp[np.argsort(gp[:, 1])]
        gp, drop_b = trim_end(gp, at_start=False)
        gp, drop_t = trim_end(gp, at_start=True)
        dts = [d for d in (drop_b, drop_t) if len(d)]
        if dts:
            side['segs'].append({'prov': 'tail_trim', 'n': int(sum(len(d) for d in dts)),
                                 'pts': np.round(np.vstack(dts), 1).tolist()})
        miss_bot = y_bot - float(gp[:, 1].max())
        miss_top = float(gp[:, 1].min()) - y_top
        if miss_bot > GAP_MIN or miss_top > GAP_MIN:
            gray = cv2.imread(str(paths.RAW_DIR / f'{stem}.JPG'), cv2.IMREAD_GRAYSCALE)
            if miss_bot > GAP_MIN:
                sx, sy = float(gp[np.argmax(gp[:, 1]), 0]), float(gp[:, 1].max())
                w = walk_edge(gray, (sx, sy), y_bot, sx, downward=True)
                if len(w):
                    side['segs'].append({'prov': 'walk_ext', 'n': len(w),
                                         'pts': np.round(w, 1).tolist()})
                    gp = np.vstack([gp, w])
            miss_top = float(gp[:, 1].min()) - y_top
            if miss_top > GAP_MIN:
                sx, sy = float(gp[np.argmin(gp[:, 1]), 0]), float(gp[:, 1].min())
                w = walk_edge(gray, (sx, sy), y_top, sx, downward=False)
                if len(w):
                    side['segs'].append({'prov': 'walk_ext', 'n': len(w),
                                         'pts': np.round(w[::-1], 1).tolist()})
                    gp = np.vstack([w[::-1], gp])
        sides[name] = {'pts': gp[np.argsort(gp[:, 1])], 'segs': side['segs']}

    # ② 边内趋势补全
    for name, axis in (('left', 1), ('right', 1), ('top', 0), ('bottom', 0)):
        s = sides[name]
        if s is None:
            continue
        gp2, fills = trend_fill(s['pts'], axis)
        if fills:
            s['segs'].extend(fills)
            s['pts'] = gp2

    # ③ 四角闭合（end: 0=链头/1=链尾；fwd: 交点应在的正方向）
    corners = {}
    plan = [('TL', 'top', 0, -1, 'left', 0, -1), ('TR', 'top', 1, +1, 'right', 0, -1),
            ('BR', 'bottom', 1, +1, 'right', 1, +1), ('BL', 'bottom', 0, -1, 'left', 1, +1)]
    for cname, na, enda, fwda, nb, endb, fwdb in plan:
        sa, sb = sides[na], sides[nb]
        if sa is None or sb is None:
            corners[cname] = None
            notes.append('%s 缺边未闭合' % cname)
            continue
        axis_a = 0 if na in ('top', 'bottom') else 1
        res, drops, note = close_corner(sa, sb, enda, fwda, endb, fwdb, axis_a)
        if res is None:
            corners[cname] = None
            notes.append('%s 闭合失败：%s' % (cname, note))
            continue
        inter, adds = res
        corners[cname] = [round(float(inter[0])), round(float(inter[1]))]
        for nm, sname, endx in (('A', na, enda), ('B', nb, endb)):
            s = sides[sname]
            drop = drops[0] if nm == 'A' else drops[1]
            if drop is not None and len(drop):
                s.setdefault('dropped_tail', []).extend(np.round(drop, 1).tolist())
            if nm in adds:
                add = adds[nm]
                seg_rec = {'prov': 'trend_close', 'pts': np.round(add, 1).tolist()}
                if endx == 0:
                    s['pts'] = np.vstack([add[::-1], s['pts']])
                    s['segs'].insert(1, seg_rec)
                else:
                    s['pts'] = np.vstack([s['pts'], add])
                    s['segs'].append(seg_rec)
            else:
                s['segs'].append({'prov': 'corner_meet',
                                  'at': [round(float(inter[0])), round(float(inter[1]))]})

    out = {'image': stem, 'corners': corners,
           'closed': all(v is not None for v in corners.values()),
           'edge_rebuilt': rebuilt, 'notes': notes}
    for name in ('left', 'right', 'top', 'bottom'):
        s = sides[name]
        out[name] = None if s is None else {
            'pts': np.round(s['pts'], 1).tolist(), 'segs': s['segs'],
            'dropped_tail': s.get('dropped_tail', [])}
    return out, sides


def render(stem, out, sides):
    viz = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_COLOR)
    prev = json.load(open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_上下框.json', encoding='utf-8'))
    dd = json.load(open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_分割线.json', encoding='utf-8'))
    cj_lines = json.load(open(paths.CANDIDATE_COORD_DIR / f'{stem}.json', encoding='utf-8'))['lines']
    used_v = {sid for ln in dd['lines'] for sid in ln.get('_orig_ids', [])}
    quiet_h = set(prev['outside']['above']) | set(prev['outside']['below']) | set(prev['outside']['inside'])
    dim = np.zeros(viz.shape[:2], bool)
    for s in cj_lines:
        if s['direction'] == 'vertical' and s['label'] == 'high' and s['id'] not in used_v:
            cv2.polylines(dim, [np.asarray(s['points'], np.int32).reshape(-1, 1, 2)], False, True, 3)
        if s['direction'] == 'horizontal' and s['label'] == 'high' and s['id'] in quiet_h:
            cv2.polylines(dim, [np.asarray(s['points'], np.int32).reshape(-1, 1, 2)], False, True, 3)
    viz[dim] = (viz[dim] * 0.45).astype(np.uint8)

    if out['closed']:
        poly = np.array([out['corners']['TL'], out['corners']['TR'],
                         out['corners']['BR'], out['corners']['BL']], np.int32)
        tint = viz.copy()
        cv2.fillPoly(tint, [poly], (120, 255, 160))
        cv2.addWeighted(tint, 0.12, viz, 0.88, 0, viz)

    for name in ('left', 'right', 'top', 'bottom'):     # 蓝=既有墨迹线（定稿/桥接/外延/行走）
        s = sides[name]
        if s is None:
            continue
        cv2.polylines(viz, [np.asarray(s['pts'], np.int32).reshape(-1, 1, 2)], False, (255, 0, 0), 6, cv2.LINE_AA)
    for name in ('left', 'right', 'top', 'bottom'):     # 黄=本轮趋势补全/闭合
        s = sides[name]
        if s is None:
            continue
        for seg in s['segs']:
            if seg['prov'] in ('trend', 'trend_close') and seg.get('pts'):
                arr = np.asarray(seg['pts'], np.int32).reshape(-1, 1, 2)
                cv2.polylines(viz, [arr], False, (0, 255, 255), 6, cv2.LINE_AA)
    for cn, cp in out['corners'].items():
        if cp is None:
            continue
        cv2.circle(viz, (int(cp[0]), int(cp[1])), 20, (255, 255, 255), 5, cv2.LINE_AA)
        cv2.putText(viz, cn, (int(cp[0]) - 24, int(cp[1]) - 30), cv2.FONT_HERSHEY_SIMPLEX,
                    1.1, (0, 0, 0), 5, cv2.LINE_AA)
        cv2.putText(viz, cn, (int(cp[0]) - 24, int(cp[1]) - 30), cv2.FONT_HERSHEY_SIMPLEX,
                    1.1, (255, 255, 255), 2, cv2.LINE_AA)
    txt = "closed frame: blue=lines  yellow=trend-closed  white=corners  tint=closed face  dim=content/deco"
    cv2.putText(viz, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 5, cv2.LINE_AA)
    cv2.putText(viz, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_闭合外框叠加图.png'),
                viz, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    half = cv2.resize(viz, (viz.shape[1] // 2, viz.shape[0] // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_闭合外框叠加图_预览.jpg'),
                half, [cv2.IMWRITE_JPEG_QUALITY, 85])


def main():
    only = sys.argv[1:] or sorted('%d' % i for i in range(1015, 1045))
    summary = {}
    for n in only:
        stem = '钻孔柱状图' + n
        out, sides = process(stem)
        render(stem, out, sides)
        json.dump(out, open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_闭合外框.json', 'w',
                            encoding='utf-8'), ensure_ascii=False, indent=1)
        print(n, 'closed=%s' % out['closed'], 'rebuilt=%s' % (out['edge_rebuilt'] or '-'),
              'corners=', out['corners'], '|', '; '.join(out['notes']) if out['notes'] else 'ok',
              flush=True)
        summary[n] = {'closed': out['closed'], 'rebuilt': out['edge_rebuilt'],
                      'corners': out['corners'], 'notes': out['notes']}
    json.dump(summary, open(paths.RUNS_DIR / 'table_reconstruct' / '闭合外框汇总.json', 'w',
                            encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
