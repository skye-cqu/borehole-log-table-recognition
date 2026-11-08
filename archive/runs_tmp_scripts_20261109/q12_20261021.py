
# -*- coding: utf-8 -*-
"""宽视野裁片: sep#8 换线区间 (y 8400..9600) 与 sep#10 右侧三线 (y 7000..9000)。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import track_rows as tr
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
OUT=paths.RUNS_DIR/'tmp'/'col_crop_20261021'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
def poly(i):
    sp=hm['sep_pts'][i]
    return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
def draw(idx_list,y0,y1,x0,x1,name,scale,marks=()):
    sub=cv2.cvtColor(gray[y0:y1,x0:x1],cv2.COLOR_GRAY2BGR)
    cols=[(0,0,255),(255,0,0),(0,200,0),(255,0,255)]
    for n,i in enumerate(idx_list):
        a=poly(i); ys=np.linspace(max(y0,a[0,0]),min(y1,a[-1,0]),400)
        if len(ys)<2: continue
        xs=np.array([tr.edge_at(a,y) for y in ys])
        ok=(xs>=x0)&(xs<x1)
        cv2.polylines(sub,[np.column_stack([xs[ok]-x0,ys[ok]-y0]).astype(np.int32)],False,cols[n%4],2)
    for (yy,xx,cc) in marks:
        if x0<=xx<x1 and y0<=yy<y1:
            cv2.circle(sub,(int(xx-x0),int(yy-y0)),9,cc,2)
    big=cv2.resize(sub,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(OUT/name),big); print(name,big.shape)
# sep#8 换线区间, 宽视野含岩性描述文字
draw([8], 8350, 9700, 940, 1300, 'c9_sep8_switch.png', 3)
# sep#10 右侧: 看三条竖线关系
draw([10], 6900, 9100, 2820, 3120, 'c10_sep10_three.png', 3)

