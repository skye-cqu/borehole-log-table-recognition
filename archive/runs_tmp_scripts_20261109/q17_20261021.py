
# -*- coding: utf-8 -*-
"""把 x 940..1160 区间内的所有长竖线整条提出来(连通域), 看有几条、各占多长。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1023'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
bw=(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)>0).astype(np.uint8)
vv=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))>0).astype(np.uint8)
sub=vv[:, 900:1200]
n,lab,stats,cent=cv2.connectedComponentsWithStats(sub,8)
print('连通域数(高≥60px):')
rows=[]
for i in range(1,n):
    x,y,w,h,area=stats[i]
    if h<60: continue
    rows.append((y,h,900+x,900+x+w-1,w,area))
for y,h,x0,x1,w,area in sorted(rows):
    print('  y[%5d,%5d] h=%5d  x[%7d,%7d] w=%2d  墨密度%.2f'%(y,y+h-1,h,x0,x1,w,area/(h*max(1,w))))
print()
print('=== 表头带 y 563..726 内的竖墨列 ===')
band=vv[563:727,900:1200].mean(axis=0)
idx=np.flatnonzero(band>0.6); grp=[]
for c in idx:
    if grp and c-grp[-1][-1]<=3: grp[-1].append(c)
    else: grp.append([c])
print('  ', [round(900+sum(g)/len(g),1) for g in grp])
print('  sep_x_band[7]=%.1f  sep_x_band[8]=%.1f'%(hm7:=json.load(open(str(paths.RUNS_DIR/'table_reconstruct'/f'{stem}_表头映射.json'),encoding='utf-8'))['sep_x_band'][7],
      hm7['sep_x_band'][8]))

