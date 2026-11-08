
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
OUT=paths.RUNS_DIR/'tmp'/'t5crop_20261020'; OUT.mkdir(parents=True,exist_ok=True)
for s,tgt in [('1030',4626.0),('1042',4660.0)]:
    stem='钻孔柱状图'+s
    hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
    rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
    midx=sum(rd['table_x'])/2.0
    rows=[r for r in rd['rows'] if row_y(r,midx)>=hm['band'][1]]
    ys=[row_y(r,midx) for r in rows]
    i=int(np.argmin([abs(y-tgt) for y in ys]))
    for j in range(max(0,i-2), min(len(rows),i+3)):
        print(s,'row',j,'y',round(ys[j],1),'poly x0..x1',round(min(p[0] for p in rows[j]['poly']),1),round(max(p[0] for p in rows[j]['poly']),1))
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    y0=int(max(0,ys[i]-260)); y1=int(min(gray.shape[0],ys[i]+260))
    x0=int(max(0,min(p[0] for p in rows[i]['poly'])-120)); x1=int(min(gray.shape[1],max(p[0] for p in rows[i]['poly'])+120))
    crop=gray[y0:y1,x0:x1].copy()
    # draw the two lines
    for j,col in [(i-1,(0,0,255)),(i,(0,255,0))]:
        if 0<=j<len(rows):
            pts=np.asarray([[int(px-x0),int(py-y0)] for px,py in rows[j]['poly']],np.int32)
            cv2.polylines(crop,[pts],False,col,3)
    cv2.imwrite(str(OUT/f'pf3_{s}_{int(tgt)}.png'),crop)
    print(' crop',crop.shape,'x',x0,x1,'y',y0,y1)
