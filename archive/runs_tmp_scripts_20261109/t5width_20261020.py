
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stems=sorted(p.name.split('_')[0] for p in D.glob('*_表头映射.json'))
print('stem           n  width_p10 p50 p90   max/min  ratio_p90_p10  jump_max')
for stem in stems:
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    k0=hm['keep'][0]
    n=len(hm['sep_pts'])
    li,ri=k0['left_sep'],k0['right_sep']
    if not (0<=li<n and 0<=ri<n):
        print('%-14s NO ERA COLUMN (keep0=%s L=%s R=%s)'%(stem.replace('钻孔柱状图',''),k0['name'],li,ri)); continue
    sp_l=hm['sep_pts'][li]; sp_r=hm['sep_pts'][ri]
    y0=max(sp_l['ys'][0],sp_r['ys'][0]); y1=min(sp_l['ys'][-1],sp_r['ys'][-1])
    ys=np.arange(y0,y1,5.0)
    w=np.array([float(np.interp(y,sp_r['ys'],sp_r['xs']))-float(np.interp(y,sp_l['ys'],sp_l['xs'])) for y in ys])
    d=np.abs(np.diff(w))
    print('%-14s %d  %5.1f %5.1f %5.1f  %5.1f  %6.1f  %6.1f'%(
        stem.replace('钻孔柱状图',''),len(sp_l['ys']),np.percentile(w,10),np.median(w),np.percentile(w,90),
        w.max()/max(1e-6,w.min()), np.percentile(w,90)/max(1e-6,np.percentile(w,10)), d.max()))
