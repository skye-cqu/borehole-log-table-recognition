
# -*- coding: utf-8 -*-
"""两处离群的第一性检查: (1) sep#8 折线自身有无跳变 (2) sep#10 在 y=7998 的灰度剖面"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table import track_rows as tr
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape

def poly(i):
    sp=hm['sep_pts'][i]
    return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])

a8=poly(8)
print('=== sep#8 折线自身逐点跳变 (>10px 记为跳变) ===')
d=np.abs(np.diff(a8[:,1]))
for k in np.flatnonzero(d>10):
    print('   y %.0f -> %.0f : x %.1f -> %.1f  (跳 %+.1f)'%(a8[k,0],a8[k+1,0],a8[k,1],a8[k+1,1],a8[k+1,1]-a8[k,1]))
print('   折线总点数',len(a8),' 最大单点跳变 %.1f'%d.max())
print()
print('=== sep#8 按 y 等距取 30 点, 看形状 ===')
for y in np.linspace(a8[0,0],a8[-1,0],30):
    print('   y=%6.0f  x=%7.1f'%(y,tr.edge_at(a8,y)))
print()
a10=poly(10)
print('=== sep#10 在 y=7998 的原始灰度 (x 2900..3000) ===')
row=gray[7998,2900:3001]
print('   ', ' '.join('%d'%v for v in row[::4]))
print('   x:', ' '.join('%d'%x for x in range(2900,3001,4)))
print('   最暗列:', 2900+int(np.argmin(row)), 'gray=', int(row.min()))
print()
print('=== 同位置 y=7998 上下 ±40 行的列均值 (naive 判据) ===')
b=gray[7958:8038,2900:3001].astype(float)
dark=(b<160).mean(axis=0)
top=np.argsort(dark)[::-1][:8]
for k in sorted(top):
    print('   x=%d  dark=%.2f'%(2900+k,dark[k]))

