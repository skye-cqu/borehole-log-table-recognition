
# -*- coding: utf-8 -*-
"""assumption-free: 岩性描述的行分隔横线, 左端点落在哪?
   只在"向右至少延伸到 x=1400"的横线上找左端 -> 那是描述列的行线, 不是柱状花纹。
"""
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
hh=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(60,1)))>0)
def poly(i):
    sp=hm['sep_pts'][i]
    return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
a7,a8=poly(7),poly(8)
print('  y      横线左端  sep7    左端-sep7   sep8折线  sep8-sep7   判断')
res=[]
for y in range(8600,11900):
    row=hh[y,900:1450]
    if not row.any(): continue
    idx=np.flatnonzero(row)
    # 必须延伸到 x>=1400
    if 1400-900 > idx[-1]: continue
    xl=900+idx[0]
    res.append((y,xl))
# 合并相邻
grp=[]
for y,xl in res:
    if grp and y-grp[-1][-1][0]<=3: grp[-1].append((y,xl))
    else: grp.append([(y,xl)])
for g in grp:
    ym=int(np.mean([a for a,_ in g])); xl=int(np.min([b for _,b in g]))
    s7=float(tr.edge_at(a7,ym)); s8=float(tr.edge_at(a8,ym))
    print('%6d  %6d  %7.1f  %8.1f  %8.1f  %8.1f   %s'%(ym,xl,s7,xl-s7,s8,s8-s7,
        'OK' if abs(xl-s8)<8 else '折线偏离横线左端 %+.0fpx'%(s8-xl)))
print()
print('=== 对照: 上半段 y 3000..8000 ===')
res=[]
for y in range(3000,8000):
    row=hh[y,900:1450]
    if not row.any(): continue
    idx=np.flatnonzero(row)
    if 1400-900 > idx[-1]: continue
    res.append((y,900+idx[0]))
grp=[]
for y,xl in res:
    if grp and y-grp[-1][-1][0]<=3: grp[-1].append((y,xl))
    else: grp.append([(y,xl)])
for g in grp:
    ym=int(np.mean([a for a,_ in g])); xl=int(np.min([b for _,b in g]))
    s7=float(tr.edge_at(a7,ym)); s8=float(tr.edge_at(a8,ym))
    print('%6d  %6d  %7.1f  %8.1f  %8.1f  %8.1f   %s'%(ym,xl,s7,xl-s7,s8,s8-s7,
        'OK' if abs(xl-s8)<8 else '折线偏离 %+.0fpx'%(s8-xl)))

