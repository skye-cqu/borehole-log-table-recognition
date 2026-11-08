
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
print('row y0    y1     leftmost_ink_col(0..75)  read')
for i in range(0,20):
    a,b=int(ys[i]),int(ys[i+1])
    if b-a<12: continue
    sub=(gray[a+6:b-6, 0:75]<150)
    if sub.size==0: continue
    cols=np.where(sub.any(axis=0))[0]
    print('%3d %5d %5d  %s'%(i,a,b,cols[0] if len(cols) else 'none'))
