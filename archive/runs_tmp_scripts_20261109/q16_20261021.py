
# -*- coding: utf-8 -*-
"""判定 sep#8 的两条平行线 A/B 各自身份:
   A(x~1030->1070)  B(x~1073->1121)
   证据: 横向行线的右端点(从图案侧过来)贴 A 还是 B? 左端点(往描述侧去)贴 A 还是 B?
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
hh=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(30,1)))>0)
sp=hm['sep_pts'][8]
a=np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
print('band =',hm['band'],'  sep_x_band[8]=',hm['sep_x_band'][8])

# 横线右端点: 在 x 900..1060 范围内, 横线的最后一段
print()
print('=== 横线右端点(x 900..1080 内的最右连续段) ===')
rows=[]
for y in range(8700,11900):
    idx=np.flatnonzero(hh[y,900:1080])
    if len(idx)>60:
        rows.append((y,900+idx[-1]))
grp=[]
for y,x in rows:
    if grp and y-grp[-1][-1][0]<=3: grp[-1].append((y,x))
    else: grp.append([(y,x)])
for g in grp[:30]:
    ys=[u for u,_ in g]; xs=[v for _,v in g]
    ym=int(np.mean(ys)); xr=int(np.max(xs))
    print('   y=%5d 横线右端x=%4d   折线=%.1f'%(ym,xr,float(tr.edge_at(a,ym))))
print()
print('=== 折线在 y 8700..11900 与最近真竖线(x1000..1200)的差 ===')
vv=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))>0)
for y in range(8700,11901,200):
    xp=float(tr.edge_at(a,y))
    b=vv[max(0,y-10):y+11,1000:1200].mean(axis=0)
    idx=np.flatnonzero(b>0.6); grp2=[]
    for c in idx:
        if grp2 and c-grp2[-1][-1]<=3: grp2[-1].append(c)
        else: grp2.append([c])
    ics=[round(1000+sum(g)/len(g),1) for g in grp2]
    print('   y=%5d 折线=%7.1f  墨=%s'%(y,xp,ics))

