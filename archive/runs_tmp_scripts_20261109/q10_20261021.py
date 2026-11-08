
# -*- coding: utf-8 -*-
"""sep#8 的 351px 空洞: y 8600..9100 原图有没有竖墨?"""
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
sp=hm['sep_pts'][8]
a=np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])

# 1) 折线 y 是否单调/有无空洞
dy=np.diff(a[:,0])
print('sep#8 点数',len(a),' y 单调?',bool((dy>0).all()))
for k in np.flatnonzero(dy>60):
    print('   y 空洞: %.0f -> %.0f  (缺 %.0f px)   x %.1f -> %.1f'%(a[k,0],a[k+1,0],dy[k],a[k,1],a[k+1,1]))
print()
# 2) 空洞区间内原图有没有竖墨 (在 x=1030..1085 范围)
bw=(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)>0).astype(np.uint8)
v=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))>0).astype(np.uint8)
print('  y       折线x   | x=1020..1100 竖墨(每2px)')
for y in range(8500,9200,50):
    xp=tr.edge_at(a,y)
    row=v[y,1020:1100]
    print('%6d  %7.1f   | %s'%(y,xp,''.join('#' if row[i] else '.' for i in range(0,80,2))))
print('x 刻度 1020 + 2*i (40格 -> 1020..1098)')
print()
# 3) 裁片
for (y0,y1,xlo,xhi,name,sc) in [(8550,9150,1010,1100,'c7_sep8_hole.png',5),(11000,12000,1040,1120,'c8_sep8_bot.png',5)]:
    sub=cv2.cvtColor(gray[y0:y1,xlo:xhi],cv2.COLOR_GRAY2BGR)
    ys=np.linspace(y0,y1,300); xs=np.array([tr.edge_at(a,y) for y in ys])
    ok=(xs>=xlo)&(xs<xhi)
    cv2.polylines(sub,[np.column_stack([xs[ok]-xlo,ys[ok]-y0]).astype(np.int32)],False,(0,0,255),1)
    big=cv2.resize(sub,None,fx=sc,fy=sc,interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(str(OUT/name),big); print(name,big.shape)

