
# -*- coding: utf-8 -*-
"""修正: 用 segment_ids 集合比对(不靠 src 编号), 并按 列/框/内容 分组。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'

def ids_of(o): return frozenset(o.get('segment_ids') or o.get('track_ids') or [])

for code in ('1015','1023'):
    stem='钻孔柱状图'+code
    cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
    print('===',code,'===')
    for grp in ('columns','frames','content'):
        for o in cs.get(grp) or []:
            print('  %-8s src=%-14s n_seg=%-4d ids[:3]=%s'%(grp,str(o.get('src')),len(ids_of(o)),sorted(ids_of(o))[:3]))
    print('  others: n=%d'%len(cs.get('others') or []))
    for o in (cs.get('others') or [])[:3]:
        print('    other src=%-14s n_track=%d ids[:3]=%s'%(str(o.get('src')),len(ids_of(o)),sorted(ids_of(o))[:3]))
    print()

