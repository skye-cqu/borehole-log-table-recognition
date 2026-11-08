
# -*- coding: utf-8 -*-
"""sep#8 到底贴哪条线: 在 x 950..1150 逐 y 列出所有竖墨列, 对比折线。"""
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
v=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))>0).astype(np.uint8)
sp=hm['sep_pts'][8]
a=np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])

def inkcols(y,x0=950,x1=1160,minrun=25):
    """该 y 附近 ±12 行里, x 上有竖墨的连续段(段高≥minrun 才算真竖线)"""
    b=v[max(0,y-12):y+13, x0:x1]
    col=b.mean(axis=0)
    idx=np.flatnonzero(col>0.6)
    grp=[]
    for c in idx:
        if grp and c-grp[-1][-1]<=3: grp[-1].append(c)
        else: grp.append([c])
    return [round(x0+sum(g)/len(g),1) for g in grp]

print('  y      折线x    该行竖墨列(x950..1160)                    折线贴哪条')
for y in range(700,11900,400):
    xp=float(tr.edge_at(a,y))
    ics=inkcols(y)
    if ics:
        k=int(np.argmin([abs(u-xp) for u in ics]))
        tag='%s(差%+.1f)'%(ics[k], ics[k]-xp)
    else:
        tag='无墨'
    print('%6d  %8.1f   %-42s %s'%(y,xp,str(ics),tag))

