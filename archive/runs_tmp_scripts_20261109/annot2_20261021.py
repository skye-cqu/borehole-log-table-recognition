
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
OUT=paths.RUNS_DIR/'tmp'/'t5crop_20261021'
stem='钻孔柱状图1023'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
names=[c['name'] for c in hm['keep']]
y0,y1=520,1560
x0,x1=170,1010
crop=cv2.cvtColor(gray[y0:y1,x0:x1],cv2.COLOR_GRAY2BGR)
crop=cv2.resize(crop,((x1-x0)*2,(y1-y0)*2),interpolation=cv2.INTER_CUBIC)
# draw TRUE polylines from sep_pts (correct way)
for c in hm['keep']:
    for key in ('left_sep',):
        i=c[key]
        if not (0<=i<len(hm['sep_pts'])): continue
        sp=hm['sep_pts'][i]
        ys=np.asarray(sp['ys'],float); xs=np.asarray(sp['xs'],float)
        m=(ys>=y0)&(ys<=y1)
        pts=np.asarray([[(x-x0)*2,(y-y0)*2] for x,y in zip(xs[m],ys[m])],np.int32)
        if len(pts)>=2: cv2.polylines(crop,[pts],False,(0,0,255),2)
# right edge of last column
i=hm['keep'][-1]['right_sep']
if 0<=i<len(hm['sep_pts']):
    sp=hm['sep_pts'][i]
    ys=np.asarray(sp['ys'],float); xs=np.asarray(sp['xs'],float)
    m=(ys>=y0)&(ys<=y1)
    pts=np.asarray([[(x-x0)*2,(y-y0)*2] for x,y in zip(xs[m],ys[m])],np.int32)
    if len(pts)>=2: cv2.polylines(crop,[pts],False,(0,0,255),2)
for i,nm in enumerate(names):
    sp=hm['sep_pts'][hm['keep'][i]['left_sep']]
    yy=float(np.interp(y0+40,sp['ys'],sp['xs']))
    cv2.putText(crop,nm,(int((yy-x0)*2)+4,26),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,140,0),2)
cv2.imwrite(str(OUT/'1023_annot_v2.png'),crop)
print('ok',crop.shape)
