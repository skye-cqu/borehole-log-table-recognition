
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table.agnes_all_verify import load_tracks
stem='钻孔柱状图1023'
d,seg,tracks=load_tracks(stem)
print('gidx  x_mid   y_min   y_max   ids数  分给谁(apply_agnes_all 口径)')
hm=json.load(open(paths.RUNS_DIR/'table_reconstruct'/f'{stem}_表头映射.json',encoding='utf-8'))
# 与 sep_pts 对齐: sep_pts[i] 的 x@mid
sp=hm['sep_pts']
spx=[(i,round(float(np.interp((np.asarray(s['ys']).min()+np.asarray(s['ys']).max())/2,
      np.asarray(s['ys']),np.asarray(s['xs']))),1)) for i,s in enumerate(sp)]
for t in tracks:
    p=np.asarray([pt for sid in t['ids'] for pt in seg[sid]['points']],float)
    print(' %-4d %8.1f %7.0f %7.0f  %-5d'%(t['gidx'],t['x_mid'],p[:,1].min(),p[:,1].max(),len(t['ids'])))
print()
print('sep_pts x@mid:',spx)

