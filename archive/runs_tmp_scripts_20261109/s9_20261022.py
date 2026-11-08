
# -*- coding: utf-8 -*-
"""从项目标准叠加图 PNG 里直接读蓝线(sep_pts)的位置, 证明标准工具画在哪。"""
import sys; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
p=paths.OVERLAY_CHECK_DIR_20260930/'钻孔柱状图1023_叠加全图.png'
img=cv2.imread(str(p))
print('叠加图尺寸', img.shape)
B,G,R=img[:,:,0].astype(int),img[:,:,1].astype(int),img[:,:,2].astype(int)
blue=(B>200)&(G<60)&(R<60)
print('蓝像素总数', int(blue.sum()))
print()
print('  y      该行蓝线 x 位置 (标准 overlay 实际画的)')
for y in (1000,3000,6000,8000,8659,9010,9500,10500,11500,11900):
    xs=np.flatnonzero(blue[y])
    if len(xs)==0:
        print('%6d  无'%y); continue
    grp=[]
    for c in xs:
        if grp and c-grp[-1][-1]<=6: grp[-1].append(c)
        else: grp.append([c])
    print('%6d  %s'%(y,[round(sum(g)/len(g),1) for g in grp]))

