
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
x1=int(hm['sep_x_band'][0])
for i in [4,5,9]:
    a,b=int(ys[i]),int(ys[i+1])
    sub=(gray[a+3:b-3, 0:x1]<150)
    # find the horizontal runs (row lines) and vertical grid line
    rowprof=sub.sum(axis=1)
    colprof=sub.sum(axis=0)
    print('=== row%d y=%d-%d'%(i,a,b))
    print('   cols with >50%% coverage (grid lines):',[int(x) for x in np.where(colprof>0.5*(b-a-6))[0]])
    print('   rows with >50%% coverage (h lines):',[int(a+3+x) for x in np.where(rowprof>0.5*x1)[0]][:6])
    print('   total ink',int(sub.sum()))
