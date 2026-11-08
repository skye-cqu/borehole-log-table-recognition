
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
for s,xl,xr in [('1030',196.7,261.0),('1042',131.1,267.6)]:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    ys=[row_y(r,midx) for r in rows]
    tgt=4626.0 if s=='1030' else 4660.0
    i=int(np.argmin([abs(y-tgt) for y in ys]))
    print('===',s,'era band x=[%.1f,%.1f] mid=%.1f'%(xl,xr,(xl+xr)/2))
    for j in (i-1,i,i+1):
        p=np.asarray(rows[j]['poly'],float)
        xa,xb=p[:,0].min(),p[:,0].max()
        xq=(xl+xr)/2
        inside = xa<=xq<=xb
        yq=float(np.interp(xq,p[:,0],p[:,1]))
        print('  row%d row_y(midx)=%.1f span=[%.0f,%.0f] y@eramid=%.1f inside=%s'%(j,ys[j],xa,xb,yq,inside))
        # also y at era band left/right edges
        for xq2 in (xl,xr):
            print('      y@%.0f=%.1f'%(xq2,float(np.interp(xq2,p[:,0],p[:,1]))))
