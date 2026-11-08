
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
H,W=gray.shape
xr=int(hm['sep_x_band'][0])
# for each row: rightmost ink x in depth column, and leftmost
print('row  y0    y1    left  right  width  gap_to_sep')
for i in range(len(rows)-1):
    a,b=int(ys[i]),int(ys[i+1])
    if b-a<8: continue
    sub=gray[a+4:b-4, 0:xr-4]
    dk=(sub<150)
    cols=np.where(dk.any(axis=0))[0]
    if len(cols)==0: 
        print('%3d %5d %5d  EMPTY'%(i,a,b)); continue
    print('%3d %5d %5d  %4d %5d %6d %8d'%(i,a,b,int(cols[0]),int(cols[-1]),int(cols[-1]-cols[0]),xr-4-int(cols[-1])))
