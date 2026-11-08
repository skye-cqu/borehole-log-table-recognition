
# -*- coding: utf-8 -*-
"""页面翘曲不变的混线检测:
   全部列线共享同一个页面翘曲 W(y)。先按各自碎片中位定 c_i,
   再用所有列线求共识 W(y)=median_i(x_i(y)-c_i),
   残差 x_i(y)-c_i-W(y) 就是"这一条线自己的"偏离 -> 混线。
   页面整体弯曲/倾斜被 W 吸收, 只剩单条列线自己的错位。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
Y0,Y1=400,30000
def build(stem):
    cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
    cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
    seg={s['id']:np.asarray(s['points'],float) for s in cj['lines'] if s['direction']=='vertical' and s['label']=='high'}
    cols=[]
    for c in cs['columns']:
        fr=[]
        for i in c.get('segment_ids') or []:
            if i not in seg: continue
            p=seg[i]; fr.append((float(np.median(p[:,1])),float(np.median(p[:,0])),i))
        if len(fr)>=6: cols.append({'idx':c['index'],'name':c.get('name'),'fr':sorted(fr)})
    return cols

hits={}
for code in sorted(p.name.replace('_列结构定稿.json','')[-4:] for p in D.glob('*_列结构定稿.json')):
    stem='钻孔柱状图'+code
    cols=build(stem)
    if len(cols)<3: continue
    ys=np.arange(Y0,Y1,20)
    X={}   # 边界 -> 各 y 的 x
    for ci,c in enumerate(cols):
        fy=np.array([a for a,_,_ in c['fr']]); fx=np.array([b for _,b,_ in c['fr']])
        X[ci]=np.interp(ys,fy,fx)
    # 各边界自身中位偏移
    med=np.array([np.median(X[ci]-ys*0) for ci in X])
    # 共识翘曲: 对每个 y, 取所有边界的 (x_i(y) - 该边界自身基线) 的中位
    # 每条边界基线 = 它自身碎片的稳健线性拟合(去掉混线段)
    base={}
    for ci,c in cols:
        fy=np.array([a for a,_,_ in c['fr']]); fx=np.array([b for _,b,_ in c['fr']])
        A=np.vstack([np.ones_like(fy),fy]).T
        for _ in range(4):
            co,_,_,_=np.linalg.lstsq(A,fx,rcond=None)
            r=fx-A@co; k=np.abs(r)<max(25.0,3*np.median(np.abs(r)))
            if k.sum()<5: break
            A=A[k];fy=fy[k];fx=fx[k]
        co,_,_,_=np.linalg.lstsq(A,fx,rcond=None)
        base[ci]=co
    W=np.zeros(len(ys))
    for j in range(len(ys)):
        vals=[X[ci][j]-(base[ci][0]+base[ci][1]*ys[j]) for ci in X]
        W[j]=np.median(vals)
    bad=[]
    for ci,c in enumerate(cols):
        r=X[ci]-(base[ci][0]+base[ci][1]*ys)+W
        m=np.abs(r)>18.0
        if not m.any(): continue
        # 连续段
        g=[]
        for j in range(len(ys)):
            if m[j]:
                if g and j==g[-1][-1]+1: g[-1].append(j)
                else: g.append([j])
        for gg in g:
            if len(gg)*20>=200:   # 连续 ≥200px
                bad.append({'col':c['idx'],'name':c.get('name'),
                            'y0':int(ys[gg[0]]),'y1':int(ys[gg[-1]]),
                            'off':round(float(np.mean(r[gg])),1),
                            'n_frag':len(c['fr'])})
    if bad: hits[code]=bad
for code in sorted(hits):
    for h in hits[code]:
        print('%-6s 列%-2d %-10s 偏离共识 %.1fpx  y[%5d,%5d]  (该线共%d碎片)'%(
            code,h['col'],str(h['name']),h['off'],h['y0'],h['y1'],h['n_frag']))
print()
print('有混线的图: %d / 30   共 %d 处'%(len(hits),sum(len(v) for v in hits.values())))
json.dump(hits,open('runs/tmp/t9_mixline_warp.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)

