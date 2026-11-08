
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
print('image', gray.shape)
for i,sp in enumerate(hm['sep_pts']):
    ys=np.asarray(sp['ys'],float); xs=np.asarray(sp['xs'],float)
    print('#%-2d kind=%-7s n=%3d y[%6.0f,%6.0f] x[%7.1f,%7.1f] xmid=%7.1f'%(
        i, sp.get('kind'), len(xs), ys.min(), ys.max(), xs.min(), xs.max(), float(np.interp((ys.min()+ys.max())/2, ys, xs))))
print()
print('columns:')
for c in hm['columns']:
    print('  ', c.get('name'), c.get('left'), c.get('right'))

