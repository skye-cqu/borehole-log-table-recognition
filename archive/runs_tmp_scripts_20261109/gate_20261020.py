
import sys,json; sys.path.insert(0,'.')
from src.core import paths
# find latest gate report
import glob
cands=sorted(paths.RUNS_DIR.glob('**/交付门禁_报告.json'),key=lambda p:p.stat().st_mtime,reverse=True)
print('gate reports:',[str(c) for c in cands[:5]])
if cands:
    d=json.loads(cands[0].read_text(encoding='utf-8'))
    print('keys',list(d.keys())[:12])
    for k,v in d.items():
        if isinstance(v,(int,float,str)): print('  ',k,v)
        elif isinstance(v,list): print('  ',k,'list len',len(v))
