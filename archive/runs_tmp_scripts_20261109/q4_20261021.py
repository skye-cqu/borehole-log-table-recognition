
# -*- coding: utf-8 -*-
"""量 1023 两处: 岩性描述左界(sep#8) 与 右外框(sep#10), 用 yard_cols 同款竖墨掩膜。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import track_rows as tr

stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
bw=(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)>0).astype(np.uint8)*255
v=cv2.morphologyEx(bw,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))
v=cv2.morphologyEx(v,cv2.MORPH_CLOSE,np.ones((25,1),np.uint8))

def report(idx,label,search=80):
    sp=hm['sep_pts'][idx]
    a=np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
    print(f'--- sep#{idx} {label}  kind={sp.get("kind")}  npts={len(a)}  y[{a[0,0]:.0f},{a[-1,0]:.0f}] x[{a[:,1].min():.1f},{a[:,1].max():.1f}]')
    rows=[]
    for y in np.linspace(a[0,0]+40, a[-1,0]-40, 41):
        yi=int(round(y)); xi=float(tr.edge_at(a,y))
        lo=max(0,int(xi)-search); hi=min(W-1,int(xi)+search)
        idxs=np.flatnonzero(v[yi,lo:hi])
        if len(idxs)==0:
            rows.append((y,xi,None)); continue
        # nearest ink column
        k=int(np.argmin(np.abs(idxs+lo-xi)))
        rows.append((y,xi,float(idxs[k]+lo)))
    devs=[abs(c-b) for _,b,c in rows if c is not None]
    miss=sum(1 for _,_,c in rows if c is None)
    print(f'    采样{len(rows)}  有墨{len(devs)}  无墨{miss}')
    if devs:
        d=np.array(devs)
        print(f'    偏差 px: 中位{np.median(d):.1f}  p90 {np.percentile(d,90):.1f}  最大{d.max():.1f}')
    # 逐点明细(每4个采样取1)
    for y,b,c in rows[::4]:
        s='无墨' if c is None else f'{c:7.1f}  差{c-b:+6.1f}'
        print(f'      y={y:6.0f}  折线x={b:7.1f}   墨x={s}')
    return rows

r8=report(8,'岩性描述左界')
print()
r10=report(10,'右外框')

