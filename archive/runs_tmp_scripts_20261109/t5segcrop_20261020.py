
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1030'
cj=json.load(open(paths.CANDIDATE_COORD_DIR/f'{stem}.json',encoding='utf-8'))
seg={s['id']:s for s in cj['lines']}
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
OUT=paths.RUNS_DIR/'tmp'/'t5crop_20261020'
# region x 300..800 y 4680..4780
y0,y1,x0,x1=4680,4790,290,820
crop=cv2.cvtColor(gray[y0:y1,x0:x1],cv2.COLOR_GRAY2BGR)
crop=cv2.resize(crop,((x1-x0)*2,(y1-y0)*2),interpolation=cv2.INTER_NEAREST)
for sid,c in ((9463,(0,0,255)),(2376,(0,180,0)),(2393,(0,255,255)),(9390,(255,0,255)),(9448,(255,128,0))):
    s=seg.get(sid)
    if not s: continue
    a=np.asarray(s['points'],float)
    pts=np.asarray([[(p[0]-x0)*2,(p[1]-y0)*2] for p in a],np.int32)
    cv2.polylines(crop,[pts],False,c,2)
cv2.imwrite(str(OUT/'1030_seg9463.png'),crop)
print(crop.shape)
