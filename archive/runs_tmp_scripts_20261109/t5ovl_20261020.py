
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
for s in ['1030','1042']:
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
    bw=xr-xl
    print('===',s,'band [%.1f,%.1f] w=%.1f'%(xl,xr,bw))
    for j,(r,yb) in enumerate(zip(rows,ys)):
        p=np.asarray(r['poly'],float); a,b=p[:,0].min(),p[:,0].max()
        lo,hi=max(a,xl),min(b,xr); ov=max(0.0,hi-lo)
        frac=ov/bw if bw>0 else 0
        if frac>=0.5:
            xq=(lo+hi)/2; yq=float(np.interp(xq,p[:,0],p[:,1]))
            print('  row%-3d y_mid=%8.1f span[%6.0f,%6.0f] ovl=%5.0f frac=%.2f y@ovl=%8.1f'%(j,yb,a,b,ov,frac,yq))
