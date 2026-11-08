
# -*- coding: utf-8 -*-
"""终判: 异常段内, 右线偏离的那条"真格线"是否真实存在墨迹(说明是画到了旁边那条线)。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
cases=(('1019',3,8860,14330),('1023',8,8860,11040),('1031',7,9880,13440),
       ('1042',8,10790,16690),('1033',6,10030,18250))
for code,ridx,y0,y1 in cases:
    stem='钻孔柱状图'+code
    cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
    cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
    seg={s['id']:np.asarray(s['points'],float) for s in cj['lines'] if s['direction']=='vertical' and s['label']=='high'}
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    H,W=gray.shape
    bw=(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)>0).astype(np.uint8)
    vv=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))>0)
    c=[c for c in cs['columns'] if c['index']==ridx][0]
    fr=[]
    for i in c.get('segment_ids') or []:
        if i not in seg: continue
        p=seg[i]; fr.append((float(np.median(p[:,1])),float(np.median(p[:,0]))))
    fr.sort(); fy=np.array([a for a,_ in fr]); fx=np.array([b for _,b in fr])
    # 真实格线: 该图同时期存在、位于右线右侧 ~43px 的竖墨, 用 y 段内中位
    offs=[]
    n=0
    for y in range(y0+100,y1-100,60):
        if not (fy.min()<=y<=fy.max()): continue
        xr=float(np.interp(y,fy,fx))
        row=vv[max(0,y-12):y+13,:]
        col=row.mean(axis=0)
        idxs=np.flatnonzero(col>0.55)
        grp=[]
        for c0 in idxs:
            if grp and c0-grp[-1][-1]<=4: grp[-1].append(c0)
            else: grp.append([c0])
        inks=sorted(float(np.mean(g)) for g in grp)
        cand=[u for u in inks if 25<(u-xr)<70]
        if cand: offs.append(min(cand,key=lambda u:u-xr)); n+=1
    if offs:
        print('%-6s 列%-2d 异常段: 右线右侧始终另有竖墨, 中位距离 %+.1fpx  (采样 %d 点, 覆盖率 %d/%d)'%(
            code,ridx,float(np.median(offs)),n,len(list(range(y0+100,y1-100,60)))))
    else:
        print('%-6s 列%-2d 异常段: 右侧未找到平行竖墨(不是换线)'%(code,ridx))

