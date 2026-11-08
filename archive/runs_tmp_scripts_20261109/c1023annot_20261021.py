
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
OUT=paths.RUNS_DIR/'tmp'/'t5crop_20261021'
stem='钻孔柱状图1023'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
xs=hm['sep_x_band']
names=[c['name'] for c in hm['keep']]
y0,y1=560,1560
x0,x1=int(xs[0])-10,int(xs[8])+10
crop=cv2.cvtColor(gray[y0:y1,x0:x1],cv2.COLOR_GRAY2BGR)
# annotate column names at top
for i,nm in enumerate(names):
    l=int(xs[i])-x0; r=int(xs[i+1])-x0
    cv2.putText(crop,nm,(max(0,l+4),24),cv2.FONT_HERSHEY_SIMPLEX,0.55,(0,0,255),2)
    cv2.line(crop,(l,0),(l,crop.shape[0]),(255,0,0),2)
crop=cv2.resize(crop,(crop.shape[1]*2,crop.shape[0]*2),interpolation=cv2.INTER_CUBIC)
cv2.imwrite(str(OUT/'1023_annot.png'),crop)
print('annot',crop.shape,'x',x0,x1,'y',y0,y1)
