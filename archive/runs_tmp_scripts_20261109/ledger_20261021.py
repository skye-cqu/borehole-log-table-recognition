
import sys,json; sys.path.insert(0,'.')
from src.core import paths
import csv, collections
d=paths.RUNS_DIR/'table_整合_全量_20261011'
rows=[]
for p in sorted(d.glob('*_校正账.csv')):
    s=p.stem.replace('钻孔柱状图','').replace('_校正账','')
    with open(p,encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            r['_fig']=s
            rows.append(r)
print('ledger entries',len(rows))
print('fields',list(rows[0].keys()) if rows else None)
c=collections.Counter((r.get('列'),r.get('来源')) for r in rows)
for k,v in c.most_common(20): print('  ',k,v)
