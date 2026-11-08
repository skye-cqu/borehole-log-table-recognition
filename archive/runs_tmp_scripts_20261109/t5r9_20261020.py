
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1030'
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
for j in (6,7,8,9,10):
    r=rd['rows'][j]; p=np.asarray(r['poly'],float)
    print('row',j,'y_at_mid=%.1f'%r['y_at_mid'],'npts',len(p),'span[%.0f,%.0f]'%(p[:,0].min(),p[:,0].max()))
    print('   segids',r.get('segment_ids'),'n_chains',r.get('n_chains'))
    print('   era',r.get('era'),'era_d_frame',r.get('era_d_frame'),'era_n_ext',r.get('era_n_ext'),'era_bridge_segs',r.get('era_bridge_segs'))
    print('   pts',[(round(a),round(b,1)) for a,b in p[:6]],'...',[(round(a),round(b,1)) for a,b in p[-4:]])
