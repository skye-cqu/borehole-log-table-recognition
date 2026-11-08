
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
for s,tgt in [('1030',4626.0),('1042',4660.0)]:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    ys=[row_y(r,midx) for r in rows]
    k0=hm['keep'][0]
    sp_l=hm['sep_pts'][k0['left_sep']]; sp_r=hm['sep_pts'][k0['right_sep']]
    y0,y1=min(ys),max(ys)
    xl=float(np.interp((y0+y1)/2,sp_l['ys'],sp_l['xs'])); xr=float(np.interp((y0+y1)/2,sp_r['ys'],sp_r['xs']))
    i=int(np.argmin([abs(y-tgt) for y in ys]))
    print('===',s,'band x=[%.1f,%.1f]'%(xl,xr))
    for j in range(max(0,i-2),min(len(rows),i+3)):
        p=np.asarray(rows[j]['poly'],float)
        a,b=p[:,0].min(),p[:,0].max()
        lo,hi=max(a,xl),min(b,xr)
        if hi-lo<2:
            print('  row%d span[%.0f,%.0f] no band overlap'%(j,a,b)); continue
        xq=(lo+hi)/2
        yq=float(np.interp(xq,p[:,0],p[:,1]))
        print('  row%d span[%.0f,%.0f] ovl[%.0f,%.0f] w=%.0f y@xq=%.1f  (y@midx=%.1f)'%(j,a,b,lo,hi,hi-lo,yq,ys[j]))
