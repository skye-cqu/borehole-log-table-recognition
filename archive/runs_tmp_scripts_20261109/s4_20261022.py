
import sys,json; sys.path.insert(0,'.')
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
d=json.load(open(D/'钻孔柱状图1023_全竖线判定.json',encoding='utf-8'))
print('Agnes 看过的 track (片内编号 -> gidx, x_mid):')
for r in d['raws']:
    print(' 片 x[%d,%d] n=%d'%(r['panel'][0],r['panel'][1],r['n_tracks']))
    for m in r['map']:
        print('    no=%-2d gidx=%-3d x_mid=%8.1f  判=%s'%(m['no'],m['gidx'],m['x_mid'],d['merged_by_track'].get(str(m['gidx']),'-')))

