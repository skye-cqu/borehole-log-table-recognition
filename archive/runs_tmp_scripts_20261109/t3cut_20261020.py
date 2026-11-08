
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1032'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
midx=sum(rd['table_x'])/2.0
rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
ys=[row_y(r,midx) for r in rows]
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
xr=int(hm['sep_x_band'][0])
# find digit rows: dark pixel count in depth cell, excluding the vertical grid lines at x<12 and x~100
res=[]
for i in range(len(rows)-1):
    a,b=int(ys[i]),int(ys[i+1])
    if b-a<12: continue
    sub=(gray[a+6:b-6, 12:xr-6]<150)
    if sub.size==0: continue
    cols=np.where(sub.any(axis=0))[0]
    if len(cols)==0:
        res.append((i,a,b,None,None,0)); continue
    res.append((i,a,b,int(cols[0])+12,int(cols[-1])+12,int(sub.sum())))
print('row  y0    y1    first  last   ink  cut?')
for i,a,b,f,l,ink in res:
    cut='CUT' if (f is not None and f<=13) else ''
    print('%3d %5d %5d  %5s %5s %5d  %s'%(i,a,b,f,l,ink,cut))
