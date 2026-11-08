
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
cases=[('1023','left_sep',11442,11929),('1025','right_sep',13776,17730),('1028','left_sep',14571,17221)]
for s,side,ya,yb in cases:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    sp=hm['sep_pts'][hm['keep'][0][side]]
    tx=float(sp['xs'][-1])
    cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
    segs=[q for q in cj['lines'] if q['direction']=='vertical' and q['label']=='high']
    hits=[]
    for q in segs:
        a=np.asarray(q['points'],float)
        ys=a[:,1]; xs=a[:,0]
        # does it live in the gap y-range and near tx?
        ov=max(0.0, min(ys.max(),yb)-max(ys.min(),ya))
        if ov<=0: continue
        m=(ys>=ya)&(ys<=yb)
        if m.sum()<2: continue
        mx=float(np.median(xs[m]))
        if abs(mx-tx)<=30:
            hits.append((q['id'],round(float(ys.min())),round(float(ys.max())),round(mx,1),round(ov)))
    print('===',s,side,'tail_x=%.1f gap=[%d,%d] len=%d'%(tx,ya,yb,yb-ya))
    print('   candidate segs near tail x in gap:',len(hits))
    for h in sorted(hits,key=lambda t:-t[4])[:6]: print('     id=%s y=[%d,%d] x=%.1f overlap=%d'%h)
    cov=sum(h[4] for h in hits)
    print('   total overlap px (may double count)=',cov,'gap len',yb-ya)
