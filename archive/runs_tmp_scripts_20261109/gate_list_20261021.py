
import sys,json; sys.path.insert(0,'.')
from src.table import delivery_gate as G
from src.core import paths
d=paths.RUNS_DIR/'table_整合_全量_20261011'
rep=G.scan_dir(d)
tot=sum(len(v) for v in rep.values())
print('total violations',tot)
for k,v in sorted(rep.items()):
    if not v: continue
    print('===',k.replace('钻孔柱状图',''),len(v))
    for x in v:
        print('   ',json.dumps(x,ensure_ascii=False))
