
# -*- coding: utf-8 -*-
"""两处离群点的定量定案 + 影响面。"""
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
a7,a8,a10=poly(7),poly(8),poly(10)
WID=hm['sep_x_band'][8]-hm['sep_x_band'][7]
print('=== 4px 那一点 (y=11421) 的真实情况 ===')
y=11421
s7=float(tr.edge_at(a7,y)); s8=float(tr.edge_at(a8,y))
print('  sep7          = %.1f'%s7)
print('  正确边界      = %.1f  (sep7 + %.1f, 表头带格宽)'%(s7+WID,WID))
print('  现折线        = %.1f  (= sep7 + %.1f)'%(s8,s8-s7))
print('  偏离正确边界  = %+.1f px'%(s8-(s7+WID)))
print('  现折线贴的墨  = %.1f  (柱状图案内条右边 = sep7+153)'%(s7+153))
print('  → 我量到的"4px"是: 折线 vs 它自己那条(错的)墨的差, 不是 vs 正确边界的差')
print()
print('=== 27px 那一点 (y=7998) 的真实情况 ===')
y=7998
x=float(tr.edge_at(a10,y))
print('  折线 x = %.1f'%x)
print('  窗口 ±30 内两条墨: x=2929 (dark=1.00) / x=2957 (dark=1.00)')
print('  我的量尺 = argmax(dark) → 平票时取最小下标 → 2929 → 差 27.5px')
print('  项目量尺 yard_cols = 取离折线最近的墨列 → 2957 → 差 0.5px')
print()
print('=== 影响面: sep#8 错线区间的行数 ===')
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
rows=rd['rows']
def ymid(r):
    p=np.asarray(r['poly'],float)
    return float(np.interp(1200,np.clip(1200,p[:,0].min(),p[:,0].max()),p[:,1]))
n_bad=sum(1 for r in rows if ymid(r)>=8735)
print('  总行 %d, 落在错线区间(y>=8735) %d 行 = %.0f%%'%(len(rows),n_bad,100*n_bad/len(rows)))
print('  这些行的 岩性描述 左界: 正确 %.1f / 实际 %.1f  → 实际更靠左 %+.1f px(格变宽, 不裁字)'%(
    float(tr.edge_at(a7,ymid(rows[-1])))+WID, float(tr.edge_at(a8,ymid(rows[-1]))),
    float(tr.edge_at(a8,ymid(rows[-1])))-(float(tr.edge_at(a7,ymid(rows[-1])))+WID)))
print()
print('=== 柱状列宽(sep8-sep7)全程统计 ===')
ds=[]
for yy in np.linspace(600,11900,300):
    ds.append(float(tr.edge_at(a8,yy))-float(tr.edge_at(a7,yy)))
ds=np.array(ds)
print('  中位 %.1f  最小 %.1f  最大 %.1f'%(np.median(ds),ds.min(),ds.max()))
print('  |宽-197.8|>10 的点: %d/300 = %.0f%%'%((np.abs(ds-WID)>10).sum(),100*(np.abs(ds-WID)>10).mean()))
print('  |宽-153|<12 的点: %d/300 = %.0f%%  (贴到图案条)'%((np.abs(ds-153)<12).sum(),100*(np.abs(ds-153)<12).mean()))

