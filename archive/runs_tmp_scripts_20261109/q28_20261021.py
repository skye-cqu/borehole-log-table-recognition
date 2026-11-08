
# -*- coding: utf-8 -*-
"""定量定案:
  sep#8 = 柱状|岩性描述 边界。真值 = sep7 + 197.8(表头带实测格宽)
  现折线在 y>=8700 落到 sep7+153(柱状图案条右边)
"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import track_rows as tr
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
def poly(i):
    sp=hm['sep_pts'][i]
    return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
a7,a8=poly(7),poly(8)
WIDTH=hm['sep_x_band'][8]-hm['sep_x_band'][7]
print('表头带格宽 sep8-sep7 = %.1f px (表头处只有一条竖线 x=976.0)'%WIDTH)
print()
print('  y       sep7    折线    折线-sep7   偏差(相对%.1f)  落在哪条'%WIDTH)
tot=0; wrong=0
for y in range(600,11901,50):
    s7=float(tr.edge_at(a7,y)); s8=float(tr.edge_at(a8,y))
    d=s8-s7; e=d-WIDTH
    tot+=1
    tag='真边界' if abs(e)<10 else ('图案条边(错)' if abs(d-153)<12 else '其他')
    if tag.startswith('图案'): wrong+=1
    if y%400==0 or tag.startswith('图案') and y%400<50:
        print('%6d %8.1f %8.1f %9.1f  %+8.1f      %s'%(y,s7,s8,d,e,tag))
print()
print('采样 %d 点, 落在图案条边(错) %d 点 = %.1f%%'%(tot,wrong,100*wrong/tot))
# 找切换点
prev=None
for y in range(600,11901,5):
    s7=float(tr.edge_at(a7,y)); d=float(tr.edge_at(a8,y))-s7
    st='ok' if abs(d-WIDTH)<10 else 'bad'
    if prev and st!=prev: print('  切换点 y=%d  %s -> %s  (格宽 %.1f)'%(y,prev,st,d))
    prev=st

