
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1030'
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
midx=sum(rd['table_x'])/2.0
rows=rd['rows']
# find indices by y_at_mid
for j,r in enumerate(rows):
    if abs(r['y_at_mid']-4698.1)<1 or abs(r['y_at_mid']-4766.0)<1:
        p=np.asarray(r['poly'],float)
        print('row',j,'y_at_mid',r['y_at_mid'],'npts',len(p),'n_chains',r.get('n_chains'),'segids',r.get('segment_ids'))
        print('   first10',[(round(a),round(b,1)) for a,b in p[:10]])
        print('   last5',[(round(a),round(b,1)) for a,b in p[-5:]])
        for xq in [190,250,400,700,900,1200,1600,2000,2270]:
            if p[:,0].min()<=xq<=p[:,0].max():
                print('      x=%5d y=%.1f'%(xq,float(np.interp(xq,p[:,0],p[:,1]))))
