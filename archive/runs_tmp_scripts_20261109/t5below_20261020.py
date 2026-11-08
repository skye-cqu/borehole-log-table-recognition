
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
PAD=12
for s,side in [('1017','right_sep'),('1020','right_sep')]:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    ys=[row_y(r,midx) for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    dy1=int(max(ys))
    k0=hm['keep'][0]
    sp_l=hm['sep_pts'][k0['left_sep']]; sp_r=hm['sep_pts'][k0['right_sep']]
    y_end=int(sp_r['ys'][-1])
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    H,W=gray.shape
    print('===',s,'tail',y_end,'data_y1',dy1)
    for y in range(y_end+2, min(dy1,H-1), 8):
        xl=float(np.interp(y,sp_l['ys'],sp_l['xs'])); xr=float(np.interp(y,sp_r['ys'],sp_r['xs']))
        a,b=int(xl)+PAD,int(xr)-PAD
        seg=gray[y,a:b]
        dk=np.where(seg<150)[0]
        if len(dk):
            print('   y=%d x[%d,%d] dark=%d at x=%s'%(y,a,b,len(dk),[a+int(k) for k in dk[:8]]))
