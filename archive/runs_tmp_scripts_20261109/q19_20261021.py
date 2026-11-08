
# -*- coding: utf-8 -*-
"""在几个 y 上, 把全部 sep_pts 折线位置与该 y 的真竖墨列并排列出, 看清 A/B 各是谁。"""
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
print('drop_columns:', [(c['name'],c['x_in_band'],c['width']) for c in hm['drop_columns']])
print('keep:', [(c['name'],c['x_in_band']) for c in hm['keep']])
print()
for y in (600,3000,6000,8659,9500,11500):
    b=vv[max(0,y-12):y+13,:2800].mean(axis=0)
    idx=np.flatnonzero(b>0.55); grp=[]
    for c in idx:
        if grp and c-grp[-1][-1]<=4: grp[-1].append(c)
        else: grp.append([c])
    ink=[round(sum(g)/len(g),1) for g in grp]
    pol=[]
    for i,sp in enumerate(hm['sep_pts']):
        ys=np.asarray(sp['ys'],float); xs=np.asarray(sp['xs'],float)
        if ys.min()-1<=y<=ys.max()+1: pol.append((i,round(float(tr.edge_at(np.column_stack([ys,xs]),y)),1)))
    print('y=%5d'%y)
    print('   墨列 :', ink)
    print('   折线 :', pol)

