
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
print('列结构定稿 keys:',list(cs.keys()))
cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
seg={s['id']:np.asarray(s['points'],float) for s in cj['lines']}
print()
for k in ('recoveries','notes','warnings'):
    if k in cs: print(k,':',json.dumps(cs[k],ensure_ascii=False)[:400])
print()
print('=== columns 各条: segment_ids 的 x 分布 ===')
for c in cs['columns']:
    ids=c.get('segment_ids') or []
    xs=[seg[i][:,0] for i in ids if i in seg]
    if not xs: 
        print('  idx=%s 无点'%c.get('index')); continue
    allx=np.concatenate(xs)
    print('  idx=%-3s x_at_mid=%-8.1f n_seg=%-4d  x[%7.1f,%7.1f]  跨度=%5.1f'%(
        c.get('index'),c['x_at_mid'],len(ids),allx.min(),allx.max(),allx.max()-allx.min()))
print()
print('=== 重点: idx=8 (岩性描述左界) 逐段 x ===')
for c in cs['columns']:
    if c.get('index')!=8: continue
    for i in c['segment_ids']:
        if i not in seg: continue
        p=seg[i]
        print('   seg=%-7d x[%7.1f,%7.1f] y[%6.0f,%6.0f]'%(i,p[:,0].min(),p[:,0].max(),p[:,1].min(),p[:,1].max()))

