
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1030'
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
seg={s['id']:s for s in cj['lines']}
for j in (8,9):
    r=rd['rows'][j]
    print('=== row',j,'era',r.get('era'),'n_ext',r.get('era_n_ext'),'bridge',r.get('era_bridge_segs'))
    for sid in r['segment_ids']:
        s=seg.get(sid)
        if not s: continue
        a=np.asarray(s['points'],float)
        print('   seg %d dir=%s label=%s x=[%.0f,%.0f] y=[%.0f,%.0f] npts=%d'%(sid,s['direction'],s['label'],a[:,0].min(),a[:,0].max(),a[:,1].min(),a[:,1].max(),len(a)))
