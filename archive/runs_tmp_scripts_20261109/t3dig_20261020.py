
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
# the depth cell is x 0..105 but the digits live near x=60..100.
# find digit band: columns with 20%-70% coverage
for i in [4,5,9,12]:
    a,b=int(ys[i]),int(ys[i+1])
    sub=(gray[a+4:b-4, 0:x1]<150)
    cp=sub.sum(axis=0); h=b-a-8
    dig=[int(x) for x in np.where((cp>0.08*h)&(cp<0.75*h))[0]]
    print('=== row%d y=%d-%d h=%d'%(i,a,b,h))
    print('   digit-ish cols:',dig[:30])
    print('   grid cols:',[int(x) for x in np.where(cp>=0.75*h)[0]])
    print('   leftmost digit-ish:',dig[0] if dig else None)
