
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1030'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
midx=sum(rd['table_x'])/2.0
rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
for j in range(5,11):
    r=rows[j]; p=np.asarray(r['poly'],float)
    print('row',j,'y_at_mid',round(r['y_at_mid'],1),'span',round(p[:,0].min()),round(p[:,0].max()),'npts',len(p))
    print('   poly',[(round(a),round(b,1)) for a,b in p[:8]])
