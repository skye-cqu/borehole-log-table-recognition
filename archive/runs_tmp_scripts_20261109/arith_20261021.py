
import sys,json; sys.path.insert(0,'.')
from src.core import paths
from openpyxl import load_workbook
from src.table import delivery_gate as G
d=paths.RUNS_DIR/'table_整合_全量_20261011'
# measure "how many cells are cross-checked by arithmetic" (depth chain / thick=delta / true=thick*cos)
import re
NUM=re.compile(r'^-?\d+(\.\d+)?$')
tot=0; chain_ok=0; chain_bad=0; thick_ok=0; thick_bad=0; skip=0
for p in sorted(d.glob('*_整合.xlsx')):
    ws=load_workbook(p,rich_text=True).active
    rows=list(ws.iter_rows(values_only=True))
    hdr=[str(x) if x else '' for x in rows[0]]
    roles=G.header_roles(hdr)
    inv={v:k-1 for k,v in roles.items()}
    di=inv.get('depth'); ti=inv.get('thick')
    if di is None or ti is None: continue
    prev=None
    for r in rows[1:]:
        d_=r[di] if len(r)>di else None
        t_=r[ti] if len(r)>ti else None
        if isinstance(d_,(int,float)) and isinstance(t_,(int,float)):
            tot+=1
            if prev is not None:
                exp=prev+t_
                if abs(exp-d_)<=0.02: chain_ok+=1
                else: chain_bad+=1
            prev=d_
        else:
            skip+=1
print('rows with numeric depth+thick:',tot,'skipped(non-numeric):',skip)
print('depth chain consistent:',chain_ok,'inconsistent:',chain_bad)
