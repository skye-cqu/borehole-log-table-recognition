
# -*- coding: utf-8 -*-
"""1023 两处离群点放大裁片: sep#8 岩性描述左界(底段) / sep#10 右外框(y=7998)。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import track_rows as tr

stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
OUT=paths.RUNS_DIR/'tmp'/'col_crop_20261021'
OUT.mkdir(parents=True, exist_ok=True)
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
color=cv2.cvtColor(gray,cv2.COLOR_GRAY2BGR)

def poly(idx):
    sp=hm['sep_pts'][idx]
    return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])

def crop(idx, y0, y1, xpad, name, scale=3, marks=()):
    a=poly(idx)
    ys=np.linspace(y0,y1,200)
    xs=np.array([tr.edge_at(a,y) for y in ys])
    xlo=int(xs.min())-xpad; xhi=int(xs.max())+xpad
    sub=color[y0:y1, max(0,xlo):min(W,xhi)].copy()
    # 折线
    pts=np.column_stack([(xs-max(0,xlo)), (ys-y0)]).astype(np.int32)
    cv2.polylines(sub,[pts],False,(0,0,255),2)
    for (yy,xx,cc) in marks:
        cv2.circle(sub,(int(xx-max(0,xlo)),int(yy-y0)),14,cc,3)
    big=cv2.resize(sub,None,fx=scale,fy=scale,interpolation=cv2.INTER_NEAREST)
    p=OUT/name; cv2.imwrite(str(p),big)
    print(f'{name}  x[{max(0,xlo)},{min(W,xhi)}] y[{y0},{y1}]  -> {big.shape[1]}x{big.shape[0]}')
    return p

# sep#8: 底段 y 10800..12000, 折线在 x 1063..1077
crop(8, 10800, 12000, 60, 'c1_sep8_bottom.png', 3, [(10951,1066,(0,255,0)),(11421,1074,(255,0,0)),(11890,1080,(0,255,255))])
# sep#8: 中段 y 8000..8700 (含 8135 无墨点)
crop(8, 7950, 8750, 60, 'c2_sep8_mid.png', 3, [(8135,1069,(0,255,0))])
# sep#10: y 7900..8100 离群点
crop(10, 7850, 8150, 80, 'c3_sep10_y7998.png', 5, [(7998,2956,(0,0,255)),(7998,2929,(0,255,0))])
# sep#10: 全段缩略
crop(10, 555, 12483, 60, 'c4_sep10_full.png', 1, [(7998,2956,(0,0,255))])

