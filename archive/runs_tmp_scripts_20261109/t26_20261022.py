
# -*- coding: utf-8 -*-
"""全库"列线混线"终判: 按 y 顺序跟踪每条列线的物理轨迹(局部趋势预测)。

物理线 = 沿 y 单调、x 随局部斜率平滑漂移的一组段。
若某列的段序列被迫分成两条互不相同的轨迹 => 该列混入了另一条物理线。
"""
import sys, json
sys.path.insert(0, '.')
import numpy as np
from src.core import paths

TOL = 30.0        # 可接受的最大局部偏离(px)
D = paths.RUNS_DIR / 'table_reconstruct'
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
    mixed = []
    for c in cs['columns']:
        ids = [str(i) for i in (c.get('segment_ids') or [])]
        items = [seg[i] for i in ids if i in seg]
        if len(items) < 4:
            continue
        items.sort(key=lambda q: q[1])
        tracks = []   # {x, ymid, slopes[]}
        assign = []
        for (mx, y0, y1) in items:
            ymid = 0.5 * (y0 + y1)
            best = None; besterr = None
            for ti, t in enumerate(tracks):
                dy = ymid - t['ymid']
                sl = float(np.median(t['slopes'])) if t['slopes'] else 0.0
                pred = t['x'] + sl * dy
                err = abs(mx - pred)
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
        if len(tracks) > 1:
            grp = {}
            for i, ti in enumerate(assign):
                grp.setdefault(ti, []).append(items[i])
            info = []
            for ti, g in grp.items():
                info.append((len(g), round(float(np.median([q[0] for q in g])), 1),
                             int(min(q[1] for q in g)), int(max(q[2] for q in g))))
            info.sort(key=lambda t: -t[0])
            if len(info) > 1 and info[1][0] >= 2:
                mixed.append((c['index'], c.get('src'), info))
    summary[code] = [(m[0], m[1], m[2]) for m in mixed]
    if mixed:
        print('=== {}  混线列 {}'.format(code, len(mixed)))
        for idx, src, info in mixed:
            s = '  |  '.join('%d段 x=%.1f y[%d..%d]' % t for t in info)
            print('   列#%d (src=%s): %s' % (idx, src, s))
    else:
        print('=== {}  混线列 0'.format(code))
print('\n合计: {} 图存在混线列, 共 {} 条'.format(sum(1 for v in summary.values() if v),
                                      sum(len(v) for v in summary.values())))
json.dump(summary, open('runs/tmp/t26_mixline_lib.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
