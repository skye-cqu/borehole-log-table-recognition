
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
seg={s['id']:np.asarray(s['points'],float) for s in cj['lines'] if s['direction']=='vertical' and s['label']=='high'}
b0,b1=hm['band']; ymid=(b0+b1)/2
print('band',b0,b1,'ymid',ymid)
for c in cs['columns']:
    fr=[]
    for i in c.get('segment_ids') or []:
        if i not in seg: continue
        p=seg[i]; fr.append((float(np.median(p[:,1])),float(np.median(p[:,0]))))
    fr.sort()
    fy=np.array([a for a,_ in fr]); fx=np.array([b for _,b in fr])
    v=np.interp(ymid,fy,fx) if fy.min()<=ymid<=fy.max() else float('nan')
    print('  idx=%-2d y范围[%6.0f,%6.0f] band内插值=%8.1f  n=%d'%(c['index'],fy.min(),fy.max(),v,len(fr)))

