
# -*- coding: utf-8 -*-
"""间距判据 v2: 基准宽度取"所有列线共同有碎片覆盖"的最上端 y 处, 而不是表头带。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
TOL=25.0; MINLEN=250
hits={}
for code in sorted(p.name.replace('_列结构定稿.json','')[-4:] for p in D.glob('*_列结构定稿.json')):
    stem='钻孔柱状图'+code
    cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
    cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
    seg={s['id']:np.asarray(s['points'],float) for s in cj['lines'] if s['direction']=='vertical' and s['label']=='high'}
    cols=[]
    for c in cs['columns']:
        fr=[]
        for i in c.get('segment_ids') or []:
            if i not in seg: continue
            p=seg[i]; fr.append((float(np.median(p[:,1])),float(np.median(p[:,0]))))
        if len(fr)>=6: cols.append((c['index'],c.get('name'),sorted(fr)))
    if len(cols)<2: continue
    allY=np.arange(300,60000,10)
    X=[];COV=[]
    for idx,name,fr in cols:
        fy=np.array([a for a,_ in fr]); fx=np.array([b for _,b in fr])
        X.append(np.interp(allY,fy,fx))
        COV.append((allY>=fy.min()-1)&(allY<=fy.max()+1))
    for i in range(len(cols)-1):
        both=COV[i]&COV[i+1]
        if not both.any(): continue
        # 基准: 两者共同覆盖区里最靠上的一段(取前 1500px 内的中位间距)
        ys_ok=allY[both]
        y0=ys_ok.min()
        base_mask=both&(allY<=y0+1500)
        if base_mask.sum()<10: continue
        w=(X[i+1]-X[i])[base_mask]
        wb=float(np.median(w))
        d=np.where(both,(X[i+1]-X[i])-wb,np.nan)
        m=np.abs(d)>TOL
        if not m.any(): continue
        g=[]
        for j in range(len(allY)):
            if m[j]:
                if g and j==g[-1][-1]+1: g[-1].append(j)
                else: g.append([j])
        for gg in g:
            if len(gg)*10>=MINLEN:
                w1=float(np.nanmean((X[i+1]-X[i])[gg]))
                hits.setdefault(code,[]).append({'left':cols[i][0],'right':cols[i+1][0],
                    'name':cols[i+1][1],'w0':round(wb,1),'w1':round(w1,1),
                    'y0':int(allY[gg[0]]),'y1':int(allY[gg[-1]])})
for code in sorted(hits):
    for h in hits[code]:
        print('%-6s 列%d→%d %-10s 间距 基准%.1f → 该段%.1f  差%+.1fpx  y[%5d,%5d]'%(
            code,h['left'],h['right'],str(h['name']),h['w0'],h['w1'],h['w1']-h['w0'],h['y0'],h['y1']))
print()
print('间距异常对: %d / 30 图, 共 %d 处'%(len(hits),sum(len(v) for v in hits.values())))
json.dump(hits,open('runs/tmp/t13_width2.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)

