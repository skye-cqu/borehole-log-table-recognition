
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1030'
rd=json.load(open(D/f'{stem}_行判定.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
y0,y1=4480,4830; x0,x1=140,1000
crop=cv2.cvtColor(gray[y0:y1,x0:x1],cv2.COLOR_GRAY2BGR)
cols={6:(0,0,255),7:(0,180,0),8:(255,0,0),9:(255,0,255),10:(0,140,255)}
for j,c in cols.items():
    r=rd['rows'][j]
    p=np.asarray(r['poly'],float)
    pts=np.asarray([[int(a-x0),int(b-y0)] for a,b in p if x0<=a<=x1],np.int32)
    if len(pts)>=2:
        cv2.polylines(crop,[pts],False,c,2)
        cv2.putText(crop,str(j),(int(pts[0][0])+4,int(pts[0][1])-4),cv2.FONT_HERSHEY_SIMPLEX,0.9,c,2)
cv2.imwrite(str(paths.RUNS_DIR/'tmp'/'t5crop_20261020'/'1030_rows_overlay.png'),crop)
print('ok',crop.shape)
