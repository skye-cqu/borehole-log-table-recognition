
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
print('列结构定稿 keys:', list(cs.keys()))
for c in cs['columns']:
    print('  ', {k:v for k,v in c.items() if k in ('x_at_mid','kind','seg_ids','n_seg','note','coverage')})
print()
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
print('表头映射 keys:', list(hm.keys()))
for i,c in enumerate(hm.get('columns',[])):
    print('  col%-2d'%i, c)

