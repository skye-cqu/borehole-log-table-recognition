
# -*- coding: utf-8 -*-
"""定量: 柱状列宽(sep#8 - sep#7)沿 y 的走势 + 岩性描述左界应有的位置。"""
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
hh=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(30,1)))>0)
def poly(i):
    sp=hm['sep_pts'][i]
    return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
a7,a8=poly(7),poly(8)
print('  y      sep7     sep8   宽(8-7)  最近真竖墨(在sep7右侧60..260px)')
for y in range(700,11901,400):
    x7=float(tr.edge_at(a7,y)); x8=float(tr.edge_at(a8,y))
    lo=int(x7)+60; hi=int(x7)+260
    b=vv[max(0,y-10):y+11,lo:hi].mean(axis=0)
    idx=np.flatnonzero(b>0.6); grp=[]
    for c in idx:
        if grp and c-grp[-1][-1]<=4: grp[-1].append(c)
        else: grp.append([c])
    ics=[round(lo+sum(g)/len(g),1) for g in grp]
    wid=[round(u-x7,1) for u in ics]
    mark='' if abs((x8-x7)-197)<8 else '   <<< 柱状列宽异常'
    print('%6d %8.1f %8.1f %8.1f   %s%s'%(y,x7,x8,x8-x7,list(zip(ics,wid)),mark))

