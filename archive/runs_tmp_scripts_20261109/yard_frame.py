# -*- coding: utf-8 -*-
"""外框与列线的"能不能连成近似矩形"标尺(用户 2026-09-27 定的验收口径)。

量的三件事:
① **连得起来**:左/右框边(kind=edge)的 y 覆盖、上下框(6d `_上下框.json`)的 x 覆盖,断口逐条出账;
② **近似矩形**:左边 x 从表顶到表底的漂移、左右两边是否各自单调不折返、四角的相对位置;
③ **边上不许突然大跳转**:每个断口两侧端点的横向错位 dx(纵向边)、纵向错位 dy(横向边),
   以及段内相邻点的最大单跳。

参照物用两把,免得自证:
  R1 = 原图"真竖线墨"(自适应二值→1×40 竖条开运算→25px 竖向闭运算,与 yard_cols 同口径),
       在表高范围内取**最左边**一簇竖墨 = 真左框应该在哪;横向同理取真顶/真底。
  R2 = 6e `_闭合外框.json` 的 corners(独立阶段算出来的四角)。

只读,不改任何产物。用法: python runs/tmp/yard_frame.py [1024 1042]   # 无参数=30 张
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.core import paths                                          # noqa: E402
from src.table import col_segments as cs                            # noqa: E402
from src.table import track_rows as tr                              # noqa: E402

VLEN, CLOSE = 40, 25          # 与 yard_cols 同口径
JUMP = 25.0                   # 断口两侧端点错位超过此值 = "突然的大跳转"
STEP = 12.0                   # 段内相邻点单跳横向位移上限(纵向边)
MIN_GAP = 50.0                # 断口出账下限


def vmask(stem):
    gray = cv2.imread(str(paths.RAW_DIR / f"{stem}.JPG"), cv2.IMREAD_GRAYSCALE)
    bw = (cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY_INV, 31, 12) > 0).astype(np.uint8) * 255
    v = cv2.morphologyEx(bw, cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_RECT, (1, VLEN)))
    v = cv2.morphologyEx(v, cv2.MORPH_CLOSE, np.ones((CLOSE, 1), np.uint8))
    h = cv2.morphologyEx(bw, cv2.MORPH_OPEN,
                         cv2.getStructuringElement(cv2.MORPH_RECT, (60, 1)))
    return v, h


def side_book(rec, y_lo, y_hi):
    """一条纵向边/列线 → dict(覆盖、断口、大跳转、段内最大单跳)。"""
    ps = [np.asarray(p, float) for p, _ in rec['parts']]
    ps += [np.asarray(p, float) for p, _ in rec['bridged']]
    ps.sort(key=lambda a: a[0, 1])
    if not ps:
        return None
    cov = sum(float(np.ptp(a[:, 1])) for a in ps)
    tot = y_hi - y_lo
    mis, mx = [], 0.0
    for a, b in zip(ps, ps[1:]):
        g = float(b[0, 1] - a[-1, 1])
        if g >= MIN_GAP:                       # 断口两侧端点的横向错位
            mis.append((round(a[-1, 1]), round(b[0, 1]), round(float(b[0, 0] - a[-1, 0]), 1)))
            mx = max(mx, abs(b[0, 0] - a[-1, 0]))
    jump = max([float(np.abs(np.diff(a[:, 0])).max()) for a in ps if len(a) > 1] or [0.0])
    return {'cov': cov / max(1.0, tot) * 100, 'gaps': len(mis), 'mis': mis, 'max_mis': mx,
            'max_step': jump, 'y0': float(ps[0][0, 1]), 'y1': float(ps[-1][-1, 1]),
            'x0': float(ps[0][0, 0]), 'xm': float(np.median(np.vstack(ps)[:, 0])),
            'x1': float(ps[-1][-1, 0]), 'n': len(ps)}


def clusters(cov, thr):
    """一维覆盖序列 → 覆盖≥thr 的簇中心列表。"""
    out, x, n = [], 0, len(cov)
    while x < n:
        if cov[x] >= thr:
            y = x
            while y + 1 < n and cov[y + 1] >= thr:
                y += 1
            c = (x + y) // 2
            out.append((c, float(cov[x:y + 1].max())))
            x = y + 1
        else:
            x += 1
    return out


def sheet(stem):
    book = cs.line_parts(stem)
    cols = [l for l in book['lines'] if l['kind'] == 'column']
    edges = {l['side']: l for l in book['lines'] if l['kind'] == 'edge'}
    v, h = vmask(stem)
    H, W = v.shape
    yv = np.array([p[1] for l in cols for pts, _ in l['parts'] for p in pts])
    y_lo, y_hi = float(yv.min()), float(yv.max())
    # R1: 表高范围内的真竖墨簇(每条 x 有多少比例的高度上有真竖墨)
    rows = np.round(np.linspace(y_lo, y_hi, 200)).astype(int)
    vcl = clusters((v[rows, :] > 0).mean(axis=0), 0.45)
    r = {'code': stem[-4:], 'n_cols': len(cols), 'n_edges': len(edges),
         'y': (round(y_lo), round(y_hi)), 'W': W, 'H': H,
         'vcl': [c for c, _ in vcl], 'vpeak': {c: round(p, 2) for c, p in vcl}}
    for side in ('left', 'right'):
        r[side] = side_book(edges[side], y_lo, y_hi) if side in edges else None
    r['cols'] = [side_book(l, y_lo, y_hi) for l in cols]
    # 真顶/真底:在左右边之间、全图高度上,横墨占表宽比例高的 y 簇
    L, Rt = r['left'], r['right']
    if L and Rt:
        xa, xb = int(min(L['xm'], Rt['xm'])), int(max(L['xm'], Rt['xm']))
        xs = np.linspace(xa, xb, 300).astype(int)
        hcl = clusters((h[:, xs] > 0).mean(axis=1), 0.5)
        r['hcl'] = [c for c, _ in hcl]
    else:
        r['hcl'] = []
    # 上下框(6d 自己算的那一套)
    tj = paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_上下框.json'
    tf = {}
    if tj.exists():
        d = json.load(open(tj, encoding='utf-8'))
        for kind in ('top', 'bottom'):
            gs = d.get(kind, {}).get('groups', [])
            ps = [np.asarray(g['pts'], float) for g in gs if g.get('pts')]
            if not ps:
                tf[kind] = {'n': 0}
                continue
            ps.sort(key=lambda a: a[0, 0])
            cov = sum(float(np.ptp(a[:, 0])) for a in ps)
            x_lo = min(a[:, 0].min() for a in ps)
            x_hi = max(a[:, 0].max() for a in ps)
            tab = ((r['right']['xm'] - r['left']['xm']) if (r['left'] and r['right']) else W)
            mis = [(round(a[-1, 0]), round(b[0, 0]), round(float(b[0, 1] - a[-1, 1]), 1))
                   for a, b in zip(ps, ps[1:]) if b[0, 0] - a[-1, 0] >= MIN_GAP]
            tf[kind] = {'n': len(ps), 'cov': cov / max(1.0, tab) * 100,
                        'x': (round(x_lo), round(x_hi)),
                        'y0': round(float(np.median(ps[0][:, 1]))),
                        'y1': round(float(np.median(ps[-1][:, 1]))),
                        'gaps': len(mis), 'max_mis': max([abs(m[2]) for m in mis] or [0.0]),
                        'unfilled': sum(len(g.get('unfilled', [])) for g in gs)}
    r['frame'] = tf
    cf = paths.RUNS_DIR / 'table_reconstruct' / f'{stem}_闭合外框.json'
    r['corners'] = json.load(open(cf, encoding='utf-8'))['corners'] if cf.exists() else None
    del v, h
    return r


def near(xs, c, tol=12):
    return xs and min(abs(c - x) for x in xs) <= tol


def fmt(code, r):
    L, Rt = r['left'], r['right']
    xs = [x['xm'] for x in r['cols'] if x] + [s['xm'] for s in (L, Rt) if s]
    tab = [c for c in r['vcl'] if L and Rt and min(L['xm'], Rt['xm']) - 20 <= c <= max(L['xm'], Rt['xm']) + 20]
    miss = [c for c in tab if not near(xs, c)]
    def s(x, k, f='{:.0f}'):
        return f.format(x[k]) if x else '—'
    print(f"{code}: 列线{r['n_cols']:>2} 框边{r['n_edges']} 表y{r['y'][0]}~{r['y'][1]} "
          f"真竖墨簇{len(r['vcl'])}个 最左簇{r['vcl'][0] if r['vcl'] else '—'} "
          f"框内簇{len(tab)} 没线贴着{len(miss)}{miss[:4]}")
    for nm, x in (('左', L), ('右', Rt)):
        if x:
            print(f"    {nm}边 覆{x['cov']:>5.0f}% y{x['y0']:.0f}~{x['y1']:.0f} "
                  f"x {x['x0']:.0f}→{x['xm']:.0f}→{x['x1']:.0f}(顶到底漂{x['x1'] - x['x0']:+.0f}px) "
                  f"段{x['n']} 断口{x['gaps']} 最大错位{x['max_mis']:.0f}px 段内最大单跳{x['max_step']:.0f}px")
        else:
            print(f"    {nm}边 缺档")
    for k in ('top', 'bottom'):
        t = r['frame'].get(k)
        if t and t.get('n'):
            print(f"    {'顶' if k == 'top' else '底'}框 x{t['x'][0]}~{t['x'][1]} 覆表宽{t['cov']:.0f}% "
                  f"y{t['y0']}~{t['y1']} 组{t['n']} 断口{t['gaps']} 最大错位{t['max_mis']:.0f}px 未补{t['unfilled']}")
        else:
            print(f"    {'顶' if k == 'top' else '底'}框 无组")
    short = [(i, c) for i, c in enumerate(r['cols']) if c and c['cov'] < 90]
    none = [i for i, c in enumerate(r['cols']) if not c or c['n'] == 0]
    for i, c in sorted(short, key=lambda u: u[1]['cov'])[:5]:
        print(f"    列线#{i} x≈{c['xm']:.0f} 覆{c['cov']:.0f}% 段{c['n']} 断口{c['gaps']} "
              f"最大错位{c['max_mis']:.0f}px 段内单跳{c['max_step']:.0f}px")
    if len(short) > 5:
        print(f"    ...另有 {len(short) - 5} 条覆盖<90%")
    big = [(nm, x) for nm, x in (('左', L), ('右', Rt)) if x and x['max_step'] > STEP]
    for nm, x in big:
        print(f"    {nm}边段内单跳 {x['max_step']:.0f}px > {STEP:.0f}px(边上突然跳转)")
    return miss, short, none


def main():
    codes = [a for a in sys.argv[1:] if a.isdigit()] or \
            sorted(p.stem[-4:] for p in paths.CANDIDATE_COORD_DIR.glob('*.json'))
    tot = dict(no_edge=0, big_mis=0, cov=0, jump=0, short=0, miss=0, none=0)
    for c in codes:
        r = sheet(f'钻孔柱状图{c}')
        miss, short, none = fmt(c, r)
        tot['miss'] += len(miss)
        tot['short'] += len(short)
        tot['none'] += len(none)
        for side in ('left', 'right'):
            s_ = r[side]
            if not s_:
                tot['no_edge'] += 1
                continue
            if s_['cov'] < 95:
                tot['cov'] += 1
            if s_['max_mis'] > JUMP:
                tot['big_mis'] += 1
            if s_['max_step'] > STEP:
                tot['jump'] += 1
    print(f"\n合计 {len(codes)} 张: 框边缺档 {tot['no_edge']}  框边覆盖<95% {tot['cov']}  "
          f"框边错位>{JUMP:.0f}px {tot['big_mis']}  框边段内单跳>{STEP:.0f}px {tot['jump']}  "
          f"列线覆盖<90% {tot['short']}  列线一段都没有 {tot['none']}  "
          f"框内有真竖墨却没线的簇 {tot['miss']}")


if __name__ == '__main__':
    main()
