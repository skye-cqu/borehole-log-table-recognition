
# -*- coding: utf-8 -*-
"""全库"列线混线"检测 v2: 修正 id 类型。"""
import sys, json
sys.path.insert(0, '.')
import numpy as np
from src.core import paths

XCLUST = 20.0
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
    tot = 0
    for c in cs['columns']:
        ids = [str(i) for i in (c.get('segment_ids') or [])]
        items = [seg[i] for i in ids if i in seg]
        tot += len(items)
        if not items:
            continue
        items.sort()
        cl = [[items[0]]]
        for it in items[1:]:
            if it[0] - cl[-1][-1][0] <= XCLUST:
                cl[-1].append(it)
            else:
                cl.append([it])
        if len(cl) > 1:
            info = []
            for g in cl:
                info.append((round(float(np.median([q[0] for q in g])), 1),
                             int(min(q[1] for q in g)), int(max(q[2] for q in g)), len(g)))
            info.sort(key=lambda t: -t[3])
            mixed.append((c['index'], c.get('src'), info))
    summary[code] = [(m[0], m[1], m[2]) for m in mixed]
    if mixed:
        print('=== {}  列数{}  段总数{}  混线列{}'.format(code, len(cs['columns']), tot, len(mixed)))
        for idx, src, info in mixed:
            s = '  |  '.join('x=%.1f y[%d..%d] %d段' % t for t in info)
            print('   列#%d (src=%s): %s' % (idx, src, s))
    else:
        print('=== {}  列数{}  段总数{}  混线列 0'.format(code, len(cs['columns']), tot))
print('\n合计混线: {} 图 / {} 条'.format(sum(1 for v in summary.values() if v),
                                      sum(len(v) for v in summary.values())))
json.dump(summary, open('runs/tmp/t23_mixline_lib.json', 'w', encoding='utf-8'),
          ensure_ascii=False, indent=1)
