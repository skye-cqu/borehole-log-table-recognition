
# -*- coding: utf-8 -*-
"""调试: 1023 列#8 混入段的归属匹配过程。"""
import sys, json
sys.path.insert(0, '.')
import numpy as np
from src.core import paths
D = paths.RUNS_DIR / 'table_reconstruct'
stem = '钻孔柱状图1023'
cj = json.load(open(paths.CANDIDATE_COORD_DIR / (stem + '.json'), encoding='utf-8'))
seg = {}
for s in cj['lines']:
    if s.get('direction') != 'vertical' or s.get('label') != 'high':
        continue
    p = np.asarray(s['points'], float)
    seg[str(s['id'])] = (float(np.median(p[:, 0])), float(p[:, 1].min()), float(p[:, 1].max()))
cs = json.load(open(D / (stem + '_列结构定稿.json'), encoding='utf-8'))
tracks_of = {}
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
        if best is not None and besterr <= 30.0:
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
        info.append({'n': len(g), 'pts': [(q[0], 0.5*(q[1]+q[2])) for q in g]})
    info.sort(key=lambda d: -d['n'])
    tracks_of[c['index']] = info
    print('列#%d src=%s 轨道数=%d  各轨: %s' % (
        c['index'], c.get('src'), len(info),
        ' | '.join('n=%d x中位=%.1f' % (d['n'], np.median([p[0] for p in d['pts']])) for d in info)))
print()
sec = tracks_of[8][1]
print('列#8 第2轨 13 段逐点归属:')
for (px, py) in sec['pts']:
    cand = []
    for ci, info in tracks_of.items():
        if ci == 8: continue
        for ti, tr in enumerate(info):
            if tr['n'] < 3: continue
            xs = np.asarray([p[0] for p in tr['pts']], float)
            ys = np.asarray([p[1] for p in tr['pts']], float)
            o = np.argsort(ys); xs = xs[o]; ys = ys[o]
            if ys[0] <= py <= ys[-1]:
                xi = float(np.interp(py, ys, xs))
                cand.append((abs(xi-px), ci, ti, round(xi,1)))
    cand.sort()
    print('   段(x=%.1f, y=%.0f) 最近匹配: %s' % (px, py,
          '  '.join('列#%d轨%d@%.1f 差%.1f' % (c[1], c[2], c[3], c[0]) for c in cand[:3])))
