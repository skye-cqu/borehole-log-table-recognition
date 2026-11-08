
# -*- coding: utf-8 -*-
"""全库比对(修正版):
   1) 重建 track 列表: 列结构定稿的 columns+frames+content (sep/frame 角色) + others
      —— 与 load_tracks 同样的口径: (sep,frame,other) 三组, 按 x_mid 排序, gidx=1..N
      注意 load_tracks 的 others 来自 列判定.json 的 others, 列结构定稿也原样带了
   2) src->gidx: columns/frames/content 的 src 即列判定.json 的 separators 编号,
      重建时按 x 序对应
   3) 比对: 定稿当列线的 track, Agnes 判什么
"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'

def build(stem):
    cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
    cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
    seg={s['id']:s for s in cj['lines'] if s['direction']=='vertical' and s['label']=='high'}
    def xmid(ids):
        ids=[i for i in ids if i in seg]
        if not ids: return None
        pts=np.asarray([p for i in ids for p in seg[i]['points']],float)
        return float(np.median(pts[:,0]))
    # sep 组 = 列判定.json 的 separators = 列结构定稿的 columns+frames+content
    seps=[]
    for grp,role in (('columns','col'),('frames','frame'),('content','content')):
        for o in cs.get(grp) or []:
            xm=xmid(o.get('segment_ids') or [])
            if xm is None: continue
            seps.append({'role':role,'src':o.get('src'),'x_mid':xm,
                          'ids':frozenset(i for i in (o.get('segment_ids') or []) if i in seg)})
    others=[]
    for o in cs.get('others') or []:
        xm=xmid(o.get('track_ids') or [])
        if xm is None: continue
        others.append({'role':'other','src':None,'x_mid':xm,
                       'ids':frozenset(i for i in (o.get('track_ids') or []) if i in seg)})
    allt=seps+others
    allt.sort(key=lambda t:t['x_mid'])
    for i,t in enumerate(allt): t['gidx']=i+1
    return cs,allt

rowsall={}
for code in sorted(p.name.replace('_列结构定稿.json','')[-4:] for p in D.glob('*_列结构定稿.json')):
    stem='钻孔柱状图'+code
    cs,allt=build(stem)
    v=json.load(open(D/f'{stem}_全竖线判定.json',encoding='utf-8'))
    vm={int(k):x for k,x in v['merged_by_track'].items()}
    n_tr=v['n_tracks']
    cols=[t for t in allt if t['role']=='col']
    bad=[(t['src'],t['gidx'],vm.get(t['gidx'],'未判'),round(t['x_mid'],1)) for t in cols
         if vm.get(t['gidx'],'未判')!='column']
    agcol=set(g for g,x in vm.items() if x=='column')
    used=set(t['gidx'] for t in cols)
    miss=sorted(agcol-used)
    rowsall[code]={'n_rebuilt':len(allt),'n_tracks':n_tr,'n_cols':len(cols),
        'bad':bad,'agcol_not_used':miss,
        'n_agcol':len(agcol),
        'judged':{str(t['gidx']):vm.get(t['gidx'],'未判') for t in cols}}
json.dump(rowsall,open('runs/tmp/t6_final_vs_agnes.json','w',encoding='utf-8'),ensure_ascii=False,indent=1)
print('图     重建/总track  定稿列线  Agnes列线  定稿列线中Agnes非column   Agnes列线未采用')
for code in sorted(rowsall):
    o=rowsall[code]
    print('%-6s %4d/%-4d      %3d      %3d    %-24s %s'%(code,o['n_rebuilt'],o['n_tracks'],
        o['n_cols'],o['n_agcol'],
        ','.join('no%s/g%s=%s'%(b[0],b[1],b[2]) for b in o['bad']) or '-',
        ','.join(str(g) for g in o['agcol_not_used']) or '-'))

