
# -*- coding: utf-8 -*-
"""1023 列#8 逐段解剖: 段(中位x, y0, y1) 按 y 排序。"""
import sys, json
sys.path.insert(0, '.')
import numpy as np
from src.core import paths
D = paths.RUNS_DIR / 'table_reconstruct'
stem = '钻孔柱状图1023'
cs = json.load(open(D / (stem + '_列结构定稿.json'), encoding='utf-8'))
cj = json.load(open(paths.CANDIDATE_COORD_DIR / (stem + '.json'), encoding='utf-8'))
seg = {}
for s in cj['lines']:
    if s.get('direction') != 'vertical' or s.get('label') != 'high':
        continue
    p = np.asarray(s['points'], float)
    seg[str(s['id'])] = (float(np.median(p[:, 0])), float(p[:, 1].min()), float(p[:, 1].max()),
                         float(p[:, 0].max() - p[:, 0].min()))
for c in cs['columns']:
    if c['index'] not in (7, 8):
        continue
    ids = [str(i) for i in (c.get('segment_ids') or [])]
    items = [seg[i] for i in ids if i in seg]
    items.sort(key=lambda q: q[1])
    print('=== 列#%d src=%s  段数=%d  x_at_mid=%s' % (c['index'], c.get('src'), len(items), c.get('x_at_mid')))
    for (mx, y0, y1, w) in items:
        print('   x=%7.1f  y[%7.1f..%7.1f]  len=%6.1f  宽=%.1f' % (mx, y0, y1, y1-y0, w))
