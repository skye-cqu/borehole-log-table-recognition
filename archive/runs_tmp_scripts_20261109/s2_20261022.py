
import sys,json; sys.path.insert(0,'.')
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
d=json.load(open(D/'钻孔柱状图1023_全竖线判定.json',encoding='utf-8'))
print('track_nos =',json.dumps(d['track_nos'],ensure_ascii=False))
print('columns_gidx =',d['columns_gidx'])
print('n_tracks=%d n_visible=%d n_panels=%d crop=%s'%(d['n_tracks'],d['n_visible'],d['n_panels'],d['crop']))
print()
print('merged_by_track:')
for k,v in sorted(d['merged_by_track'].items(), key=lambda t:int(t[0])):
    print('   track %-4s -> %s'%(k,json.dumps(v,ensure_ascii=False)))

