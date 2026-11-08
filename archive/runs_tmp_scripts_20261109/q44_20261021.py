
# -*- coding: utf-8 -*-
"""出干净的两张定案裁片(大字标注)。"""
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
a7,a8,a10=poly(7),poly(8),poly(10)

def fig(y0,y1,x0,x1,lines,out,sc,title):
    sub=cv2.cvtColor(gray[y0:y1,x0:x1],cv2.COLOR_GRAY2BGR)
    ys=np.arange(y0,y1)
    for arr,c in lines:
        ok=(arr>=x0)&(arr<x1)
        cv2.polylines(sub,[np.column_stack([arr[ok]-x0,ys[ok]-y0]).astype(np.int32)],False,c,1)
    big=cv2.resize(sub,None,fx=sc,fy=sc,interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(str(OUT/out),big)
    print(out,big.shape,title)

# ---- A: sep#8 下段错线 ----
y0,y1,x0,x1=9500,10100,980,1220
ys=np.arange(y0,y1)
s7=np.array([tr.edge_at(a7,y) for y in ys])
s8=np.array([tr.edge_at(a8,y) for y in ys])
fig(y0,y1,x0,x1,[(s7+197.8,(255,0,0)),(s8,(0,0,255)),(s7+153.5,(0,200,0))],'J1_sep8_lower.png',4,'A')
# ---- B: sep#8 上段正确 ----
y0b,y1b=4500,5100
ysb=np.arange(y0b,y1b)
t7=np.array([tr.edge_at(a7,y) for y in ysb]); t8=np.array([tr.edge_at(a8,y) for y in ysb])
fig(y0b,y1b,x0,x1,[(t7+197.8,(255,0,0)),(t8,(0,0,255)),(t7+153.5,(0,200,0))],'J2_sep8_upper.png',4,'B')
# ---- C: sep#10 右外框 ----
y0c,y1c,x0c,x1c=7800,8200,2900,3010
sub=cv2.cvtColor(gray[y0c:y1c,x0c:x1c],cv2.COLOR_GRAY2BGR)
ysc=np.arange(y0c,y1c)
t10=np.array([tr.edge_at(a10,y) for y in ysc])
ok=(t10>=x0c)&(t10<x1c)
cv2.polylines(sub,[np.column_stack([t10[ok]-x0c,ysc[ok]-y0c]).astype(np.int32)],False,(0,0,255),1)
big=cv2.resize(sub,None,fx=8,fy=8,interpolation=cv2.INTER_NEAREST)
cv2.imwrite(str(OUT/'J3_sep10_frame.png'),big); print('J3',big.shape)

