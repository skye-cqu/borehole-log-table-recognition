
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
for s in ['1030','1042']:
    stem='钻孔柱状图'+s
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    print('===',s,'top keys',[k for k in rd if k!='rows'])
    print('   n_era_full',rd.get('n_era_full'),'n_era_partial',rd.get('n_era_partial'))
    r0=rd['rows'][0]
    print('   row keys:',list(r0.keys()))
    print('   era rows:',[(i,round(r['y_at_mid'],1),r.get('era'),r.get('era_d_frame')) for i,r in enumerate(rd['rows']) if r.get('era')])
