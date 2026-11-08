
# -*- coding: utf-8 -*-
"""混线列最终定性 + 1比1 证据图。

修正: 归属匹配必须在 err<25px 内才算命中(此前首个候选无条件胜出, 结论无效)。
"""
import sys, json, os
sys.path.insert(0, '.')
import numpy as np, cv2
from src.core import paths

TOL = 30.0
OWNER_TOL = 25.0
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
        seg[str(s['id'])] = (float(np.median(p[:, 0])), float(p[:, 1].min()), float(p[:, 1].max()))
    cs = json.load(open(D / (stem + '_列结构定稿.json'), encoding='utf-8'))
    hm = json.load(open(D / (stem + '_表头映射.json'), encoding='utf-8'))
    coltr = []
    for c in cs['columns']:
        ids = [str(i) for i in (c.get('segment_ids') or [])]
        items = [seg[i] for i in ids if i in seg]
        items.sort(key=lambda q: q[1])
        tracks = []; assign = []
        for it in items:
            mx, y0, y1 = it
            ymid = 0.5*(y0+y1)
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
        coltr.append({'index': c['index'], 'src': c.get('src'), 'tracks': info,
                       'seg_ids': [str(i) for i in (c.get('segment_ids') or [])]})
    mixed = []
    for col in coltr:
        if len(col['tracks']) < 2:
            continue
        main = col['tracks'][0]
        for si, sec in enumerate(col['tracks'][1:], start=1):
            if sec['n'] < 2:
                continue
            # (a) 相对本列主轨的偏离: 用主轨末端斜率外推
            mp = main['pts']
            xs = np.asarray([p[0] for p in mp], float); ys = np.asarray([p[1] for p in mp], float)
            o = np.argsort(ys); xs = xs[o]; ys = ys[o]
            sl_all = (xs[-1]-xs[0])/max(1e-6, (ys[-1]-ys[0]))
            dev = []
            for (px, py) in sec['pts']:
                if ys[0] <= py <= ys[-1]:
                    xi = float(np.interp(py, ys, xs))
                else:
                    xi = xs[-1] + sl_all*(py-ys[-1])
                dev.append(px-xi)
            dev_med = float(np.median(dev))
            # (b) 是否落在邻列的线上
            owners = []
            for (px, py) in sec['pts']:
                bo = None; berr = None
                for cj2 in coltr:
                    if cj2 is col:
                        continue
                    for tr in cj2['tracks']:
                        if tr['n'] < 3:
                            continue
                        ax = np.asarray([p[0] for p in tr['pts']], float)
                        ay = np.asarray([p[1] for p in tr['pts']], float)
                        oo = np.argsort(ay); ax = ax[oo]; ay = ay[oo]
                        if ay[0] <= py <= ay[-1]:
                            xi = float(np.interp(py, ay, ax))
                            if berr is None or abs(xi-px) < berr:
                                berr = abs(xi-px); bo = cj2['index']
                owners.append(bo if (berr is not None and berr < OWNER_TOL) else None)
            cnt = {}
            for o_ in owners:
                k = o_ if o_ is not None else 'none'
                cnt[k] = cnt.get(k, 0) + 1
            dom = max(cnt, key=lambda k: cnt[k])
            mixed.append({'col': col['index'], 'src': col['src'],
                          'main_n': main['n'], 'main_x': round(main['x'],1), 'main_y': [main['y0'], main['y1']],
                          'sec_n': sec['n'], 'sec_x': round(sec['x'],1), 'sec_y': [sec['y0'], sec['y1']],
                          'dev_med': round(dev_med,1), 'owner': dom, 'owner_n': cnt[dom]})
    if not mixed:
        continue
    print('=== {}'.format(code))
    for m in mixed:
        own = ('邻列#%s' % m['owner']) if m['owner'] != 'none' else '非列线(图形边)'
        print('   列#%s src=%s | 主轨 %d段 x=%.1f y[%d..%d] | 混入 %d段 x=%.1f y[%d..%d] | 偏离本列主轨 %+.1fpx | %s(%d/%d)' % (
            m['col'], m['src'], m['main_n'], m['main_x'], m['main_y'][0], m['main_y'][1],
            m['sec_n'], m['sec_x'], m['sec_y'][0], m['sec_y'][1], m['dev_med'], own,
            m['owner_n'], m['sec_n']))
    summary[code] = mixed
json.dump(summary, open('runs/tmp/t31_mixowner.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
