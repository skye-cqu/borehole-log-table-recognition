
# -*- coding: utf-8 -*-
"""全库"列线混线"检测: 每条列分隔线的 segment_ids 是否混入另一条物理线。"""
import sys, json
sys.path.insert(0, '.')
import numpy as np
from src.core import paths

XCLUST = 20.0
D = paths.RUNS_DIR / 'table_reconstruct'
codes = [str(c) for c in range(1015, 1045)]
res = {}
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
    allcols = []
    for c in cs['columns']:
        ids = c.get('segment_ids') or []
        items = [seg[i] for i in ids if i in seg]
        if not items:
            allcols.append((c['index'], c.get('x_at_mid'), 0, 0))
            continue
        items.sort()
        cl = [[items[0]]]
        for it in items[1:]:
            if it[0] - cl[-1][-1][0] <= XCLUST:
                cl[-1].append(it)
            else:
                cl.append([it])
        cl.sort(key=lambda g: -len(g))
        allcols.append((c['index'], c.get('x_at_mid'), len(items), len(cl)))
        if len(cl) > 1:
            info = []
            for g in cl:
                info.append((round(float(np.median([q[0] for q in g])), 1),
                             int(min(q[1] for q in g)), int(max(q[2] for q in g)), len(g)))
            info.sort(key=lambda t: -t[3])
            mixed.append((c['index'], c.get('src'), info))
    res[code] = mixed
    if mixed:
        print('=== {}  列数 {}  混线列 {}'.format(code, len(cs['columns']), len(mixed)))
        for idx, src, info in mixed:
            s = '  |  '.join('x=%.1f y[%d..%d] %d段' % t for t in info)
            print('   列#%d (src=%s): %s' % (idx, src, s))
    else:
        print('=== {}  列数 {}  混线列 0'.format(code, len(cs['columns'])))
tot = sum(len(v) for v in res.values())
print('\n合计: {} 图存在混线列, 共 {} 条'.format(sum(1 for v in res.values() if v), tot))
json.dump({k: v for k, v in res.items()}, open('runs/tmp/t22_mixline_lib.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1, default=str)
