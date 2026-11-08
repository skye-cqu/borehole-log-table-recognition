
import sys,json; sys.path.insert(0,'.')
from src.core import paths
from openpyxl import load_workbook
from src.table import delivery_gate as G
d=paths.RUNS_DIR/'table_整合_全量_20261011'
byrole={}
for p in sorted(d.glob('*_整合.xlsx')):
    ws=load_workbook(p,rich_text=True).active
    rows=list(ws.iter_rows(values_only=True))
    hdr=[str(x) if x else '' for x in rows[0]]
    roles=G.header_roles(hdr)
    for r in rows[1:]:
        for c,v in enumerate(r):
            if v in (None,''): continue
            role=roles.get(c+1)
            if role is None: continue
            st=byrole.setdefault(role,{'n':0,'fail':0})
            st['n']+=1
            rule=G.ROLE_RULES.get(role)
            if rule is not None and not rule(v): st['fail']+=1
tot=sum(v['n'] for v in byrole.values()); totf=sum(v['fail'] for v in byrole.values())
print('asserted cells',tot,'failing',totf)
for k in ['era','layer','depth','thick','length','dip','true_thick','desc']:
    v=byrole.get(k,{'n':0,'fail':0})
    print('  %-11s asserted=%-6d fail=%-4d rate=%.3f%%'%(k,v['n'],v['fail'],100*v['fail']/max(1,v['n'])))
