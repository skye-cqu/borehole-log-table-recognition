
# -*- coding: utf-8 -*-
"""混线缺陷 -> 交付影响: 每条混线列影响多少行(行带), 错位多大。"""
import sys, json
sys.path.insert(0, '.')
import numpy as np
from src.core import paths

TOL = 30.0
D = paths.RUNS_DIR / 'table_reconstruct'
codes = ['1019', '1023', '1024', '1030', '1031', '1033', '1035', '1042']
rows_all = {}
for code in codes:
    stem = '钻孔柱状图' + code
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / (stem + '.json'), encoding='utf-8'))
    seg = {}
    for s in cj['lines']:
        if s.get('direction') != 'vertical' or s.get('label') != 'high':
            continue
        p = np.asarray(s['points'], float)
        seg[str(s['id'])] = (float(np.median(p[:, 0])), float(p[:, 1].min()), float(p[:, 1].max()))
    cs = json.load(open(D / (stem + '_列结构定稿.json'), encoding='utf-8'))
    hm = json.load(open(D / (stem + '_表头映射.json'), encoding='utf-8'))
    rj = json.load(open(D / (stem + '_行判定.json'), encoding='utf-8'))
    rows = rj['rows']
    seps = []
    for j, s in enumerate(hm['sep_pts']):
        ys = np.asarray(s['ys'], float); xs = np.asarray(s['xs'], float)
        o = np.argsort(ys, kind='stable')
        seps.append((j, ys[o], xs[o]))
    # 行带中点 y
    def row_yf(poly, x):
        a = np.asarray(poly, float); o = np.argsort(a[:, 0], kind='stable')
        return float(np.interp(x, a[o, 0], a[o, 1]))
    bands = []
    for i in range(len(rows) - 1):
        p0 = np.asarray(rows[i]['poly'], float); p1 = np.asarray(rows[i+1]['poly'], float)
        bands.append((p0, p1))
    print('=== {}'.format(code))
    for c in cs['columns']:
        ids = [str(i) for i in (c.get('segment_ids') or [])]
        items = [seg[i] for i in ids if i in seg]
        if len(items) < 4:
            continue
        items.sort(key=lambda q: q[1])
        tracks = []; assign = []
        for it in items:
            mx, y0, y1 = it; ymid = 0.5*(y0+y1)
            best = None; besterr = None
            for ti, t in enumerate(tracks):
                dy = ymid - t['ymid']
                sl = float(np.median(t['slopes'])) if t['slopes'] else 0.0
                err = abs(mx - (t['x'] + sl*dy))
                if besterr is None or err < besterr:
                    besterr = err; best = ti
            if best is not None and besterr <= TOL:
                t = tracks[best]; dy = ymid - t['ymid']
                if dy > 0:
                    t['slopes'] = (t['slopes'] + [(mx - t['x'])/dy])[-5:]
                t['x'] = mx; t['ymid'] = ymid
                assign.append(best)
            else:
                tracks.append({'x': mx, 'ymid': ymid, 'slopes': []})
                assign.append(len(tracks)-1)
        grp = {}
        for i, ti in enumerate(assign):
            grp.setdefault(ti, []).append(items[i])
        info = []
        for ti, g in grp.items():
            info.append({'n': len(g), 'x': float(np.median([q[0] for q in g])),
                         'y0': int(min(q[1] for q in g)), 'y1': int(max(q[2] for q in g)),
                         'pts': [(q[0], 0.5*(q[1]+q[2])) for q in g]})
        info.sort(key=lambda d: -d['n'])
        if len(info) < 2:
            continue
        main = info[0]
        # 该列的画线
        mx_ = np.asarray([p[0] for p in main['pts']], float); my_ = np.asarray([p[1] for p in main['pts']], float)
        o = np.argsort(my_); mx_ = mx_[o]; my_ = my_[o]
        bestsep = None; bestd = None
        for (j, py, px) in seps:
            ds = [abs(float(np.interp(fy, py, px))-fx) for (fx, fy) in main['pts'] if py[0] <= fy <= py[-1]]
            if not ds: continue
            md = float(np.median(ds))
            if bestd is None or md < bestd:
                bestd = md; bestsep = (j, py, px)
        if bestsep is None: continue
        j, py, px = bestsep
        # 逐行带: 画线与主轨的偏差
        devs = []
        for bi, (p0, p1) in enumerate(bands):
            if not (p0[:, 0].min() <= 700 <= p0[:, 0].max()):
                continue
            ymid = 0.5*(row_yf(p0, 700)+row_yf(p1, 700))
            if not (py[0] <= ymid <= py[-1]):
                continue
            if not (my_[0] <= ymid <= my_[-1]):
                continue
            xsep = float(np.interp(ymid, py, px))
            xmain = float(np.interp(ymid, my_, mx_))
            devs.append((bi, int(ymid), xsep - xmain))
        bad = [d for d in devs if abs(d[2]) > 10]
        if not bad:
            continue
        ybad0 = min(d[1] for d in bad); ybad1 = max(d[1] for d in bad)
        mx_dev = max(abs(d[2]) for d in bad)
        print('   列#%s src=%s (sep#%d): 画线偏离本列主轨 |dx|>10px 的行带 %d/%d, y[%d..%d], 最大偏离 %.1fpx' % (
            c['index'], c.get('src'), j, len(bad), len(devs), ybad0, ybad1, mx_dev))
        rows_all.setdefault(code, []).append((c['index'], c.get('src'), len(bad), len(devs), ybad0, ybad1, round(mx_dev,1)))
json.dump(rows_all, open('runs/tmp/t33_impact.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
