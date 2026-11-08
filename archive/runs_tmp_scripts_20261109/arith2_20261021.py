
import sys,json,re; sys.path.insert(0,'.')
from src.core import paths
from openpyxl import load_workbook
from src.table import delivery_gate as G
d=paths.RUNS_DIR/'table_整合_全量_20261011'
per={}
for p in sorted(d.glob('*_整合.xlsx')):
    s=p.stem.replace('钻孔柱状图','').replace('_整合','')
    ws=load_workbook(p,rich_text=True).active
    rows=list(ws.iter_rows(values_only=True))
    roles=G.header_roles([str(x) if x else '' for x in rows[0]])
    inv={v:k-1 for k,v in roles.items()}
    di=inv.get('depth'); ti=inv.get('thick')
    ok=bad=0
    prev=None
    for r in rows[1:]:
        dv=r[di] if len(r)>di else None
        tv=r[ti] if len(r)>ti else None
        if isinstance(dv,(int,float)) and isinstance(tv,(int,float)):
            if prev is not None:
                if abs(prev+tv-dv)<=0.02: ok+=1
                else: bad+=1
            prev=dv
    per[s]=(ok,bad)
print('figure  chain_ok chain_bad')
for s,(o,b) in sorted(per.items()):
    if b: print('  %-6s %6d %8d'%(s,o,b))
print()
print('total ok',sum(o for o,b in per.values()),'bad',sum(b for o,b in per.values()))
