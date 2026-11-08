
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
# is x=0..3 a real cut edge, or is there a border line?
print('per-column dark frac over x 0..10, full height:')
for x in range(0,11):
    print('  x=%d %.3f'%(x,(gray[1000:21850,x]<150).mean()))
print()
print('=== ascii rows 1035..1271 x0..110')
seg=(gray[1035:1271, 0:110]<150)
for r in range(0,seg.shape[0],12):
    print('  y%5d '%(1035+r)+''.join('#' if v else '.' for v in seg[r]))
