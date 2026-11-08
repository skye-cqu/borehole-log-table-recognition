
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
stems=sorted(p.name.split('_')[0] for p in D.glob('*_表头映射.json'))
PAD=12
print('stem           data_y0 data_y1 strip_y0 strip_y1  ink_y0 ink_y1  out_text  above_text  PF1')
for stem in stems:
    s=stem.replace('钻孔柱状图','')
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    ys=[row_y(r,midx) for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    dy0,dy1=int(min(ys)),int(max(ys))
    k0=hm['keep'][0]; li,ri=k0['left_sep'],k0['right_sep']
    n=len(hm['sep_pts'])
    sp_l=hm['sep_pts'][li] if 0<=li<n else None
    sp_r=hm['sep_pts'][ri] if 0<=ri<n else None
    sy0=int(max(sp_l['ys'][0] if sp_l else 0, sp_r['ys'][0] if sp_r else 0))
    sy1=int(min(sp_l['ys'][-1] if sp_l else 10**9, sp_r['ys'][-1] if sp_r else 10**9))
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    H,W=gray.shape
    text_rows=[]
    for y in range(dy0,min(dy1,H-1)):
        xl=float(np.interp(y,sp_l['ys'],sp_l['xs'])) if sp_l else 0.0
        xr=float(np.interp(y,sp_r['ys'],sp_r['xs'])) if sp_r else float(W)
        a,b=int(xl)+PAD,int(xr)-PAD
        if b-a<8: continue
        c=int((gray[y,a:b]<150).sum())
        if 0<c and c/(b-a)<=0.85: text_rows.append(y)
    ty0,ty1=(text_rows[0],text_rows[-1]) if text_rows else (dy0,dy1)
    out=[y for y in text_rows if y>sy1 or y<sy0]
    above=[y for y in out if y<sy0]; below=[y for y in out if y>sy1]
    cov=1.0
    if ty1>ty0:
        cov=max(0.0,min(sy1,ty1)-max(sy0,ty0))/(ty1-ty0)
    print('%-14s %7d %7d %8d %8d  %6d %6d  %8d  %10d  %.4f'%(s,dy0,dy1,sy0,sy1,ty0,ty1,len(below),len(above),cov))
