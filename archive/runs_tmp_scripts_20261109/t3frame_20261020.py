
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
y0,y1=int(ys[0]),int(ys[-1])
# vertical grid lines: columns with high dark fraction inside table
sub=(gray[y0+20:y1-20, :400]<150)
frac=sub.mean(axis=0)
print('vertical line candidates (frac>0.5):',[int(x) for x in np.where(frac>0.5)[0]])
print('frac at x=0..12:',[round(float(frac[x]),3) for x in range(13)])
print()
# horizontal row lines: rows with high dark fraction in depth cell x 0..60
sub2=(gray[y0:y1, 0:60]<150)
rf=sub2.mean(axis=1)
print('rows with >50%% dark in x0..60:',int((rf>0.5).sum()),'of',len(rf))
print('   sample:',[int(y0+i) for i in np.where(rf>0.5)[0][:10]])
# left frame presence: dark frac at x 0..3 by y-band
for a in range(y0, y1, 2000):
    seg=(gray[a:min(a+2000,y1), 0:4]<150).mean()
    print('   y%5d frac(x0..3)=%.3f'%(a,seg))
