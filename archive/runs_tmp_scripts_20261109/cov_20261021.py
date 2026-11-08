
import sys,json; sys.path.insert(0,'.')
from src.core import paths
from openpyxl import load_workbook
from src.table import delivery_gate as G

d=paths.RUNS_DIR/'table_整合_全量_20261011'
tot_cells=0; tot_data=0
per=[]
for p in sorted(d.glob('*_整合.xlsx')):
    ws=load_workbook(p,rich_text=True).active
    rows=list(ws.iter_rows(values_only=True))
    hdr=[str(x) if x else '' for x in rows[0]]
    roles=G.column_roles(hdr) if hasattr(G,'column_roles') else None
    n=0; nonempty=0
    for r in rows[1:]:
        for c in r:
            n+=1
            if c not in (None,''): nonempty+=1
    per.append((p.stem.replace('钻孔柱状图',''),len(rows)-1,len(hdr),n,nonempty))
    tot_cells+=n; tot_data+=len(rows)-1
print('figures',len(per))
print('data rows total',tot_data)
print('cells total',tot_cells)
print('non-empty cells total',sum(x[4] for x in per))
print()
print('figure rows cols cells nonempty')
for x in per[:6]: print(' ',x)
