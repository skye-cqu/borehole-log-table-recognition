
# -*- coding: utf-8 -*-
"""列 <-> sep_pts 映射核对 + 画线与自身段的一致性(全库)。"""
import sys, json
sys.path.insert(0, '.')
import numpy as np
from src.core import paths

D = paths.RUNS_DIR / 'table_reconstruct'
code = sys.argv[1] if len(sys.argv) > 1 else '1023'
stem = '钻孔柱状图' + code
hm = json.load(open(D / (stem + '_表头映射.json'), encoding='utf-8'))
cs = json.load(open(D / (stem + '_列结构定稿.json'), encoding='utf-8'))
cj = json.load(open(paths.CANDIDATE_COORD_DIR / (stem + '.json'), encoding='utf-8'))
seg = {}
for s in cj['lines']:
    if s.get('direction') != 'vertical' or s.get('label') != 'high':
        continue
    p = np.asarray(s['points'], float)
    seg[str(s['id'])] = (float(np.median(p[:, 0])), float(p[:, 1].min()), float(p[:, 1].max()))

print('--- sep_pts 索引表')
for j, s in enumerate(hm['sep_pts']):
    print('  sep_pts[%2d] kind=%-6s index=%-4s side=%-5s x范围[%.1f..%.1f] n=%d' % (
        j, s.get('kind'), s.get('index'), s.get('side'), min(s['xs']), max(s['xs']), len(s['xs'])))
print('--- 列结构定稿 列表')
for c in cs['columns']:
    ids = [str(i) for i in (c.get('segment_ids') or [])]
    items = [seg[i] for i in ids if i in seg]
    xs = sorted(set(round(q[0]) for q in items))
    print('  列#%d src=%-4s x_at_mid=%-8s 段数=%-4d 段x取值=%s' % (
        c['index'], c.get('src'), c.get('x_at_mid'), len(items), xs[:14]))
print('--- frames/content')
print('  frames:', [(f.get('index'), f.get('src'), f.get('x_at_mid')) for f in cs.get('frames', [])])
print('  content:', [(f.get('index'), f.get('src'), f.get('x_at_mid')) for f in cs.get('content', [])])
