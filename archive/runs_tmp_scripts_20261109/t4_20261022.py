
# -*- coding: utf-8 -*-
"""全库: 列结构定稿每条列/框/内容 的 src(=no) → 重建 gidx → Agnes 判定。
   目的: 找"Agnes 判 column 但定稿没当列线" 与 "定稿当列线但 Agnes 判 content/frame"。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'

def rebuild(stem):
    cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
    cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
    seg={s['id']:s for s in cj['lines'] if s['direction']=='vertical' and s['label']=='high'}
    tr=[]
    def add(role,src,ids):
        ids=[i for i in ids if i in seg]
        if not ids: return
        pts=np.asarray([p for i in ids for p in seg[i]['points']],float)
        tr.append({'role_hint':role,'src':src,'gidx':0,
                   'x_mid':float(np.median(pts[:,0])),'n':len(ids)})
    for c in cs['columns']: add('sep',c.get('src'),c.get('segment_ids') or [])
    for f in cs['frames']:  add('frame',f.get('src'),f.get('segment_ids') or [])
    for c in cs.get('content') or []: add('sep',c.get('src'),c.get('segment_ids') or [])
    for o in cs.get('others') or []: add('other','other',o.get('track_ids') or [])
    tr.sort(key=lambda t:t['x_mid'])
    for i,t in enumerate(tr): t['gidx']=i+1
    return tr

out={}
for code in sorted(p.name.replace('_列结构定稿.json','')[-4:] for p in D.glob('*_列结构定稿.json')):
    stem='钻孔柱状图'+code
    tr=rebuild(stem)
    v=json.load(open(D/f'{stem}_全竖线判定.json',encoding='utf-8'))
    vm={int(k):x for k,x in v['merged_by_track'].items()}
    cols=[t for t in tr if t['role_hint']=='sep']
    # 定稿里当列线的(src 来自 columns)
    cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
    colsrc=set(str(c.get('src')) for c in cs['columns'])
    rows=[]
    for t in cols:
        a=vm.get(t['gidx'],'未判')
        rows.append({'src':t['src'],'gidx':t['gidx'],'x_mid':round(t['x_mid'],1),
                     'agnes':a,'is_col':t['src'] in colsrc})
    # Agnes 判 column 但不在定稿列线里的
    agcol=set(g for g,x in vm.items() if x=='column')
    used=set(t['gidx'] for t in cols if t['src'] in colsrc)
    missing=sorted(agcol-used)
    out[code]={'rows':rows,'missing':missing,
               'n_ag_col':len(agcol),'n_used':len(used)}
json.dump(out,open('runs/tmp/t4_final_vs_agnes.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)

print('图     定稿列线  Agnes判column  两者一致  定稿当列但Agnes非column  Agnes判column但未采用')
for code in sorted(out):
    o=out[code]
    bad=[r for r in o['rows'] if r['is_col'] and r['agnes'] not in ('column',)]
    print('%-6s %5d %12d %10s %22s %20s'%(code,o['n_used'],o['n_ag_col'],
        'OK' if not bad and not o['missing'] else '有差',
        ','.join('no%s/g%s=%s'%(r['src'],r['gidx'],r['agnes']) for r in bad) or '-',
        ','.join(str(g) for g in o['missing']) or '-'))

