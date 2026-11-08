
# -*- coding: utf-8 -*-
"""全库检测"同一条列线的碎片里混进了另一条平行线":
   对列结构定稿每条列线的碎片, 按 y 排序, 用整条线做稳健线性拟合 x=a+b*y,
   找连续成组的残差 > 15px 的碎片 (= 贴到了另一条平行线)。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
TOL=15.0
out={}
for code in sorted(p.name.replace('_列结构定稿.json','')[-4:] for p in D.glob('*_列结构定稿.json')):
    stem='钻孔柱状图'+code
    cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
    cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
    seg={s['id']:np.asarray(s['points'],float) for s in cj['lines'] if s['direction']=='vertical' and s['label']=='high'}
    hits=[]
    for c in cs['columns']:
        fr=[]
        for i in c.get('segment_ids') or []:
            if i not in seg: continue
            p=seg[i]
            fr.append((float(np.median(p[:,1])),float(np.median(p[:,0])),i))
        if len(fr)<8: continue
        fr.sort()
        Y=np.array([a for a,_,_ in fr]); X=np.array([b for _,b,_ in fr])
        # 稳健拟合: 先全拟合, 去残差大的, 再拟合
        A=np.vstack([np.ones_like(Y),Y]).T
        for _ in range(3):
            coef,_,_,_=np.linalg.lstsq(A,X,rcond=None)
            r=X-A@coef
            keep=np.abs(r)<max(TOL*2,np.median(np.abs(r))*3)
            if keep.sum()<6: break
            A=A[keep]; Y=Y[keep]; X=X[keep]
        coef,_,_,_=np.linalg.lstsq(A,X,rcond=None)
        r=np.array([b-(coef[0]+coef[1]*a) for a,b,_ in fr])
        bad=np.abs(r)>TOL
        if bad.any():
            # 成组: 连续段
            grp=[]
            for k in range(len(fr)):
                if bad[k]:
                    if grp and k==grp[-1][-1]+1: grp[-1].append(k)
                    else: grp.append([k])
            for g in grp:
                if len(g)>=3:
                    hits.append({'col':c['index'],'name':c.get('name'),'n':len(g),
                                 'y0':round(fr[g[0]][0]),'y1':round(fr[g[-1]][0]),
                                 'off':round(float(np.mean(r[g])),1),
                                 'n_all':len(fr)})
    if hits: out[code]=hits
for code in sorted(out):
    for h in out[code]:
        print('%-6s 列%-2d %-8s 混线碎片 %2d/%-3d  y[%5d,%5d]  偏离主拟合 %+6.1fpx'%(
            code,h['col'],str(h['name']),h['n'],h['n_all'],h['y0'],h['y1'],h['off']))
print()
print('有混线的图: %d / 30   共 %d 条列线'%(len(out),sum(len(v) for v in out.values())))
json.dump(out,open('runs/tmp/t8_mixline.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)

