
# -*- coding: utf-8 -*-
"""最朴素检验: 在某条行分隔线上, 从 x=1000 向右扫, 第一个连续暗像素在哪。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1023'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
for y in (9497,9570,9741,9861,10337,11071):
    best=None
    for yy in range(y-2,y+3):
        row=gray[yy,1000:1600]
        dark=row<170
        # 找最长连续暗段
        k=0; runs=[]
        s=None
        for i,d in enumerate(dark):
            if d and s is None: s=i
            elif not d and s is not None: runs.append((s,i-1)); s=None
        if s is not None: runs.append((s,len(dark)-1))
        runs=[(a,b) for a,b in runs if b-a>=30]
        if runs:
            a,b=runs[0]
            if best is None or a<best[0]: best=(a,b,yy)
    if best:
        print('y=%5d  最长暗段起点 x=%4d  终点 x=%4d  (在 y=%d)'%(y,1000+best[0],1000+best[1],best[2]))
    else:
        print('y=%5d  无 >=30px 暗段'%y)
print()
print('=== 同一方法量"正确"区 y=5000 附近 ===')
for y in (4928,4998,5104,5255):
    for yy in range(y-2,y+3):
        row=gray[yy,950:1600]
        dark=row<170
        s=None; runs=[]
        for i,d in enumerate(dark):
            if d and s is None: s=i
            elif not d and s is not None: runs.append((s,i-1)); s=None
        if s is not None: runs.append((s,len(dark)-1))
        runs=[(a,b) for a,b in runs if b-a>=30]
        if runs:
            print('y=%5d 暗段起点 x=%4d'%(y,950+runs[0][0])); break

