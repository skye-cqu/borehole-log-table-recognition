
# -*- coding: utf-8 -*-
"""先验检验用户假设: 数据对不对, 还是我画错了?
   判据: 交付用的裁片左界 vs 该行岩性描述首字墨迹左缘。
   裁界 <= 首字左缘  -> 不切字(数据没错)
   裁界 >  首字左缘  -> 切字(数据真错)
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
def poly(i):
    sp=hm['sep_pts'][i]
    return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
a8=poly(8)
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
rows=rd['rows']
def ymid(r):
    p=np.asarray(r['poly'],float)
    return float(np.interp(1200,p[:,0],p[:,1]))
# 逐行: 裁界(现折线) vs 该行带内最左文字墨
print('行  y      裁界x   首字墨左缘  余量(裁界-墨)  判定')
cut_text=0; n=0
for i,r in enumerate(rows):
    y=ymid(r)
    if y<8735: continue
    n+=1
    xc=float(tr.edge_at(a8,y))
    band=gray[max(0,int(y)-8):int(y)+9, int(xc):int(xc)+300]
    if band.size==0: continue
    dark=(band<150)
    # 每列墨量, 找第一列有像"字"的墨(>=3px高)
    col=dark.sum(axis=0)
    idx=np.flatnonzero(col>=3)
    if len(idx)==0: continue
    x_ink=xc+idx[0]
    margin=xc-x_ink
    bad=margin>0
    if bad: cut_text+=1
    if n<=14 or bad:
        print('%-3d %6.0f %8.1f %9.1f %12.1f   %s'%(i+1,y,xc,x_ink,margin,'切字!' if bad else 'ok'))
print()
print('y>=8735 行数 %d, 其中裁界切进文字的 %d 行'%(n,cut_text))

