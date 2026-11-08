
# -*- coding: utf-8 -*-
"""sep#10 离群点上下文: 宽视野看 y=7998 附近到底有几条竖线。"""
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
sp=hm['sep_pts'][10]
a=np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])

def wide(y0,y1,xlo,xhi,name,scale=2,marks=()):
    sub=cv2.cvtColor(gray[y0:y1,xlo:xhi],cv2.COLOR_GRAY2BGR)
    ys=np.linspace(y0,y1,300)
    xs=np.array([tr.edge_at(a,y) for y in ys])
    ok=(xs>=xlo)&(xs<xhi)
    pts=np.column_stack([xs[ok]-xlo, ys[ok]-y0]).astype(np.int32)
    cv2.polylines(sub,[pts],False,(0,0,255),2)
    for (yy,xx,cc,lab) in marks:
        if xlo<=xx<xhi:
            cv2.circle(sub,(int(xx-xlo),int(yy-y0)),10,cc,2)
    big=cv2.resize(sub,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(OUT/name),big)
    print(name, big.shape)

# 宽视野: 整个表格右侧 + 页边
wide(7400,8700,2750,W,'c5_wide_right.png',2,[(7998,2956,(0,0,255),'poly'),(7998,2929,(0,255,0),'naive')])
# 极宽: 全表宽在 y=7998 一行
wide(7900,8100,0,W,'c6_wide_row.png',1,[(7998,2956,(0,0,255),'poly'),(7998,2929,(0,255,0),'naive')])

