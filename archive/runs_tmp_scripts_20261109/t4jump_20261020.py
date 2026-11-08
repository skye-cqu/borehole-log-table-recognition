
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1019'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
sp=hm['sep_pts'][1]
ys=np.asarray(sp['ys'],float); xs=np.asarray(sp['xs'],float)
print('npts',len(ys))
# find jumps > 20px between consecutive samples within 60 y
order=np.argsort(ys); ys=ys[order]; xs=xs[order]
for i in range(1,len(ys)):
    if abs(xs[i]-xs[i-1])>20 and (ys[i]-ys[i-1])<80:
        print('  JUMP at i=%d y %.0f->%.0f  x %.0f->%.0f'%(i,ys[i-1],ys[i],xs[i-1],xs[i]))
print()
print('samples:')
for y in [1000,2000,3000,4000,4200,4400,4600,5000,6000,8000,10000,12000,14000,16000,17400]:
    print('  y=%5d x=%7.1f'%(y,float(np.interp(y,ys,xs))))
