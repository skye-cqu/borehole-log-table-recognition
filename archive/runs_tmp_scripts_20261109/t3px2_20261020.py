
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
# locate ink rows inside each cell in x 8..x1-6 (inside cell, away from both grid lines)
for i in [4,5,9]:
    a,b=int(ys[i]),int(ys[i+1])
    sub=(gray[a+3:b-3, 8:x1-6]<150)
    prof=sub.sum(axis=1)
    nz=np.where(prof>0)[0]
    print('=== row%d y=%d-%d  ink rows %s'%(i,a,b,(nz.min()+a+3,nz.max()+a+3) if len(nz) else 'none'))
    if len(nz):
        lo,hi=nz.min(),nz.max()
        seg=(gray[a+3+lo:a+3+hi+1, 0:x1]<150)
        cols=np.where(seg.any(axis=0))[0]
        print('   ink cols in 0..%d: %s'%(x1,list(cols[:20])),'...' if len(cols)>20 else '')
        for r in range(0,min(seg.shape[0],24),2):
            print('   '+''.join('#' if v else '.' for v in seg[r]))
