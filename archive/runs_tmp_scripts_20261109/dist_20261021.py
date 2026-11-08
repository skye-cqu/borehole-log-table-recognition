
import sys,json,re; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from openpyxl import load_workbook
from src.table import delivery_gate as G
d=paths.RUNS_DIR/'table_整合_全量_20261011'
diffs=[]
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
                diffs.append((s,i+2,round(dv-(prev+tv),4),prev,tv,dv))
            prev=dv
print('total pairs',len(diffs))
a=np.array([abs(x[2]) for x in diffs])
print()
print('|diff| distribution:')
for thr in [0,0.005,0.01,0.015,0.02,0.03,0.05,0.1,0.5,1,5,100]:
    print('  <= %-6s : %5d  (%.1f%%)'%(thr,int((a<=thr).sum()),100*(a<=thr).mean()))
print()
print('quantiles:',[round(float(np.percentile(a,q)),4) for q in [50,75,90,95,99,99.9]])
print('max',float(a.max()))
