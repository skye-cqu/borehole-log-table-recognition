
# -*- coding: utf-8 -*-
"""修正上一版: 裁界处那条竖线本身就是墨, 要跳过它再看首字。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import track_rows as tr
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
def poly(i):
    sp=hm['sep_pts'][i]
    return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
a7,a8=poly(7),poly(8)
WID=hm['sep_x_band'][8]-hm['sep_x_band'][7]
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
rows=rd['rows']
def ymid(r):
    p=np.asarray(r['poly'],float)
    return float(np.interp(1200,p[:,0],p[:,1]))

def first_text(x_start,y,span=260,skip=10):
    """从 x_start+skip 起, 找第一处"文字级"墨(列墨>=4px 且宽>=6px 的块)"""
    b=gray[max(0,int(y)-10):int(y)+11, int(x_start)+skip:int(x_start)+skip+span]
    if b.size==0: return None
    dark=(b<150)
    col=dark.sum(axis=0)
    idx=np.flatnonzero(col>=4)
    if len(idx)==0: return None
    # 合并成块, 取第一个宽度>=6 的
    grp=[]
    for c in idx:
        if grp and c-grp[-1][-1]<=4: grp[-1].append(c)
        else: grp.append([c])
    for g in grp:
        if len(g)>=6: return int(x_start)+skip+g[0]
    return int(x_start)+skip+idx[0]

print('行   y     现裁界   真边界  首字墨左缘  现裁界余量  真边界余量')
res=[]
for i,r in enumerate(rows):
    y=ymid(r)
    if y<8600: continue
    xc=float(tr.edge_at(a8,y)); xt=float(tr.edge_at(a7,y))+WID
    # 从真边界右侧找首字
    t=first_text(xt,y)
    if t is None: continue
    res.append((i+1,y,xc,xt,t,xc-t,xt-t))
for a in res[:16]:
    print('%-4d %6.0f %8.1f %8.1f %9.1f %10.1f %10.1f'%(a[0],a[1],a[2],a[3],a[4],a[5],a[6]))
print()
bad_now=sum(1 for a in res if a[5]>0)
bad_true=sum(1 for a in res if a[6]>0)
print('样本 %d 行'%len(res))
print('  现裁界切字(裁界>首字左缘): %d 行'%bad_now)
print('  真边界切字: %d 行'%bad_true)
print('  现裁界余量: 中位 %.1f  最小 %.1f'%(np.median([a[5] for a in res]),min(a[5] for a in res)))
print('  真边界余量: 中位 %.1f  最小 %.1f'%(np.median([a[6] for a in res]),min(a[6] for a in res)))

