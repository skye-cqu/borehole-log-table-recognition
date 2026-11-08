
# -*- coding: utf-8 -*-
"""x=2929 那条线有多长? 以及 x=3225 是什么。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1023'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
bw=(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)>0).astype(np.uint8)
vv=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))>0).astype(np.uint8)
sub=vv[:,2915:2945]
n,lab,stats,cent=cv2.connectedComponentsWithStats(sub,8)
print('x 2915..2945 的连通域(高>=40):')
for i in range(1,n):
    x,y,w,h,area=stats[i]
    if h<40: continue
    print('  y[%5d,%5d] h=%5d x[%d,%d]'%(y,y+h-1,h,2915+x,2915+x+w-1))
print()
sub2=vv[:,3210:3248]
n2,lab2,st2,_=cv2.connectedComponentsWithStats(sub2,8)
print('x 3210..3248 的连通域(高>=40):')
for i in range(1,n2):
    x,y,w,h,area=st2[i]
    if h<40: continue
    print('  y[%5d,%5d] h=%5d x[%d,%d]'%(y,y+h-1,h,3210+x,3210+x+w-1))
print()
print('=== 右外框(x 2857->3016)与 x=2929 的关系: 2929 只在 y 7998 附近? ===')
col=vv[:,2928:2931].max(axis=1)
ys=np.flatnonzero(col)
print('  x=2928..2930 有竖墨的 y 范围: %s ... %s'%(ys.min() if len(ys) else None, ys.max() if len(ys) else None))
# 分段
grp=[]
for y in ys:
    if grp and y-grp[-1][-1]<=5: grp[-1].append(y)
    else: grp.append([y])
print('  段数=%d'%len(grp), [(g[0],g[-1]) for g in grp][:10])

