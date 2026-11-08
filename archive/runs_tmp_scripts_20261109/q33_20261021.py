
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table import track_rows as tr
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
def poly(i):
    sp=hm['sep_pts'][i]
    return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
a7,a8=poly(7),poly(8)
WID=hm['sep_x_band'][8]-hm['sep_x_band'][7]
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
rows=rd['rows']
def ymid(r):
    p=np.asarray(r['poly'],float)
    xs=p[:,0]; ys=p[:,1]
    return float(np.interp(1200,xs,ys))
bad=0; last=None
for i,r in enumerate(rows):
    y=ymid(r)
    if y>=8735:
        bad+=1
        if last is None: last=(i,y)
print('总行 %d  落在错线区间(y>=8735) %d 行 = %.0f%%  起始 行%d y=%.0f'%(len(rows),bad,100*bad/len(rows),last[0],last[1]))
y=ymid(rows[-1])
corr=float(tr.edge_at(a7,y))+WID; act=float(tr.edge_at(a8,y))
print('末行 y=%.0f: 正确左界 %.1f / 实际 %.1f  → 实际偏左 %.1f px'%(y,corr,act,act-corr))
print('  → 岩性描述格变宽 %.1f px, 只会多裁进左侧图案, 不会切字'%(corr-act))

