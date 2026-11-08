
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
from src.table import track_rows as tr
RECON=paths.RUNS_DIR/'table_reconstruct'
rows=[]
for p in sorted(RECON.glob('*_表头映射.json')):
    stem=p.name.replace('_表头映射.json',''); code=stem[-4:]
    hm=json.load(open(p,encoding='utf-8'))
    if 'sep_pts' not in hm or not hm.get('keep'): continue
    try: w,e,src=tr.content_band(stem)
    except Exception: continue
    if w is None: continue
    def poly(i):
        sp=hm['sep_pts'][i]
        return np.column_stack([np.asarray(sp['ys'],float),np.asarray(sp['xs'],float)])
    desc=[c for c in hm['keep'] if c['name']=='岩性描述']
    if not desc: continue
    ls=desc[0]['left_sep']
    if ls<0 or ls>=len(hm['sep_pts']): continue
    a=poly(ls); ytop,ybot=a[0,0],a[-1,0]
    xb=float(tr.edge_at(a,ybot)); xw=float(np.interp(ybot,np.asarray(w)[:,0],np.asarray(w)[:,1])) if np.asarray(w).ndim==2 else float(w)
    rows.append((code,round(xw,1),round(xb,1),round(xb-xw,1),src))
print('图     带西缘@底   柱状右界@底   错位   出处')
for r in sorted(rows,key=lambda t:-abs(t[3])):
    print('%-5s %9.1f %11.1f %8.1f   %s%s'%(r[0],r[1],r[2],r[3],r[4],'  <<<' if abs(r[3])>40 else ''))

