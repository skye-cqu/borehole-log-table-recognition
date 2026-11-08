
import sys,json,re; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from openpyxl import load_workbook
from src.table import delivery_gate as G
d=paths.RUNS_DIR/'table_整合_全量_20261011'
nz=[]
for p in sorted(d.glob('*_整合.xlsx')):
    s=p.stem.replace('钻孔柱状图','').replace('_整合','')
    ws=load_workbook(p,rich_text=True).active
    rows=list(ws.iter_rows(values_only=True))
    roles=G.header_roles([str(x) if x else '' for x in rows[0]])
    inv={v:k-1 for k,v in roles.items()}
    di=inv.get('depth'); ti=inv.get('thick')
    prev=None
    for i,r in enumerate(rows[1:]):
        dv=r[di] if len(r)>di else None
        tv=r[ti] if len(r)>ti else None
        if isinstance(dv,(int,float)) and isinstance(tv,(int,float)):
            if prev is not None:
                diff=round(dv-(prev+tv),4)
                if abs(diff)>0: nz.append((s,i+2,diff,prev,tv,dv))
            prev=dv
print('non-zero diffs:',len(nz))
a=np.array([abs(x[2]) for x in nz])
print()
print('buckets of |diff| among non-zero:')
for lo,hi in [(0,0.01),(0.01,0.05),(0.05,0.1),(0.1,0.5),(0.5,2),(2,10),(10,100),(100,1e9)]:
    n=int(((a>lo)&(a<=hi)).sum())
    if n: print('  (%g, %g] : %4d'%(lo,hi,n))
print()
print('examples of SMALL diffs (<=0.1):')
for x in [y for y in nz if abs(y[2])<=0.1][:15]:
    print('  %-5s row%-4d diff=%+.4f prev=%-9s thick=%-7s depth=%s'%x)
print()
print('examples of LARGE diffs (>10):')
for x in [y for y in nz if abs(y[2])>10][:10]:
    print('  %-5s row%-4d diff=%+.2f prev=%-9s thick=%-7s depth=%s'%x)
