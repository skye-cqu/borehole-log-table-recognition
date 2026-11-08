
# -*- coding: utf-8 -*-
"""混线列定性: 第二条轨迹是"邻列的线"(映射错位) 还是 "非列线"(图形边)?

判据: 第二轨迹在 y 处的 x, 是否与任一邻列主轨迹在该 y 的 x 相符(<25px)
      相符 => 片段是从邻列偷来的(列映射错位)
      不符 => 是图内非列线(被误吸入)
"""
import sys, json
sys.path.insert(0, '.')
import numpy as np
from src.core import paths

TOL = 30.0
D = paths.RUNS_DIR / 'table_reconstruct'
codes = [str(c) for c in range(1015, 1045)]
report = {}
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
    # 先算出每列的轨迹
    coltr = []
    for c in cs['columns']:
        ids = [str(i) for i in (c.get('segment_ids') or [])]
        items = [seg[i] for i in ids if i in seg]
        items.sort(key=lambda q: q[1])
        tracks = []
        assign = []
        for (mx, y0, y1) in items:
            ymid = 0.5 * (y0 + y1)
            best = None; besterr = None
            for ti, t in enumerate(tracks):
                dy = ymid - t['ymid']
                sl = float(np.median(t['slopes'])) if t['slopes'] else 0.0
                err = abs(mx - (t['x'] + sl * dy))
                if besterr is None or err < besterr:
                    besterr = err; best = ti
            if best is not None and besterr <= TOL:
                t = tracks[best]
                dy = ymid - t['ymid']
                if dy > 0:
                    t['slopes'] = (t['slopes'] + [(mx - t['x']) / dy])[-5:]
                t['x'] = mx; t['ymid'] = ymid
                assign.append(best)
            else:
                tracks.append({'x': mx, 'ymid': ymid, 'slopes': []})
                assign.append(len(tracks) - 1)
        grp = {}
        for i, ti in enumerate(assign):
            grp.setdefault(ti, []).append(items[i])
        info = []
        for ti, g in grp.items():
            info.append({'n': len(g),
                         'x': float(np.median([q[0] for q in g])),
                         'y0': int(min(q[1] for q in g)), 'y1': int(max(q[2] for q in g)),
                         'pts': [(float(q[0]), 0.5*(q[1]+q[2])) for q in g]})
        info.sort(key=lambda d: -d['n'])
        coltr.append({'index': c['index'], 'src': c.get('src'), 'tracks': info})
    # 判定
    out = []
    for ci, col in enumerate(coltr):
        if len(col['tracks']) < 2:
            continue
        main = col['tracks'][0]
        for sec in col['tracks'][1:]:
            if sec['n'] < 2:
                continue
            # 第二轨迹代表点(取其中位 y 处)
            x2 = sec['x']; y2 = 0.5*(sec['y0']+sec['y1'])
            owner = None
            for cj2 in coltr:
                if cj2 is col:
                    continue
                for tr in cj2['tracks']:
                    if tr['n'] < 3:
                        continue
                    xs = [p[0] for p in tr['pts']]
                    ys = [p[1] for p in tr['pts']]
                    o = np.argsort(ys)
                    if ys[o][0] <= y2 <= ys[o][-1]:
                        xi = float(np.interp(y2, np.asarray(ys)[o], np.asarray(xs)[o]))
                        if abs(xi - x2) < 25:
                            owner = (cj2['index'], cj2['src'], round(xi,1))
            out.append({'col': col['index'], 'src': col['src'],
                        'main_n': main['n'], 'main_x': round(main['x'],1),
                        'main_y': [main['y0'], main['y1']],
                        'sec_n': sec['n'], 'sec_x': round(sec['x'],1),
                        'sec_y': [sec['y0'], sec['y1']],
                        'stolen_from': owner})
    if out:
        print('=== {}'.format(code))
        for o in out:
            kind = ('邻列#%d(src=%s)的线 @x=%.1f' % o['stolen_from']) if o['stolen_from'] else '非列线(图内图形边)'
            print('   列#%d src=%s | 主轨 %d段 x=%.1f y[%d..%d] | 混入 %d段 x=%.1f y[%d..%d] -> %s' % (
                o['col'], o['src'], o['main_n'], o['main_x'], o['main_y'][0], o['main_y'][1],
                o['sec_n'], o['sec_x'], o['sec_y'][0], o['sec_y'][1], kind))
        report[code] = out
json.dump(report, open('runs/tmp/t27_mixkind.json','w',encoding='utf-8'), ensure_ascii=False, indent=1)
