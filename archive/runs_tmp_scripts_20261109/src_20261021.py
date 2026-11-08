
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
def show(fp,label):
    d=json.load(open(fp,encoding='utf-8'))
    cols=sorted(d.get('columns') or [], key=lambda c:c['x_at_mid'])
    print('===',label,'columns',len(cols))
    for c in cols:
        print('   x_at_mid=%7.1f  side=%-6s name=%s'%(c['x_at_mid'],c.get('side'),c.get('name')))
show(D/f'{stem}_列结构定稿.json','列结构定稿(6a)')
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
print('=== 表头映射 sep_pts',len(hm['sep_pts']))
for i,sp in enumerate(hm['sep_pts']):
    ys=np.asarray(sp['ys'],float); xs=np.asarray(sp['xs'],float)
    print('   #%-2d kind=%-6s index=%-4s side=%-5s x@mid=%7.1f npts=%d'%(
        i,sp.get('kind'),sp.get('index'),sp.get('side'),
        float(np.interp((ys.min()+ys.max())/2,ys,xs)),len(ys)))
