
# -*- coding: utf-8 -*-
"""重建 no→gidx 映射: load_tracks 的口径 = (separators+frames+others) 按 x_mid 排序, gidx=序号+1。
   列结构定稿自带 columns/frames/content/others 的 segment_ids/track_ids, 可复原。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'

def rebuild(stem):
    cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
    cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
    seg={s['id']:s for s in cj['lines'] if s['direction']=='vertical' and s['label']=='high'}
    tracks=[]
    for c in cs['columns']:
        ids=[i for i in c.get('segment_ids') or [] if i in seg]
        if not ids: continue
        pts=np.asarray([p for i in ids for p in seg[i]['points']],float)
        tracks.append({'role_hint':'sep','src':c.get('src'),'ids':ids,
                        'x_mid':float(np.median(pts[:,0])),'y_min':float(pts[:,1].min())})
    for f in cs['frames']:
        ids=[i for i in f.get('segment_ids') or [] if i in seg]
        if not ids: continue
        pts=np.asarray([p for i in ids for p in seg[i]['points']],float)
        tracks.append({'role_hint':'frame','src':f.get('src'),'ids':ids,
                        'x_mid':float(np.median(pts[:,0])),'y_min':float(pts[:,1].min())})
    for o in cs.get('others') or []:
        ids=[i for i in (o.get('track_ids') or []) if i in seg]
        if not ids: continue
        pts=np.asarray([p for i in ids for p in seg[i]['points']],float)
        tracks.append({'role_hint':'other','src':'other%s'%o.get('span'),'ids':ids,
                        'x_mid':float(np.median(pts[:,0])),'y_min':float(pts[:,1].min())})
    tracks.sort(key=lambda t:t['x_mid'])
    for i,t in enumerate(tracks): t['gidx']=i+1
    return tracks

# 验证: 1015 分歧报告说 no=9 ↔ gidx=12
rep=json.load(open(D/'回收与分歧报告.json',encoding='utf-8'))
for code in ('1015','1023','1036'):
    stem='钻孔柱状图'+code
    tr=rebuild(stem)
    v=json.load(open(D/f'{stem}_全竖线判定.json',encoding='utf-8'))
    vm={int(k):x for k,x in v['merged_by_track'].items()}
    print('===',code,' 重建 track 数=%d (Agnes 全竖线判定 n_tracks=%d)'%(len(tr),v['n_tracks']))
    m={t['src']:t for t in tr}
    for t in tr:
        if t['role_hint']=='sep':
            print('   no=%-4s gidx=%-3d x_mid=%8.1f  Agnes=%s'%(t['src'],t['gidx'],t['x_mid'],vm.get(t['gidx'],'未判')))
    for dg in rep[code].get('disagreements') or []:
        g=dg['gidx']
        hit=[t for t in tr if t['gidx']==g]
        print('   [报告] no=%s ↔ gidx=%s base=%s agnes=%s x_mid=%s  重建: %s'%(
            dg['no'],g,dg['base'],dg['agnes'],dg['x_mid'],
            ('no=%s x_mid=%.1f'%(hit[0]['src'],hit[0]['x_mid'])) if hit else '未找到'))
    print()

