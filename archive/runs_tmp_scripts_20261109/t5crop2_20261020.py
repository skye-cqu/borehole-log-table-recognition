
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
OUT=paths.RUNS_DIR/'tmp'/'t5crop_20261020'
for s,ya,yb,xa,xb,name in [
  ('1017',9000,10183,0,900,'wide'),
  ('1020',17900,19080,150,900,'wide'),
]:
    stem='钻孔柱状图'+s
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    H,W=gray.shape
    crop=gray[max(0,ya):min(H,yb), max(0,xa):min(W,xb)]
    h,w=crop.shape
    if h>2000:
        sc=2000.0/h; crop=cv2.resize(crop,(int(w*sc),2000),interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(OUT/f'{s}_{name}_{ya}-{yb}.png'),crop)
    print(s,crop.shape)
