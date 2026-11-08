
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

def extend(dark, sp, y_to, tol=25.0, gapmax=40):
    ys=list(sp['ys']); xs=list(sp['xs'])
    x=xs[-1]; miss=0; n=0
    for y in range(int(ys[-1])+1, int(y_to)+1):
        rr=thin_runs(dark[y])
        if len(rr)==0: miss+=1
        else:
            k=int(np.abs(rr-x).argmin())
            if abs(rr[k]-x)<=tol:
                x=rr[k]; ys.append(float(y)); xs.append(float(x)); miss=0; n+=1; continue
            miss+=1
        if miss>gapmax: break
    return np.asarray(xs,float), np.asarray(ys,float), n

print('stem           side  tail_y data_y1  gained  new_end  changes')
for stem in stems:
    s=stem.replace('钻孔柱状图','')
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    ys=[row_y(r,midx) for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    y1=int(max(ys))
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    dark=gray<160
    for i,sp in enumerate(hm['sep_pts']):
        ty=int(sp['ys'][-1])
        if ty>=y1-1: continue
        nx,ny,n=extend(dark,sp,min(y1,gray.shape[0]-1))
        if n>=20:
            print('%-14s #%-3d %7d %7d  +%5d  %7.0f'%(s,i,ty,y1,n,ny[-1]))
