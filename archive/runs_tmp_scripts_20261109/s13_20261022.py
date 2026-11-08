
# -*- coding: utf-8 -*-
"""逐碎片打印第8条全部 85 个碎片相对 sep7 的偏移, 按 y 排序。"""
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
# sep7: 每个 y 取所有 c7 碎片中最近的点
P7=np.vstack([seg[i] for i in c7['segment_ids'] if i in seg])
P7=P7[np.argsort(P7[:,1])]
print('p7 y 单调?',bool((np.diff(P7[:,1])>=0).all()),' 点数',len(P7))
WID=hm['sep_x_band'][8]-hm['sep_x_band'][7]
print('格宽=%.1f'%WID)
print()
print('   y中位     seg       x中位   偏离sep7   判')
for i in c8['segment_ids']:
    if i not in seg: continue
    p=seg[i]; yc=float(np.median(p[:,1])); xc=float(np.median(p[:,0]))
    off=xc-float(np.interp(yc,P7[:,1],P7[:,0]))
    tag='真格线' if abs(off-WID)<12 else ('图案条' if abs(off-153)<12 else '其他')
    print('%8.0f  %-8d %8.1f %8.1f   %s'%(yc,i,xc,off,tag))

