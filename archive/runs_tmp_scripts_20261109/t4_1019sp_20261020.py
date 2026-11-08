
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1019'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
print('n_sep',hm['n_sep'],'len sep_pts',len(hm['sep_pts']))
print('sep_x_band',hm['sep_x_band'])
print('keep',[(i,c['name'],c['left_sep'],c['right_sep'],c['x_in_band']) for i,c in enumerate(hm['keep'])])
for i,sp in enumerate(hm['sep_pts']):
    ys=np.asarray(sp['ys'],float); xs=np.asarray(sp['xs'],float)
    print('#%d kind=%s index=%s side=%s npts=%d y=[%.0f,%.0f] x=[%.0f,%.0f] x@mid=%.1f'%(
        i,sp.get('kind'),sp.get('index'),sp.get('side'),len(ys),ys.min(),ys.max(),xs.min(),xs.max(),
        float(np.interp((ys.min()+ys.max())/2,ys,xs))))
