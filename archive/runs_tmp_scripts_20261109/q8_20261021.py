
# -*- coding: utf-8 -*-
"""sep#10 到底贴的是哪条线: 在 x 2850..3100 逐列统计竖墨占比(局部窗)。"""
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
v=cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))
v=(v>0).astype(np.uint8)
sp=hm['sep_pts'][10]
a=np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])

print('  y      poly   |  x=2850..3100 竖墨占比(每2px) ')
for y in [7000,7500,7900,7998,8100,8500,9000,9500,9970,10500]:
    row=v[y,2850:3100]
    segs=''.join('#' if row[i] else '.' for i in range(0,250,2))
    pred=float(tr.edge_at(a,y))
    print(f'{y:6d}  {pred:7.1f}  | {segs}')
print()
print('x 刻度: 2850 + 2*i, 共 125 格 -> 2850..3098')
print()
# 整列竖向覆盖率(在 y 7000..10000 之间)
band=v[7000:10000,2850:3100].mean(axis=0)
print('x=2850..3100 在 y7000..10000 的竖墨占比 (>0.5 的列):')
for i,val in enumerate(band):
    if val>0.5: print('   x=%d  %.2f'%(2850+i,val))

