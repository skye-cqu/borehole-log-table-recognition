
# -*- coding: utf-8 -*-
"""验证: 这些间距异常处, 相邻两条线各自贴的是不是"另一条平行线"。
   判据: 异常段里, 右线相对左线的偏移, 是否恰好等于某条真实竖墨线的位置。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
for code,cols,y0,y1 in (('1019',(2,3),8860,14330),('1023',(7,8),8860,11040),
                        ('1031',(6,7),9880,13440),('1042',(7,8),10790,16690)):
    stem='钻孔柱状图'+code
    cs=json.load(open(D/f'{stem}_列结构定稿.json',encoding='utf-8'))
    cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
    seg={s['id']:np.asarray(s['points'],float) for s in cj['lines'] if s['direction']=='vertical' and s['label']=='high'}
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    H,W=gray.shape
    bw=(cv2.adaptiveThreshold(gray,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY_INV,31,12)>0).astype(np.uint8)
    vv=(cv2.morphologyEx(bw*255,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_RECT,(1,40)))>0)
    def line_of(idx):
        c=[c for c in cs['columns'] if c['index']==idx][0]
        fr=[]
        for i in c.get('segment_ids') or []:
            if i not in seg: continue
            p=seg[i]; fr.append((float(np.median(p[:,1])),float(np.median(p[:,0]))))
        fr.sort()
        return np.array([a for a,_ in fr]), np.array([b for _,b in fr])
    ya,xa=line_of(cols[0]); yb,xb=line_of(cols[1])
    print('=== %s 列%d→%d  y[%d,%d] ==='%(code,cols[0],cols[1],y0,y1))
    for y in (y0+200,(y0+y1)//2,y1-200):
        if not (ya.min()<=y<=ya.max() and yb.min()<=y<=yb.max()): continue
        xa_=float(np.interp(y,ya,xa)); xb_=float(np.interp(y,yb,xb))
        # 该 y 附近所有真竖墨
        row=vv[max(0,y-12):y+13,:]
        col=row.mean(axis=0)
        idxs=np.flatnonzero(col>0.55); grp=[]
        for c0 in idxs:
            if grp and c0-grp[-1][-1]<=4: grp[-1].append(c0)
            else: grp.append([c0])
        inks=[round(float(np.mean(g)),1) for g in grp]
        near=lambda x: min(inks,key=lambda u:abs(u-x)) if inks else None
        print('   y=%6d 左线=%.1f(%s)  右线=%.1f(%s)  该行竖墨=%s'%(
            y,xa_,near(xa_),xb_,near(xb_),[i for i in inks if abs(i-xa_)<160 or abs(i-xb_)<160]))
    print()

