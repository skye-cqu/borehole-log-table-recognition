
# -*- coding: utf-8 -*-
"""混线列: 逐段归属判定 + 1比1 证据图。

图例: 蓝=实际画出的 sep_pts 折线; 绿=主轨段; 红=混入段; 黄=原图竖墨
"""
import sys, json, os
sys.path.insert(0, '.')
import numpy as np, cv2
from src.core import paths

TOL = 30.0
D = paths.RUNS_DIR / 'table_reconstruct'
OUT = paths.RUNS_DIR / 'tmp' / 'mixline_20261022'
os.makedirs(str(OUT), exist_ok=True)
codes = [str(c) for c in range(1015, 1045)]
summary = {}
for code in codes:
    stem = '钻孔柱状图' + code
    cj = json.load(open(paths.CANDIDATE_COORD_DIR / (stem + '.json'), encoding='utf-8'))
    seg = {}
    for s in cj['lines']:
        if s.get('direction') != 'vertical' or s.get('label') != 'high':
            continue
        p = np.asarray(s['points'], float)
        seg[str(s['id'])] = (str(s['id']), float(np.median(p[:, 0])),
                             float(p[:, 1].min()), float(p[:, 1].max()))
    cs = json.load(open(D / (stem + '_列结构定稿.json'), encoding='utf-8'))
    hm = json.load(open(D / (stem + '_表头映射.json'), encoding='utf-8'))
    coltr = []
    for c in cs['columns']:
        ids = [str(i) for i in (c.get('segment_ids') or [])]
        items = [seg[i] for i in ids if i in seg]
        items.sort(key=lambda q: q[2])
        tracks = []; assign = []
        for it in items:
            mx = it[1]; ymid = 0.5*(it[2]+it[3])
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
            info.append({'n': len(g), 'x': float(np.median([q[1] for q in g])),
                         'y0': int(min(q[2] for q in g)), 'y1': int(max(q[3] for q in g)),
                         'pts': [(q[1], 0.5*(q[2]+q[3])) for q in g]})
        info.sort(key=lambda d: -d['n'])
        coltr.append({'index': c['index'], 'src': c.get('src'), 'tracks': info})
    mixed = []
    for ci, col in enumerate(coltr):
        if len(col['tracks']) < 2:
            continue
        main = col['tracks'][0]
        for sec in col['tracks'][1:]:
            if sec['n'] < 2:
                continue
            # 逐段找最近邻列轨道
            owners = []
            for (px, py) in sec['pts']:
                best = None; berr = None
                for cj2 in coltr:
                    if cj2 is col:
                        continue
                    for ti, tr in enumerate(cj2['tracks']):
                        if tr['n'] < 3:
                            continue
                        xs = np.asarray([p[0] for p in tr['pts']], float)
                        ys = np.asarray([p[1] for p in tr['pts']], float)
                        o = np.argsort(ys); xs = xs[o]; ys = ys[o]
                        if ys[0] <= py <= ys[-1]:
                            xi = float(np.interp(py, ys, xs))
                            if berr is None or abs(xi-px) < berr:
                                berr = abs(xi-px); best = (cj2['index'], cj2['src'], ti, round(xi,1))
                owners.append((best[0], best[1], round(berr,1)) if best else (None, None, None))
            cnt = {}
            for o in owners:
                cnt[o[0] if o[0] is not None else 'none'] = cnt.get(o[0] if o[0] is not None else 'none', 0) + 1
            dom = max(cnt, key=lambda k: cnt[k])
            mixed.append({'col': col['index'], 'src': col['src'],
                          'main_n': main['n'], 'main_x': round(main['x'],1), 'main_y': [main['y0'], main['y1']],
                          'sec_n': sec['n'], 'sec_x': round(sec['x'],1), 'sec_y': [sec['y0'], sec['y1']],
                          'dom_owner': dom, 'dom_n': cnt[dom], 'owners': owners})
    if not mixed:
        continue
    print('=== {}'.format(code))
    for m in mixed:
        own = ('邻列#%s' % m['dom_owner']) if m['dom_owner'] != 'none' else '无邻列对应(非列线)'
        print('   列#%s src=%s | 主轨 %d段 x=%.1f y[%d..%d] | 混入 %d段 x=%.1f y[%d..%d] | 归属=%s(%d/%d段)' % (
            m['col'], m['src'], m['main_n'], m['main_x'], m['main_y'][0], m['main_y'][1],
            m['sec_n'], m['sec_x'], m['sec_y'][0], m['sec_y'][1], own, m['dom_n'], m['sec_n']))
    summary[code] = mixed
json.dump(summary, open('runs/tmp/t29_mixowner.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
print('\n有混线的图: %s' % list(summary.keys()))
