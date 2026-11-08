
import sys,json; sys.path.insert(0,'.')
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
d=json.load(open(D/'钻孔柱状图1023_全竖线判定.json',encoding='utf-8'))
print('Agnes 看过的 track:')
seen=set()
for r in d['raws']:
    print(' 片 x[%d,%d] n=%d'%(r['panel'][0],r['panel'][1],r['n_tracks']))
    for m in r['map']:
        seen.add(m['gidx'])
        print('    no=%-2d gidx=%-3d role_hint=%-6s 判=%s'%(m['no'],m['gidx'],m.get('role_hint'),d['merged_by_track'].get(str(m['gidx']),'-')))
print()
print('送检 gidx 集合:',sorted(seen))
print('总 track 数:',d['n_tracks'])
print('未送检 gidx:',[g for g in range(1,d['n_tracks']+1) if g not in seen])

