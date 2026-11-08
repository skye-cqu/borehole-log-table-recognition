
# -*- coding: utf-8 -*-
"""把 1023 列结构定稿第8条(idx=8)的 85 个碎片, 按"离 sep7 多少 px"分类。
   表头带实测格宽 197.8 -> 真格线; 153 -> 柱状图案条边。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
seg={s['id']:np.asarray(s['points'],float) for s in cj['lines']}
c7=[c for c in cs['columns'] if c['index']==7][0]
c8=[c for c in cs['columns'] if c['index']==8][0]
p7=np.vstack([seg[i][np.argsort(seg[i][:,1])] for i in c7['segment_ids'] if i in seg])
WID=hm['sep_x_band'][8]-hm['sep_x_band'][7]
print('sep7 点列 %d 点, y[%.0f,%.0f]   表头带格宽=%.1f'%(len(p7),p7[:,1].min(),p7[:,1].max(),WID))
print()
def sep7_at(y): return float(np.interp(np.clip(y,p7[:,1].min(),p7[:,1].max()),p7[:,1],p7[:,0]))
rows=[]
for i in c8['segment_ids']:
    if i not in seg: continue
    p=seg[i]; yc=float(np.median(p[:,1])); xc=float(np.median(p[:,0]))
    off=xc-sep7_at(yc)
    rows.append((yc,i,xc,off,p[:,1].min(),p[:,1].max()))
rows.sort()
on_true=[r for r in rows if abs(r[3]-WID)<12]
on_band=[r for r in rows if abs(r[3]-153)<12]
other=[r for r in rows if r not in on_true and r not in on_band]
print('第8条(岩性描述左界) 共 %d 个碎片:'%len(rows))
print('  贴真格线  sep7+%.1f : %2d 个,  y[%.0f,%.0f]'%(WID,len(on_true),min(r[4] for r in on_true),max(r[5] for r in on_true)))
print('  贴图案条  sep7+153  : %2d 个,  y[%.0f,%.0f]'%(len(on_band),min(r[4] for r in on_band),max(r[5] for r in on_band)))
print('  其他                : %2d 个'%len(other))
print()
print('=== 换线处逐碎片 ===')
for r in rows:
    if r[5]<8500 or r[4]>9300: continue
    tag='真格线' if abs(r[3]-WID)<12 else ('图案条' if abs(r[3]-153)<12 else '其他')
    print('  seg=%-7d y[%6.0f,%6.0f] x=%7.1f  偏离sep7=%6.1f  %s'%(r[1],r[4],r[5],r[2],r[3],tag))

