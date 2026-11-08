
import sys; sys.path.insert(0,'.')
from src.core import paths
for n in ('OVERLAY_CHECK_DIR_20260930','RAW_DIR','RUNS_DIR'):
    print(n,'=',getattr(paths,n,None))
p=paths.OVERLAY_CHECK_DIR_20260930
print('存在?',p.exists())
if p.exists():
    fs=sorted(x.name for x in p.glob('*1023*'))
    print('1023 已有产物:',fs[:10])

