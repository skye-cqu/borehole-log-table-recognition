
# -*- coding: utf-8 -*-
"""sep#8: A线 与 B线 谁是真列界? 全表高范围内用"横线左端点"投票。"""
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
sp=hm['sep_pts'][8]
a=np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])

# 折线自身: 在哪些 y 段贴 A, 哪些贴 B
print('=== 折线 sep#8 逐 400px 采样: 折线 x / 该处两条线位置 ===')
for y in range(700,11900,400):
    xp=float(tr.edge_at(a,y))
    b=vv[max(0,y-10):y+11, 980:1160].mean(axis=0)
    idx=np.flatnonzero(b>0.6)
    grp=[]
    for c in idx:
        if grp and c-grp[-1][-1]<=3: grp[-1].append(c)
        else: grp.append([c])
    ics=[round(980+sum(g)/len(g),1) for g in grp]
    near=min(ics,key=lambda u:abs(u-xp)) if ics else None
    print('  y=%6d 折线=%7.1f  墨=%s  最近=%s 差=%s'%(y,xp,ics,near,('n/a' if near is None else '%+.1f'%(near-xp))))
print()
print('=== 横线左端点投票 (x 900..1300, 表高 700..11800) ===')
rows=[]
for y in range(700,11800):
    idx=np.flatnonzero(hh[y,900:1300])
    if len(idx)>60: rows.append((y,900+idx[0]))
grp=[]
for y,x in rows:
    if grp and y-grp[-1][-1][0]<=3: grp[-1].append((y,x))
    else: grp.append([(y,x)])
print('  横线条数(合并后):',len(grp))
for g in grp:
    ys=[u for u,_ in g]; xs=[v for _,v in g]
    ym=int(np.mean(ys)); xl=int(np.min(xs))
    xp=float(tr.edge_at(a,ym))
    print('   y=%5d 左端x=%4d  折线=%.1f  差=%+6.1f'%(ym,xl,xp,xl-xp))

