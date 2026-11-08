
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
print('sep_x_band (标量,x at band mid-y):',[round(x,1) for x in hm['sep_x_band']])
print()
print('sep_pts 是折线吗? 逐条看 y 跨度内的 x 漂移:')
for i,sp in enumerate(hm['sep_pts']):
    ys=np.asarray(sp['ys'],float); xs=np.asarray(sp['xs'],float)
    if len(ys)<2: 
        print('  #%d 单点'%i); continue
    # drift across the crop range 560..1560
    lo,hi=max(560,ys.min()),min(1560,ys.max())
    if hi<=lo:
        print('  #%d y=[%.0f,%.0f] 不在裁片范围'%(i,ys.min(),ys.max())); continue
    xa=float(np.interp(lo,ys,xs)); xb=float(np.interp(hi,ys,xs))
    print('  #%d kind=%-6s npts=%-5d y=[%5.0f,%5.0f]  x@560=%6.1f  x@1560=%6.1f  drift=%+6.1f'%(
        i,sp.get('kind'),len(ys),ys.min(),ys.max(),xa,xb,xb-xa))
