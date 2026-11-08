
import sys,json; sys.path.insert(0,'.')
from src.core import paths
from openpyxl import load_workbook
from src.table import delivery_gate as G
d=paths.RUNS_DIR/'table_整合_全量_20261011'
COLS=G.COLS
# for each column role, how many non-empty cells does the gate actually assert?
stat={}
for p in sorted(d.glob('*_整合.xlsx')):
    ws=load_workbook(p,rich_text=True).active
    rows=list(ws.iter_rows(values_only=True))
    hdr=[str(x) if x else '' for x in rows[0]]
    try:
        roles=G.header_roles(hdr)
    except Exception as e:
        print('header_roles fail',p.name,e); continue
    for i,r in enumerate(rows[1:]):
        for c,v in enumerate(r):
            if v in (None,''): continue
            role=None
            for nm,ro in roles.items():
                pass
    break
print('header_roles sample',G.header_roles([str(x) if x else '' for x in load_workbook(sorted(d.glob('*_整合.xlsx'))[0],rich_text=True).active.iter_rows(values_only=True).__next__()]))
print('COLS',G.COLS)
print('ROLE_RULES keys',list(G.ROLE_RULES))
