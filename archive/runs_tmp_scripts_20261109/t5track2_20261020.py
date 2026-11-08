
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'

def thin_runs(row, wmax=5):
    out=[];s=None
    for i,v in enumerate(row):
        if v and s is None: s=i
        elif not v and s is not None:
            if i-s<=wmax: out.append((s+i-1)/2.0)
            s=None
    if s is not None and len(row)-s<=wmax: out.append((s+len(row)-1)/2.0)
    return np.asarray(out,float)

def track(dark, x0, y0, y1, tol=30.0, gapmax=60):
    x=x0; miss=0; hits=0; total=0; last=y0; offs=[]
    for y in range(int(y0)+1,int(y1)+1):
        rr=thin_runs(dark[y]); total+=1
        if len(rr)==0: miss+=1
        else:
            k=int(np.abs(rr-x).argmin())
            if abs(rr[k]-x)<=tol:
                offs.append(rr[k]-x); x=0.6*x+0.4*rr[k]; hits+=1; miss=0; last=y
            else: miss+=1
        if miss>gapmax: break
    return hits,total,last,offs

for s,side,tol in [('1025','right_sep',30.0),('1025','left_sep',30.0),('1028','left_sep',30.0),('1023','left_sep',30.0),('1017','right_sep',30.0),('1020','right_sep',30.0)]:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    ys=[row_y(r,midx) for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    y1=int(max(ys))
    sp=hm['sep_pts'][hm['keep'][0][side]]
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    dark=gray<160
    h,t,last,offs=track(dark,sp['xs'][-1],sp['ys'][-1],min(y1,gray.shape[0]-1),tol)
    print('%-5s %-9s tail_y=%6d data_y1=%6d hits=%4d/%4d last=%6d frac=%.3f  medoff=%.1f'%(
        s,side,sp['ys'][-1],y1,h,t,last,h/max(1,t), float(np.median(offs)) if offs else 0.0))
