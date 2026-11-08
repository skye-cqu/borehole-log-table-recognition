
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'

print('stem         strip_y0 strip_y1 data_y0 data_y1  era_ink_below  ink_above  note')
for s in ['1017','1020','1023','1025','1028','1032']:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    ys=[row_y(r,midx) for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    dy0,dy1=min(ys),max(ys)
    k0=hm['keep'][0]
    li,ri=k0['left_sep'],k0['right_sep']
    n=len(hm['sep_pts'])
    sp_l=hm['sep_pts'][li] if li>=0 else None
    sp_r=hm['sep_pts'][ri] if ri>=0 else None
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    H,W=gray.shape
    y0=int(max(sp_l['ys'][0] if sp_l else 0, sp_r['ys'][0] if sp_r else 0))
    y1=int(min(sp_l['ys'][-1] if sp_l else H, sp_r['ys'][-1] if sp_r else H))
    # era x range at strip bottom
    if sp_l is not None and sp_r is not None:
        xa=float(np.interp(y1,sp_l['ys'],sp_l['xs'])); xb=float(np.interp(y1,sp_r['ys'],sp_r['xs']))
    else:
        xa,xb=0.0,float(np.interp(y1,sp_r['ys'],sp_r['xs'])) if sp_r else float(W)
    xa,xb=int(xa)+3,int(xb)-3
    def ink(ya,yb):
        if yb<=ya: return 0
        sub=(gray[int(ya):int(yb), xa:xb]<150)
        return int(sub.sum())
    below=ink(y1, dy1)
    above=ink(dy0, y0)
    print('%-12s %7d %7d %7d %7d   below=%7d above=%7d  L=%s R=%s'%(s,y0,y1,dy0,dy1,below,above,li,ri))
