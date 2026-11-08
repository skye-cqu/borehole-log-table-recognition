
# -*- coding: utf-8 -*-
import sys, json
sys.path.insert(0, '.')
from src.core import paths
D = paths.RUNS_DIR / 'table_reconstruct'
for code in ['1019', '1023']:
    stem = '钻孔柱状图' + code
    hm = json.load(open(D / (stem + '_表头映射.json'), encoding='utf-8'))
    print('===', code, '_表头映射.json top keys:', list(hm.keys()))
    sp = hm.get('sep_pts')
    if sp is not None:
        print('  sep_pts: n=%d  per-item keys=%s' % (len(sp), list(sp[0].keys()) if sp and isinstance(sp[0], dict) else type(sp[0])))
        if sp and isinstance(sp[0], dict):
            for i, s in enumerate(sp):
                xs = s.get('xs'); ys = s.get('ys')
                print('   #%d n=%d x:[%s..%s] y:[%s..%s]' % (
                    i, len(xs), round(min(xs),1), round(max(xs),1), round(min(ys),1), round(max(ys),1)))
    cs = json.load(open(D / (stem + '_列结构定稿.json'), encoding='utf-8'))
    print('  _列结构定稿 top keys:', list(cs.keys()))
    for c in cs['columns'][:3]:
        print('   col keys:', list(c.keys()))
        print('   ', {k: (v if not isinstance(v, list) else ('list[%d]' % len(v))) for k, v in c.items()})
        break
    print()
