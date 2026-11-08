
import sys,json; sys.path.insert(0,'.')
from src.table import delivery_gate as G
from src.core import paths
d=paths.RUNS_DIR/'table_整合_全量_20261011'
rep=G.scan_dir(d)
tot=0
for k,v in sorted(rep.items()):
    tot+=len(v)
    print('%-16s %d'%(k,len(v)))
print('TOTAL',tot)
