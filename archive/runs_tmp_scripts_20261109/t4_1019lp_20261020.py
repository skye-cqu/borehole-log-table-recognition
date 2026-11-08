
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table import col_segments as CS
lp=CS.line_parts('钻孔柱状图1019')
for i,ln in enumerate(lp['lines']):
    nparts=len(ln['parts']); nbr=len(ln.get('bridged',[]))
    pts=[p for seg,_ in ln['parts'] for p in seg]+[p for seg,_ in ln.get('bridged',[]) for p in seg]
    if not pts: continue
    a=np.asarray(pts,float)
    print('#%d kind=%s index=%s side=%s parts=%d bridged=%d y=[%.0f,%.0f] x=[%.0f,%.0f]'%(
        i,ln['kind'],ln.get('index'),ln.get('side'),nparts,nbr,a[:,1].min(),a[:,1].max(),a[:,0].min(),a[:,0].max()))
