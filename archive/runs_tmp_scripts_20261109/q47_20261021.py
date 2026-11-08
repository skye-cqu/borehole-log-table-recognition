
# -*- coding: utf-8 -*-
"""归属问题还是桥接问题? 阶段4 在 y 9010..11900 有没有 x~1081 的竖碎片, 它被分给了谁。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
stem='钻孔柱状图1023'
cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
verts=[s for s in cj['lines'] if s['direction']=='vertical']
print('阶段4 竖段总数',len(verts))
hits=[]
for s in verts:
    p=np.asarray(s['points'],float)
    if p[:,1].min()>8900 and p[:,1].max()<12100:
        xm=float(np.median(p[:,0]))
        if 1060<=xm<=1105:
            hits.append((s['id'],round(xm,1),round(p[:,1].min()),round(p[:,1].max()),s.get('label'),len(p)))
print('y 8900..12100 且 x 1060..1105 的竖段: %d 条'%len(hits))
for h in sorted(hits,key=lambda t:t[2])[:40]:
    print('   id=%-7d x=%7.1f y[%5d,%5d] label=%-6s npts=%d'%h)
print()
# 这些 id 被分到哪条线
d=json.load(open(paths.RUNS_DIR/'table_reconstruct'/f'{stem}_分割线.json',encoding='utf-8'))
owner={}
for ln in d['lines']:
    for sid in ln.get('_orig_ids',[]):
        owner.setdefault(sid,[]).append('%s%s'%(ln['kind'],ln.get('index')))
for h in sorted(hits,key=lambda t:t[2]):
    print('   id=%-7d x=%7.1f y[%5d,%5d] -> %s'%(h[0],h[1],h[2],h[3],owner.get(h[0],['未归属'])))

