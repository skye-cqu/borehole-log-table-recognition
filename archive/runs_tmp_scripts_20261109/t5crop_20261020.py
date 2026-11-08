
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
OUT=paths.RUNS_DIR/'tmp'/'t5crop_20261020'; OUT.mkdir(parents=True,exist_ok=True)
cases=[('1017',9259,9863,290),('1020',18270,18810,415),('1023',11443,11929,332),('1025',13777,17730,259),('1028',14572,17221,210)]
for s,ya,yb,px in cases:
    stem='钻孔柱状图'+s
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    H,W=gray.shape
    y0=max(0,ya-80); y1=min(H,yb+80)
    x0=max(0,int(px)-320); x1=min(W,int(px)+320)
    crop=gray[y0:y1,x0:x1]
    # downsample tall crops to <=2400px
    h,w=crop.shape
    if h>2400:
        sc=2400.0/h
        crop=cv2.resize(crop,(int(w*sc),2400),interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(OUT/f'{s}_{ya}-{yb}.png'),crop)
    print(s,'crop',crop.shape,'x',x0,x1,'y',y0,y1)
