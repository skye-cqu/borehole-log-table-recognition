
# -*- coding: utf-8 -*-
"""列结构定稿每条列的 src(=原 track 编号) 与 Agnes 判定对照。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
v=json.load(open(D/f'{stem}_全竖线判定.json',encoding='utf-8'))
vm={int(k):x for k,x in v['merged_by_track'].items()}
print('列结构定稿 columns:')
print(' idx  src(track)  x_at_mid   Agnes判定   碎片数')
for c in cs['columns']:
    src=c.get('src'); 
    try: k=int(src)
    except: k=None
    print(' %-4d %-11s %9.1f   %-9s  %d'%(c['index'],src,c['x_at_mid'],vm.get(k,'未判'),len(c['segment_ids'])))
print()
print('frames:')
for f in cs['frames']:
    print('   src=%s x_at_mid=%.1f 碎片=%d'%(f.get('src'),f['x_at_mid'],len(f['segment_ids'])))
print()
print('Agnes 判 column 的 track:',sorted(g for g,x in vm.items() if x=='column'))
print('列结构定稿的 src     :',sorted(str(c.get('src')) for c in cs['columns']))

