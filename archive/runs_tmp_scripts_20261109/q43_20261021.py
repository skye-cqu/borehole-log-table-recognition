
# -*- coding: utf-8 -*-
"""最后确认: 1023 的 sep#8 在 y>=8735 贴的是"柱状图案的填充条边"还是"格线"。
   判据: 该线在 x 方向的左侧是否还有一条更长的、一直延伸到 y 底部的竖线。
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
vv=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))>0).astype(np.uint8)
def poly(i):
    sp=hm['sep_pts'][i]
    return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
a7,a8=poly(7),poly(8)
# 在 y 9000..11900 内, 统计 x=sep7+153 与 x=sep7+197 两条线的"存在率"
n=0; c153=0; c197=0
for y in range(9000,11900,10):
    s7=float(tr.edge_at(a7,y)); n+=1
    for off,key in ((153,'a'),(197,'b')):
        x=int(s7+off)
        if vv[max(0,y-15):y+16, x-4:x+5].any():
            if key=='a': c153+=1
            else: c197+=1
print('y 9000..11900 采样 %d 点:'%n)
print('  x=sep7+153 (图案条边)  有墨 %d = %.0f%%'%(c153,100*c153/n))
print('  x=sep7+197 (真格线)    有墨 %d = %.0f%%'%(c197,100*c197/n))
print()
# 同法量上段
n2=0; a2=0; b2=0
for y in range(1000,8000,10):
    s7=float(tr.edge_at(a7,y)); n2+=1
    for off,key in ((153,'a'),(197,'b')):
        x=int(s7+off)
        if vv[max(0,y-15):y+16, x-4:x+5].any():
            if key=='a': a2+=1
            else: b2+=1
print('y 1000..8000 采样 %d 点:'%n2)
print('  x=sep7+153 有墨 %d = %.0f%%'%(a2,100*a2/n2))
print('  x=sep7+197 有墨 %d = %.0f%%'%(b2,100*b2/n2))

