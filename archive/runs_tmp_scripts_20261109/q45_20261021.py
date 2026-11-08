
# -*- coding: utf-8 -*-
"""全库: 柱状带(content_band)是表头带定的固定 x 区间, 但表体随倾斜右漂。
   量每张图"带"与"实际柱状列"在表底的错位量, 看 1023 是不是孤例。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table import track_rows as tr
RECON=paths.RUNS_DIR/'table_reconstruct'
rows=[]
for p in sorted(RECON.glob('*_表头映射.json')):
    stem=p.name.replace('_表头映射.json','')
    code=stem[-4:]
    hm=json.load(open(p,encoding='utf-8'))
    if 'sep_pts' not in hm or not hm.get('keep'): continue
    try:
        w,e,src=tr.content_band(stem)
    except Exception as ex:
        continue
    if w is None: continue
    def poly(i):
        sp=hm['sep_pts'][i]
        return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
    # 柱状列 = 岩性描述 左邻格: keep 里 岩性描述 的 left_sep 就是柱状右界
    desc=[c for c in hm['keep'] if c['name']=='岩性描述']
    if not desc: continue
    rs=desc[0]['right_sep'] if desc[0]['right_sep']>=0 else None
    ls=desc[0]['left_sep']
    if ls<0 or ls>=len(hm['sep_pts']): continue
    a=poly(ls)
    ytop,ybot=a[0,0],a[-1,0]
    xb=float(tr.edge_at(a,ybot))
    drift=xb-float(tr.edge_at(a,ytop))
    rows.append((code,round(w,1),round(e,1),round(xb,1),round(drift,1),round(xb-(w+e)/2,1)))
print('图    带左   带右   柱状右界@底  漂移   相对带中心偏移')
for r in sorted(rows,key=lambda t:-abs(t[5])):
    flag='  <<<' if abs(r[5])>60 else ''
    print('%-5s %7.1f %7.1f %10.1f %7.1f %12.1f%s'%(r[0],r[1],r[2],r[3],r[4],r[5],flag))

