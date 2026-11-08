
import sys,json,csv; sys.path.insert(0,'.')
from src.core import paths
d=paths.RUNS_DIR/'table_整合_全量_20261011'
rows=[]
for p in sorted(d.glob('*_校正账.csv')):
    s=p.stem.replace('钻孔柱状图','').replace('_校正账','')
    with open(p,encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            r['_fig']=s; rows.append(r)
applied=[r for r in rows if str(r['应用'])=='1']
print('total ledger',len(rows),'applied',len(applied))
# which applied entries derive value from chain (not from pixel/Agnes)?
chain=[r for r in applied if ('链' in (r['依据'] or '')) or ('终深差' in (r['依据'] or ''))]
print('applied AND chain-derived:',len(chain))
for r in chain:
    print('  %-5s 行%-4s %-6s 原=%-20s 新=%-20s 依据=%s'%(r['_fig'],r['行'],r['列'],str(r['原'])[:20],str(r['新'])[:20],r['依据'][:50]))
print()
sugg=[r for r in rows if str(r['应用'])=='0' and '终深差' in (r['依据'] or '')]
print('suggestion-only (应用=0) chain entries:',len(sugg))
