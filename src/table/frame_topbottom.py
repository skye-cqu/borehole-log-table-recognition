# -*- coding: utf-8 -*-
"""阶段6d：恢复表格真实上/下外框（用户 2026-09-04 指示），装饰性外框必须忽略。

证据 = {stem}_分割线.json 各线（列线+左右边界）的首末端点：列线顶底相连于真实上下框，
装饰框顶/底与图签框都落在证据带之外（1015 实测：装饰框顶距表格顶 ~75px）。
选择 = 证据端点曲线 C(x)±TOL 内、中位残差达标、横跨表格区的水平候选段(label=high)。
补全 = 按残差分组后转置复用 bridge_line（用户断口补齐三点要求）；
端部 = A 方案分带墨迹实证外延至左右边界角点 x 为止，墨迹断即停，绝不越过角点。
数据源神圣：只画既有候选段 + 段间补全 + 墨迹证实外延，不新造线；
装饰框/图签等框外水平线仅记录并压暗。

输出 {stem}_上下框.json、{stem}_外框叠加图.png(+预览)、上下框汇总.json。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core import paths  # noqa: E402
from src.table.bridge_gaps import bridge_line  # noqa: E402

TOL = 55.0        # 点级残差容差（须小于装饰框与表格顶的实测间距 ~75px）
MED_TOL = 40.0    # 段中位残差上限（防擦边混入装饰框）
CLUSTER = 120.0   # 端点证据聚类容差（同 robust_span 先例）
GROUP_TOL = 40.0  # 残差分组间距（双线框时分组）
GAP_MIN = 8.0
X_OVERLAP = 0.60  # 段与表格区横向重叠比例下限
INBAND = 0.60     # 段内落于容差带的比例下限
BAND_H = 250.0    # 外延步长（同 A 方案）


def largest_cluster(vals, tol=CLUSTER):
    """最大聚类（抗离群端点，如右边界延伸进图签区的尾巴）。"""
    best, bc = None, -1
    for v in vals:
        c = sum(1 for w in vals if abs(w - v) <= tol)
        if c > bc:
            best, bc = v, c
    return best


def make_curve(eps):
    """证据端点 (x,y) → y(x) 曲线：按 x 排序 + 滑动中位（去单点离群）+ 线性插值。"""
    eps = sorted(eps)
    xs = np.array([e[0] for e in eps], float)
    ys = np.array([e[1] for e in eps], float)
    if len(ys) >= 5:
        ys = np.array([np.median(ys[max(0, i - 2):i + 3]) for i in range(len(ys))])
    keep = np.concatenate([[True], np.diff(xs) > 1e-6])
    xs, ys = xs[keep], ys[keep]
    return lambda t: np.interp(t, xs, ys)


def corner(edge, curve, default_x):
    """边界线与上下框的角点：返回 (角点x, 该处框线y)。无边界线退到扫描边。"""
    if edge is None or not edge.get('pts'):
        return float(default_x), float(curve(default_x))
    arr = np.asarray(edge['pts'], float)
    y_mid = float(curve(float(np.median(arr[:, 0]))))
    i = int(np.argmin(np.abs(arr[:, 1] - y_mid)))
    return float(arr[i, 0]), float(curve(float(arr[i, 0])))


def select_pieces(hs, curve, x0r, x1r):
    """按证据曲线选框线碎片，返回 [(sid, 带符号中位残差)]。"""
    sel = []
    for sid, p in hs.items():
        if len(p) < 2 or np.ptp(p[:, 0]) < 20:
            continue
        res = p[:, 1] - curve(p[:, 0])
        ov = max(0.0, min(p[:, 0].max(), x1r) - max(p[:, 0].min(), x0r))
        span = max(float(np.ptp(p[:, 0])), 1e-6)
        if ((np.abs(res) <= TOL).mean() >= INBAND and abs(float(np.median(res))) <= MED_TOL
                and ov / span >= X_OVERLAP):
            sel.append((sid, float(np.median(res))))
    sel.sort(key=lambda t: t[1])
    return sel


def group_residuals(sel):
    """按带符号残差分组（同一条物理线残差相近；双线框分成两组）。"""
    groups, cur = [], []
    for sid, r in sel:
        if cur and r - cur[-1][1] > GROUP_TOL:
            groups.append(cur)
            cur = []
        cur.append((sid, r))
    if cur:
        groups.append(cur)
    return groups


def bridge_group(ids, hs):
    """转置复用 bridge_line：x 当 y、y 当 x，桥接机制与列线完全一致。
    返回前把 fills/unfilled/trims 坐标换算回原图 (x,y)，键名相应改为 x 段。"""
    wanted = set(ids)
    segT = {sid: {'points': p[:, ::-1]} for sid, p in hs.items() if sid in wanted}
    pts_t, fills, unf, trims = bridge_line(segT, ids)
    fills = [{'x': fl['y'], 'gap': fl['gap'],
              'fill': [[b, a] for a, b in fl['fill']]} for fl in fills]
    unf = [{'x': u['y'], 'gap': u['gap'], 'reason': u['reason']} for u in unf]
    trims = [{'x': t['y'], 'y': t['x']} for t in trims]
    return np.asarray(pts_t, float)[:, ::-1], fills, unf, trims


def _peak_salient(oT, a_lo, a_hi, w0, w1, ref, cont):
    """带内墨迹峰显著性检验（比 bridge_gaps._peak_in 严格）：
    峰值须高出带内中位基线 0.10×带宽×255——排除恰好穿过框带的竖线/曲线基线
    （1035 实证：水文锯齿线会被当峰跟上，外延沿曲线漂移）。"""
    band = oT[int(a_lo):int(a_hi), max(0, int(w0)):int(w1)]
    if band.size == 0:
        return None
    strength = (255.0 - band.astype(float)).sum(axis=0)
    span = float(a_hi - a_lo)
    if strength.max() < 0.10 * span or \
            float(strength.max()) - float(np.median(strength)) < 0.10 * span * 255:
        return None
    yi = max(0, int(w0)) + int(np.argmax(strength))
    if abs(yi - ref) > cont:
        return None
    return float(yi)


def extend_h(oT, pts, nom, stop, from_left, band_h=BAND_H, win=40.0, cont=40.0):
    """A 方案端点外延（转置版）：从框端向角点逐带走，首步标称 y±win，
    后续只按连续性 ±cont 跟走；每带墨迹峰达显著性阈值才走，墨迹断即停。
    win=40：装饰框距真实框仅 ~70px 且更粗更黑，窗口过宽会被吸到装饰框上。"""
    ext = []
    if from_left:
        p = pts[0]
        c0, c1 = float(p[0]), float(p[1])
        first = True
        while c0 - stop > GAP_MIN:
            tgt = max(stop, c0 - band_h)
            if first:   # 首步窗口与连续性都锚定标称位：链尾若是角点下弯伪端点不致带偏
                w0, w1, ref = int(nom - win), int(nom + win), nom
            else:
                w0, w1, ref = int(c1 - cont), int(c1 + cont), c1
            yi = _peak_salient(oT, tgt, c0, w0, w1, ref, cont)
            if yi is None:
                break
            ext.append((tgt, yi))
            c0, c1 = tgt, yi
        if ext and ext[-1][0] > stop:
            ext.append((stop, ext[-1][1]))
        return list(reversed(ext))
    p = pts[-1]
    c0, c1 = float(p[0]), float(p[1])
    first = True
    while stop - c0 > GAP_MIN:
        tgt = min(stop, c0 + band_h)
        if first:
            w0, w1, ref = int(nom - win), int(nom + win), nom
        else:
            w0, w1, ref = int(c1 - cont), int(c1 + cont), c1
        yi = _peak_salient(oT, c0, tgt, w0, w1, ref, cont)
        if yi is None:
            break
        ext.append((tgt, yi))
        c0, c1 = tgt, yi
    if ext and ext[-1][0] < stop:
        ext.append((stop, ext[-1][1]))
    return ext


def process(stem):
    d = json.load(open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_分割线.json', encoding='utf-8'))
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / f'{stem}.json', encoding='utf-8'))
    hs = {s['id']: np.asarray(s['points'], float) for s in cj['lines']
          if s['direction'] == 'horizontal' and s['label'] == 'high'}
    lines = d['lines']
    gray = cv2.imread(str(paths.RAW_DIR / f'{stem}.JPG'), cv2.IMREAD_GRAYSCALE)
    H, W = gray.shape
    oT = np.ascontiguousarray(gray.T)

    edges = {l.get('side'): l for l in lines
             if l['kind'] == 'edge' and l.get('side') in ('left', 'right')}
    # 证据曲线只用列线端点：边界线与顶/底框的骨架接续点常在角点下游几十至上百 px
    # （1019 实证 80px），混入会把曲线拽弯导致真框碎片选不上。
    cols = [l for l in lines if l['kind'] == 'column' and l['pts']]
    top_y = largest_cluster([l['pts'][0][1] for l in cols])
    bot_y = largest_cluster([l['pts'][-1][1] for l in cols])
    top_use = [(l['pts'][0][0], l['pts'][0][1]) for l in cols
               if abs(l['pts'][0][1] - top_y) <= CLUSTER]
    bot_use = [(l['pts'][-1][0], l['pts'][-1][1]) for l in cols
               if abs(l['pts'][-1][1] - bot_y) <= CLUSTER]
    c_top, c_bot = make_curve(top_use), make_curve(bot_use)
    ends_all = [(l['pts'][0][0], l['pts'][0][1]) for l in lines if l['pts']] + \
               [(l['pts'][-1][0], l['pts'][-1][1]) for l in lines if l['pts']]
    ex0 = min(p[0] for p in ends_all)
    ex1 = max(p[0] for p in ends_all)

    lx, ly = corner(edges.get('left'), c_top, 0.0)
    rx, ry = corner(edges.get('right'), c_top, float(W - 1))
    lbx, lby = corner(edges.get('left'), c_bot, 0.0)
    rbx, rby = corner(edges.get('right'), c_bot, float(W - 1))

    result = {'image': stem,
              'evidence': {'table_y': d['table_y'],
                           'corner_tl': [round(lx), round(ly)], 'corner_tr': [round(rx), round(ry)],
                           'corner_bl': [round(lbx), round(lby)], 'corner_br': [round(rbx), round(rby)],
                           'top_eps': [[round(a), round(b)] for a, b in top_use],
                           'bottom_eps': [[round(a), round(b)] for a, b in bot_use]}}
    stats, outside, chosen_all = {}, {'above': [], 'below': [], 'inside': []}, set()
    for kind, curve, eps in (('top', c_top, top_use), ('bottom', c_bot, bot_use)):
        sel = select_pieces(hs, curve, ex0, ex1)
        chosen, groups_out = set(), []
        for g in group_residuals(sel):
            ids = [sid for sid, _ in g]
            pts, fills, unf, trims = bridge_group(ids, hs)
            chosen.update(ids)
            if kind == 'top':
                lstop, lnom, rstop, rnom = lx, ly, rx, ry
            else:
                lstop, lnom, rstop, rnom = lbx, lby, rbx, rby
            ext_l = extend_h(oT, pts, lnom, lstop, from_left=True) \
                if pts[:, 0].min() - lstop > GAP_MIN else []
            ext_r = extend_h(oT, pts, rnom, rstop, from_left=False) \
                if rstop - pts[:, 0].max() > GAP_MIN else []
            parts = [np.asarray(x, float) for x in (ext_l, pts, ext_r) if len(x)]
            full = np.vstack(parts) if len(parts) > 1 else parts[0]
            conn = []                     # 外延与链体的连接段（JSON 连续、叠加图橙色）
            if ext_l:
                conn.append([[ext_l[-1][0], ext_l[-1][1]],
                             [float(pts[0][0]), float(pts[0][1])]])
            if ext_r:
                conn.append([[float(pts[-1][0]), float(pts[-1][1])],
                             [ext_r[0][0], ext_r[0][1]]])
            groups_out.append({'segment_ids': ids, 'median_res': round(g[0][1], 1),
                               'pts': np.round(full, 1).tolist(),
                               'fills': fills, 'unfilled': unf, 'trims': trims,
                               'extends': [[round(x), round(y)] for x, y in ext_l + ext_r],
                               'ext_conn': conn,
                               'ext_short': [int(max(0, full[:, 0].min() - lstop)),
                                             int(max(0, rstop - full[:, 0].max()))]})
        chosen_all |= chosen
        stats[kind] = {'pieces': len(chosen), 'groups': len(groups_out),
                       'fills': sum(len(g['fills']) for g in groups_out),
                       'unfilled': sum(len(g['unfilled']) for g in groups_out),
                       'extends': sum(len(g['extends']) for g in groups_out),
                       'ext_short': [[g['ext_short'][0], g['ext_short'][1]] for g in groups_out]}
        result[kind] = {'groups': groups_out}
    for sid in hs:                        # 未选中碎片只分类一次（防上下两轮重复计数）
        if sid in chosen_all:
            continue
        p = hs[sid]
        rt = p[:, 1] - c_top(p[:, 0])
        rb = p[:, 1] - c_bot(p[:, 0])
        if np.abs(rt).min() <= TOL or np.abs(rb).min() <= TOL:
            outside['inside'].append(sid)     # 带内但未达选择标准（行线等）
        elif rt.mean() < 0:
            outside['above'].append(sid)      # 顶框上方：装饰框等，忽略
        elif rb.mean() > 0:
            outside['below'].append(sid)      # 底框下方：图签框、装饰框底等，忽略
        else:
            outside['inside'].append(sid)
    result['outside'] = {k: sorted(v) for k, v in outside.items()}
    # 角点标记 = 框链端实测位置 + 证据曲线 y（诚实反映实际到达的角点）；
    # 无框组时退回边界线推算值。
    for kind, curve, ck_l, ck_r in (('top', c_top, 'corner_tl', 'corner_tr'),
                                    ('bottom', c_bot, 'corner_bl', 'corner_br')):
        gs = result[kind]['groups']
        if gs:
            gp = max((np.asarray(g['pts'], float) for g in gs),
                     key=lambda a: float(np.ptp(a[:, 0])))
            result['evidence'][ck_l] = [round(float(gp[:, 0].min())),
                                        round(float(curve(float(gp[:, 0].min()))))]
            result['evidence'][ck_r] = [round(float(gp[:, 0].max())),
                                        round(float(curve(float(gp[:, 0].max()))))]
    return result, stats, cj


def render(stem, cj, result):
    viz = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_COLOR)
    lines = [l for l in json.load(open(paths.RUNS_DIR / 'table_reconstruct' /
             f'{stem}_分割线.json', encoding='utf-8'))['lines']]
    hs = {s['id']: np.asarray(s['points'], np.int32) for s in cj['lines']
          if s['direction'] == 'horizontal' and s['label'] == 'high'}
    vs = {s['id']: np.asarray(s['points'], np.int32) for s in cj['lines']
          if s['direction'] == 'vertical' and s['label'] == 'high'}
    used_v = {sid for ln in lines for sid in ln.get('_orig_ids', [])}
    quiet = set(result['outside']['above']) | set(result['outside']['below']) \
        | set(result['outside']['inside'])

    dim = np.zeros(viz.shape[:2], bool)
    for sid, p in vs.items():
        if sid not in used_v:
            cv2.polylines(dim, [p.reshape(-1, 1, 2)], False, True, 3)
    for sid in hs:
        if sid in quiet:
            cv2.polylines(dim, [hs[sid].reshape(-1, 1, 2)], False, True, 3)
    viz[dim] = (viz[dim] * 0.45).astype(np.uint8)

    for ln in lines:                      # 参照：列线细红、左右边界细绿
        col = (0, 200, 0) if ln['kind'] == 'edge' else (0, 0, 255)
        th = 3 if ln['kind'] == 'edge' else 2
        cv2.polylines(viz, [np.asarray(ln['pts'], np.int32).reshape(-1, 1, 2)],
                      False, col, th, cv2.LINE_AA)
    for kind in ('top', 'bottom'):        # 上下框：原始蓝、补全青、外延橙、未补品红
        for g in result[kind]['groups']:
            gp = np.asarray(g['pts'], float)
            for sid in g['segment_ids']:
                if sid in hs:
                    cv2.polylines(viz, [hs[sid].reshape(-1, 1, 2)], False, (255, 0, 0), 6, cv2.LINE_AA)
            for fl in g['fills']:
                (xa, ya), (xb, yb) = np.asarray(fl['fill'], float)
                cv2.line(viz, (int(xa), int(ya)), (int(xb), int(yb)), (255, 200, 0), 6, cv2.LINE_AA)
            for ex in g['extends']:
                if len(ex) >= 2:
                    arr = np.asarray(ex, np.int32).reshape(-1, 1, 2)
                    cv2.polylines(viz, [arr], False, (0, 165, 255), 6, cv2.LINE_AA)
            for c1, c2 in g.get('ext_conn', []):
                cv2.line(viz, (int(c1[0]), int(c1[1])), (int(c2[0]), int(c2[1])),
                         (0, 165, 255), 6, cv2.LINE_AA)
            for u in g['unfilled']:       # 未补缺口：品红细线 + 中点圆圈标记
                xa, xb = u['x']
                lv, rv = gp[gp[:, 0] <= xa], gp[gp[:, 0] >= xb]
                ya = lv[-1, 1] if len(lv) else float(gp[:, 1].mean())
                yb = rv[0, 1] if len(rv) else float(gp[:, 1].mean())
                cv2.line(viz, (int(xa), int(ya)), (int(xb), int(yb)), (255, 0, 255), 2, cv2.LINE_AA)
                cv2.circle(viz, (int((xa + xb) / 2), int((ya + yb) / 2)), 14,
                           (255, 0, 255), 3, cv2.LINE_AA)
    for key, col in (('corner_tl', (0, 255, 255)), ('corner_tr', (0, 255, 255)),
                     ('corner_bl', (0, 255, 255)), ('corner_br', (0, 255, 255))):
        x, y = result['evidence'][key]
        cv2.circle(viz, (int(x), int(y)), 18, col, 3, cv2.LINE_AA)
    txt = "blue=top/bottom border  cyan=bridged  orange=extended  magenta=unfilled  thin red/green=cols/edges  dim=content+deco"
    cv2.putText(viz, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 5, cv2.LINE_AA)
    cv2.putText(viz, txt, (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_外框叠加图.png'),
                viz, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    half = cv2.resize(viz, (viz.shape[1] // 2, viz.shape[0] // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_外框叠加图_预览.jpg'),
                half, [cv2.IMWRITE_JPEG_QUALITY, 85])


def main():
    only = sys.argv[1:] or sorted('%d' % i for i in range(1015, 1045))
    summary = {}
    for n in only:
        stem = '钻孔柱状图' + n
        result, stats, cj = process(stem)
        render(stem, cj, result)
        json.dump(result, open(paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_上下框.json', 'w',
                               encoding='utf-8'), ensure_ascii=False, indent=1)
        t, b = stats['top'], stats['bottom']
        print(n, '顶框:片%d组%d补%d延%d未补%d 端差%s | 底框:片%d组%d补%d延%d未补%d 端差%s | 外部:上%d下%d带内%d'
              % (t['pieces'], t['groups'], t['fills'], t['extends'], t['unfilled'], t['ext_short'],
                 b['pieces'], b['groups'], b['fills'], b['extends'], b['unfilled'], b['ext_short'],
                 len(result['outside']['above']), len(result['outside']['below']),
                 len(result['outside']['inside'])), flush=True)
        summary[n] = stats
    json.dump(summary, open(paths.RUNS_DIR / 'table_reconstruct' / '上下框汇总.json', 'w',
                            encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
