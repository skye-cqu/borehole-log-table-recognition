
import sys,json; sys.path.insert(0,'.')
from src.table import delivery_gate as G
from src.core import paths
d=paths.FINALIZE_FULL_DIR_20261016
rep=G.scan_dir(d)
tot=0
for k,v in sorted(rep.items()):
    print(k,len(v))
    tot+=len(v)
    for x in v[:3]:
        print('   ',json.dumps(x,ensure_ascii=False)[:180])
print('TOTAL',tot)
