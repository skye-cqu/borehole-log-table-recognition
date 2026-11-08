
# -*- coding: utf-8 -*-
"""证据裁片 4 张: 上段正确/下段错/表头唯一线/右外框 2929 是水文曲线。"""
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
a7,a8=poly(7),poly(8)
WID=hm['sep_x_band'][8]-hm['sep_x_band'][7]

def shot(y0,y1,x0,x1,name,sc,marks=True):
    sub=cv2.cvtColor(gray[y0:y1,x0:x1],cv2.COLOR_GRAY2BGR)
    ys=np.arange(y0,y1)
    s7=np.array([tr.edge_at(a7,y) for y in ys])
    s8=np.array([tr.edge_at(a8,y) for y in ys])
    if marks:
        for (arr,c,lab) in ((s7+WID,(255,0,0),'BLUE = true border (sep7+%.1f)'%WID),
                            (s7+153.5,(0,200,0),'GREEN = hatch-bar edge'),
                            (s8,(0,0,255),'RED = current sep#8')):
            ok=(arr>=x0)&(arr<x1)
            cv2.polylines(sub,[np.column_stack([arr[ok]-x0,ys[ok]-y0]).astype(np.int32)],False,c,1)
        cv2.putText(sub,'B=true border G=bar edge R=current',(3,14),cv2.FONT_HERSHEY_SIMPLEX,0.4,(0,0,0),1)
    cv2.imwrite(str(OUT/name),cv2.resize(sub,None,fx=sc,fy=sc,interpolation=cv2.INTER_NEAREST))
    print(name,(y1-y0)*sc,(x1-x0)*sc)

shot(4700,5400,960,1180,'i1_upper_ok.png',3)
shot(9500,10200,980,1200,'i2_lower_bad.png',3)
shot(555,745,940,1050,'i3_header.png',8,marks=False)

# 右外框: 2929 是水文曲线竖连段
sub=cv2.cvtColor(gray[7650,0:0+1] if False else gray[7600:8350,2850:3010],cv2.COLOR_GRAY2BGR)
ys=np.arange(7600,8350)
x10=np.array([tr.edge_at(poly(10),y) for y in ys])
ok=(x10>=2850)&(x10<3010)
cv2.polylines(sub,[np.column_stack([x10[ok]-2850,ys[ok]-7600]).astype(np.int32)],False,(0,0,255),1)
cv2.circle(sub,(2929-2850,7998-7600),8,(0,255,0),2)
cv2.circle(sub,(2957-2850,7998-7600),8,(255,0,0),2)
cv2.putText(sub,'GREEN=2929 (hydrograph)  RED=2957 (frame)',(2,12),cv2.FONT_HERSHEY_SIMPLEX,0.32,(0,0,0),1)
cv2.imwrite(str(OUT/'i4_right_frame.png'),cv2.resize(sub,None,fx=5,fy=5,interpolation=cv2.INTER_NEAREST))
print('i4',750*5,160*5)

