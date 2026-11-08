
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table.finalize_columns import FINAL
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
d=json.loads((D/f'{stem}_全竖线判定.json').read_text(encoding='utf-8'))
# track x positions? check if stored
print('keys',list(d.keys()))
for k in d:
    if k in ('image','n_tracks','n_visible','n_panels'): continue
print()
print('crop:',json.dumps(d.get('crop'),ensure_ascii=False)[:300])
print()
print('raws panel info:')
for r in d.get('raws',[]):
    print('  panel',r['panel'],'n_tracks',r['n_tracks'],'map sample',r['map'][:3])
