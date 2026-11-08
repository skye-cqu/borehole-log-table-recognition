
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
for s in ['1030','1042']:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    print('===',s,'table_x',rd['table_x'],'midx',sum(rd['table_x'])/2)
    midx=sum(rd['table_x'])/2.0
    rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    tgt=4626.0 if s=='1030' else 4660.0
    ys=[row_y(r,midx) for r in rows]
    i=int(np.argmin([abs(y-tgt) for y in ys]))
    for j in (i-1,i):
        p=np.asarray(rows[j]['poly'],float)
        print(' row',j,'span',p[:,0].min(),p[:,0].max())
        for xq in [p[:,0].min()+5, 300, 500, 800, 1200, 1800, p[:,0].max()-5]:
            if p[:,0].min()<=xq<=p[:,0].max():
                print('    x=%6.0f y=%.1f'%(xq,float(np.interp(xq,p[:,0],p[:,1]))))
