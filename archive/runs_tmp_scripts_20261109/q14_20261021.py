
# -*- coding: utf-8 -*-
"""sep#10 右侧: 把 x 2850..3120 内所有"连续竖墨"逐条追踪出来, 看折线贴的是哪一条。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import track_rows as tr
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
bw=(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)>0).astype(np.uint8)
vv=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))>0)
sp=hm['sep_pts'][10]
a=np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])

def track(x0,y0,y1,tol=4):
    x=float(x0); pts=[]
    for y in range(y0,y1):
        lo=max(0,int(round(x))-tol); hi=min(W,int(round(x))+tol+1)
        idx=np.flatnonzero(vv[y,lo:hi])
        if len(idx): x=float(idx[np.argmin(np.abs(idx+lo-x))]+lo)
        pts.append((y,x))
    return np.array(pts,float)

print('=== 起点扫描: 在 y=7000 上, x2850..3120 的所有竖墨列 ===')
row=vv[7000,2850:3120]
idx=np.flatnonzero(row)
grp=[]
for c in idx:
    if grp and c-grp[-1][-1]<=3: grp[-1].append(c)
    else: grp.append([c])
starts=[2850+sum(g)/len(g) for g in grp]
print('  ', [round(s,1) for s in starts])
print('   折线x@7000 = %.1f'%tr.edge_at(a,7000))
print()
print('=== 各条追踪 7000->10000 ===')
for s in starts:
    P=track(s,7000,10000)
    xs=P[:,1]
    print('  start=%7.1f  -> end=%7.1f  x范围[%7.1f,%7.1f]  漂移%+7.1f'%(s,xs[-1],xs.min(),xs.max(),xs[-1]-xs[0]))
print()
print('=== 折线 vs 各条 在若干 y 的距离 ===')
for y in (7000,7500,7998,8500,9000,9500,10000):
    xp=float(tr.edge_at(a,y))
    ds=[(round(s,1),round(abs(tr.edge_at(track(s,7000,10000),y)-xp),1)) for s in starts]
    print('  y=%5d 折线=%7.1f  '%(y,xp)+'  '.join('start%.0f:%.1f'%(u,v) for u,v in ds))

