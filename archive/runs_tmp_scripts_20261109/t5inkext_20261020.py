
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
stems=sorted(p.name.split('_')[0] for p in D.glob('*_表头映射.json'))
PAD=12
print('stem           data_y0 data_y1  ink_y0 ink_y1  strip_y0 strip_y1  ink_out  era_json bands')
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
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    H,W=gray.shape
    sy0=int(max(sp_l['ys'][0] if sp_l else 0, sp_r['ys'][0] if sp_r else 0))
    sy1=int(min(sp_l['ys'][-1] if sp_l else H, sp_r['ys'][-1] if sp_r else H))
    rows_ink=[]
    for y in range(dy0, min(dy1,H-1)):
        xl=float(np.interp(y,sp_l['ys'],sp_l['xs'])) if sp_l else 0.0
        xr=float(np.interp(y,sp_r['ys'],sp_r['xs'])) if sp_r else float(W)
        a,b=int(xl)+PAD,int(xr)-PAD
        if b<=a: continue
        if (gray[y,a:b]<150).sum()>0: rows_ink.append(y)
    iy0,iy1=(rows_ink[0],rows_ink[-1]) if rows_ink else (0,0)
    out=sum(1 for y in rows_ink if y<sy0 or y>sy1)
    ep=paths.ERA_CHAR_DIR/stem/'era_chars.json'
    nb='-'
    if ep.exists():
        nb=len(json.loads(ep.read_text(encoding='utf-8')).get('bands',[]))
    print('%-14s %7d %7d  %6d %6d  %8d %8d  %7d  %-5s %s'%(s,dy0,dy1,iy0,iy1,sy0,sy1,out,ep.exists(),nb))
