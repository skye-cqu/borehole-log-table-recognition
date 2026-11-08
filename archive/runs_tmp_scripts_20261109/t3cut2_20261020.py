
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
cut=0; clean=0
print('row  y0    y1    ink_at_x<=6  digit_ink')
for i in range(len(rows)-1):
    a,b=int(ys[i]),int(ys[i+1])
    if b-a<12: continue
    sub=(gray[a+6:b-6, 0:xr-6]<150)
    if sub.size==0: continue
    edge=int(sub[:, :7].sum())
    tot=int(sub.sum())
    if tot==0: continue
    tag='CUT' if edge>=8 else ''
    if tag: cut+=1
    else: clean+=1
    print('%3d %5d %5d  %11d  %9d  %s'%(i,a,b,edge,tot,tag))
print()
print('rows with cut-edge ink:',cut,'clean:',clean)
