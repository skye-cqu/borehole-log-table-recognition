
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1042'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
k0=hm['keep'][0]
sl=hm['sep_pts'][k0['left_sep']]; sr=hm['sep_pts'][k0['right_sep']]
for y in [900,2000,5000,9000,13000,17000,19700]:
    L=float(np.interp(y,sl['ys'],sl['xs'])); R=float(np.interp(y,sr['ys'],sr['xs']))
    print('y=%5d L=%6.1f R=%6.1f width=%6.1f'%(y,L,R,R-L))
print()
print('left pts:',[(round(a),round(b)) for a,b in zip(sl['ys'],sl['xs'])])
