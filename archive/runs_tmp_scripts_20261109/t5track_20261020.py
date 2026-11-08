
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
stems=sorted(p.name.split('_')[0] for p in D.glob('*_表头映射.json'))

def thin_runs(row, wmax=5):
    out=[];s=None
    for i,v in enumerate(row):
        if v and s is None: s=i
        elif not v and s is not None:
            if i-s<=wmax: out.append((s+i-1)/2.0)
            s=None
    if s is not None and len(row)-s<=wmax: out.append((s+len(row)-1)/2.0)
    return np.asarray(out,float)

def track(dark, x0, y0, y1, tol=12.0, gapmax=40):
    x=x0; miss=0; hits=0; total=0; last=y0; xs=[]
    for y in range(int(y0)+1,int(y1)+1):
        rr=thin_runs(dark[y])
        total+=1
        if len(rr)==0: miss+=1
        else:
            k=int(np.abs(rr-x).argmin())
            if abs(rr[k]-x)<=tol:
                x=0.7*x+0.3*rr[k]; hits+=1; miss=0; last=y; xs.append((y,x))
            else:
                miss+=1
        if miss>gapmax: break
    return hits, total, last, xs

print('stem side  tail_y data_y1  hits/total  last  frac')
for stem in stems:
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    if 'sep_pts' not in hm: print(stem,'NO sep_pts'); continue
    midx=sum(rd['table_x'])/2.0
    ys=[row_y(r,midx) for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    y1=int(max(ys))
    k0=hm['keep'][0]
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    dark=gray<160
    for side in ('left_sep','right_sep'):
        idx=k0[side]
        if idx is None or idx<0 or idx>=len(hm['sep_pts']):
            print(stem,side,'idx',idx,'OOR'); continue
        sp=hm['sep_pts'][idx]
        ty=sp['ys'][-1]; tx=sp['xs'][-1]
        h,t,last,_=track(dark,tx,ty,min(y1,gray.shape[0]-1))
        print('%-14s %-9s tail=%6d data_y1=%6d hits=%4d/%4d last=%6d frac=%.3f'%(stem.replace('钻孔柱状图',''),side,ty,y1,h,t,last,h/max(1,t)))
