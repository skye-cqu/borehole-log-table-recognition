
# -*- coding: utf-8 -*-
"""sep#8 的两条平行线: A(x~1030..1070) 与 B(x~1072..1121). 谁是真列线?
   证据1: 各自在 y 方向的墨迹覆盖长度
   证据2: 行分隔横线的左端点落在哪条线上
"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1023'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
bw=(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)>0).astype(np.uint8)
vv=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))>0)
hh=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(30,1)))>0)

# 追踪两条线: 从 y=8300 出发, 逐行找最近墨列, 允许 +-3 漂移
def track(x0,y0,y1,step=1,tol=3):
    x=x0; pts=[]
    for y in range(y0,y1):
        lo=max(0,int(round(x))-tol); hi=min(W,int(round(x))+tol+1)
        idx=np.flatnonzero(vv[y,lo:hi])
        if len(idx):
            x=float(idx[np.argmin(np.abs(idx+lo-x))]+lo)
        pts.append((y,x))
    return np.array(pts,float)

A=track(1030,8300,9600); B=track(1072.5,8300,9600)
for nm,P in (('A',A),('B',B)):
    xs=P[:,1]
    print('%s: y[%.0f,%.0f]  x[%.1f,%.1f]  drift %+.1f  x@8300=%.1f x@9600=%.1f'%(
        nm,P[0,0],P[-1,0],xs.min(),xs.max(),xs[-1]-xs[0],xs[0],xs[-1]))
print()
# 证据2: 横线左端点
print('横线左端点(在 x 900..1300 内找最左):')
rows=[]
for y in range(8300,9600):
    idx=np.flatnonzero(hh[y,900:1300])
    if len(idx)>50:
        rows.append((y,900+idx[0]))
# 合并相邻 y
grp=[]
for y,x in rows:
    if grp and y-grp[-1][-1][0]<=3: grp[-1].append((y,x))
    else: grp.append([(y,x)])
for g in grp:
    ys=[a for a,_ in g]; xs=[b for _,b in g]
    ym=int(np.mean(ys)); xl=int(np.min(xs))
    # 该 y 的 A/B 位置
    ya=int(np.clip(ym,A[0,0],A[-1,0])); xa=float(np.interp(ya,A[:,0],A[:,1]))
    xb=float(np.interp(ya,B[:,0],B[:,1]))
    print('   y=%5d 横线左端 x=%4d   A=%.1f(%+.1f)  B=%.1f(%+.1f)'%(ym,xl,xa,xl-xa,xb,xl-xb))

