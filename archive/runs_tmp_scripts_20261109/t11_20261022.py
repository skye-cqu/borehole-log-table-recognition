
# -*- coding: utf-8 -*-
"""混线检测(间距判据, 页面翘曲免疫):
   相邻两列线的间距 w_i(y) = x_{i+1}(y) - x_i(y)。
   表头带实测 w_i(0) 为基准; 页面整体倾斜/弯曲对所有 i 同向作用, 会被约掉。
   |w_i(y) - w_i(0)| 持续 > 25px 的区段 = 这对列线里有一条换了物理线。
   只在两线都有碎片覆盖的 y 上判定(不外推)。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
TOL=25.0; MINLEN=250

def frags(stem, cs, cj):
    seg={s['id']:np.asarray(s['points'],float) for s in cj['lines'] if s['direction']=='vertical' and s['label']=='high'}
    out=[]
    for c in cs['columns']:
        fr=[]
        for i in c.get('segment_ids') or []:
            if i not in seg: continue
            p=seg[i]; fr.append((float(np.median(p[:,1])),float(np.median(p[:,0]))))
        out.append((c['index'],c.get('name'),sorted(fr)))
    return out

def prof(fr, ys):
    fy=np.array([a for a,_ in fr]); fx=np.array([b for _,b in fr])
    ok=(ys>=fy.min()-1)&(ys<=fy.max()+1)
    x=np.full(len(ys),np.nan)
    x[ok]=np.interp(ys[ok],fy,fx)
    return x

hits={}
for code in sorted(p.name.replace('_列结构定稿.json','')[-4:] for p in D.glob('*_列结构定稿.json')):
    stem='钻孔柱状图'+code
    cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
    cols=frags(stem,cs,cj)
    if len(cols)<2: continue
    # 表头带基准间距: 用 sep_x_band
    sb=hm.get('sep_x_band') or []
    # 列线在表头带的位置: 用各线自身在 band 内的插值
    b0,b1=hm['band']
    xs_band=[]
    for idx,name,fr in cols:
        fy=np.array([a for a,_ in fr]); fx=np.array([b for _,b in fr])
        v=np.interp((b0+b1)/2,fy,fx) if fy.min()<=(b0+b1)/2<=fy.max() else np.nan
        xs_band.append(v)
    ys=np.arange(b0,b1+1,10)
    # 全表 y 网格, 每条线插值
    allY=np.arange(300,60000,10)
    X=[]
    for idx,name,fr in cols:
        fy=np.array([a for a,_ in fr]); fx=np.array([b for _,b in fr])
        v=np.interp(allY,fy,fx)
        cov=(allY>=fy.min()-1)&(allY<=fy.max()+1)
        X.append((v,cov))
    for i in range(len(cols)-1):
        v1,c1=X[i]; v2,c2=X[i+1]
        wb=xs_band[i+1]-xs_band[i]
        if not np.isfinite(wb): continue
        w=v2-v1; ok=c1&c2
        d=np.where(ok,w-wb,np.nan)
        m=np.abs(d)>TOL
        if not m.any(): continue
        g=[]
        for j in range(len(allY)):
            if m[j]:
                if g and j==g[-1][-1]+1: g[-1].append(j)
                else: g.append([j])
        for gg in g:
            if len(gg)*10>=MINLEN:
                hits.setdefault(code,[]).append({
                    'left':cols[i][0],'right':cols[i+1][0],'name':cols[i+1][1],
                    'w0':round(float(wb),1),'w1':round(float(np.nanmean(w[gg])),1),
                    'y0':int(allY[gg[0]]),'y1':int(allY[gg[-1]])})
for code in sorted(hits):
    for h in hits[code]:
        print('%-6s 列%d→%d %-10s 间距 表头%.1f → 该段%.1f  差%+.1fpx  y[%5d,%5d]'%(
            code,h['left'],h['right'],str(h['name']),h['w0'],h['w1'],h['w1']-h['w0'],h['y0'],h['y1']))
print()
print('间距异常对: %d / 30 图, 共 %d 处'%(len(hits),sum(len(v) for v in hits.values())))
json.dump(hits,open('runs/tmp/t11_width.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)

