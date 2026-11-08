
import sys,json,csv; sys.path.insert(0,'.')
from src.core import paths
d=paths.RUNS_DIR/'table_整合_全量_20261011'
rows=[]
for p in sorted(d.glob('*_校正账.csv')):
    s=p.stem.replace('钻孔柱状图','').replace('_校正账','')
    with open(p,encoding='utf-8-sig') as f:
        for r in csv.DictReader(f):
            r['_fig']=s; rows.append(r)
# any entry that derives a value from the depth chain?
key=('链','闭合','Δ','差')
sus=[r for r in rows if any(k in (r.get('依据') or '') for k in key)]
print('entries whose 依据 mentions chain/delta:',len(sus))
import collections
c=collections.Counter((r['列'],r['依据'][:40]) for r in sus)
for k,v in c.most_common(15): print('  ',k,v)
print()
print('--- 深度/层厚 全部条目 ---')
for r in rows:
    if r['列'] in ('深度','层厚','数值列'):
        print('  %-5s 行%-4s %-8s 原=%-22s 新=%-22s 依据=%s 应用=%s'%(
            r['_fig'],r['行'],r['列'],str(r['原'])[:22],str(r['新'])[:22],str(r['依据'])[:40],r['应用']))
