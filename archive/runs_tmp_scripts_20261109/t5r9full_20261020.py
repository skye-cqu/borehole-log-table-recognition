
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1030'
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
r=rd['rows'][9]; p=np.asarray(r['poly'],float)
print('row9 npts',len(p))
for a,b in p:
    print('  x=%6.0f y=%.1f'%(a,b))
