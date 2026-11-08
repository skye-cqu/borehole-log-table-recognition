
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
print('depth cell x range: 15..%d (skip left frame)'%xr)
touching=0
for i in range(len(rows)-1):
    a,b=int(ys[i]),int(ys[i+1])
    if b-a<10: continue
    sub=gray[a+5:b-5, 15:xr-4]
    dk=(sub<150)
    cols=np.where(dk.any(axis=0))[0]
    if len(cols)==0: continue
    lm=int(cols[0])
    flag='  <== TOUCHES CUT EDGE' if lm<=1 else ''
    if flag: touching+=1
    print('row%3d y=%5d-%5d  first_dark_x=%3d (abs %3d)%s'%(i,a,b,lm,15+lm,flag))
print('touching',touching)
