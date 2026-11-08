
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
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
    xr=float(np.interp((y0+y1)/2,sp_r['ys'],sp_r['xs'])); xl=float(np.interp((y0+y1)/2,sp_l['ys'],sp_l['xs']))
    print('===',s,'xl',round(xl,1),'xr',round(xr,1))
    prev=None
    for r,yb in zip(rows,ys):
        xs=[x for x,_ in r['poly']]
        if not (min(xs)<=xr and max(xs)>=xl): continue
        if prev is not None and yb-prev<8.0:
            print('  viol y=',round(yb,1),'gap',round(yb-prev,1))
        prev=yb
