
import sys,json; sys.path.insert(0,'.')
from src.table import delivery_gate as G
from src.core import paths
for d in [paths.RUNS_DIR/'table_整合_全量_20261011', paths.RUNS_DIR/'table_整合_全量_20261016']:
    rep=G.scan_dir(d)
    tot=sum(len(v) for v in rep.values())
    nz={k.replace('钻孔柱状图',''):len(v) for k,v in rep.items() if v}
    print('%-45s figures=%-3d violations=%-4d %s'%(d.name,len(rep),tot,nz))
