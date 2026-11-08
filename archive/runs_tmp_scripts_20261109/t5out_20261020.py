
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
PAD=12
for s in ['1029','1016','1037','1033','1030','1032']:
    stem='钻孔柱状图'+s
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
    out=[]
    for y in range(dy0,min(dy1,H-1)):
        xl=float(np.interp(y,sp_l['ys'],sp_l['xs'])) if sp_l else 0.0
        xr=float(np.interp(y,sp_r['ys'],sp_r['xs'])) if sp_r else float(W)
        a,b=int(xl)+PAD,int(xr)-PAD
        if b<=a: continue
        c=int((gray[y,a:b]<150).sum())
        if c>0 and (y<sy0 or y>sy1): out.append((y,c))
    print('===',s,'strip',sy0,sy1,'data',dy0,dy1,'out_rows',len(out))
    if out:
        print('   first',out[:4],'last',out[-4:])
        print('   maxink',max(c for _,c in out))
