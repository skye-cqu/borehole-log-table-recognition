
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
# PF3 root cause: row 7 (1030) is a short poly [252,763] entirely left of most of the era band?
# check: is it a fragment/leak row? count poly length distribution & y jumps
for s,tgt in [('1030',4626.0),('1042',4660.0)]:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    ys=[row_y(r,midx) for r in rows]
    i=int(np.argmin([abs(y-tgt) for y in ys]))
    r=rows[i]
    print('===',s,'row',i,'keys',list(r.keys()))
    print('   n_chains',r.get('n_chains'),'cov',r.get('cov'),'kind',r.get('kind'),'sub',r.get('sub'))
    p=np.asarray(r['poly'],float)
    print('   poly first/last',p[0],p[-1],'npts',len(p))
    print('   y range',p[:,1].min(),p[:,1].max())
    print('   neighbors ys',[round(ys[j],1) for j in range(max(0,i-2),min(len(ys),i+3))])
