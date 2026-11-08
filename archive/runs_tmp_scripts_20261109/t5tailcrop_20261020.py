
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'
OUT=paths.RUNS_DIR/'tmp'/'t5crop_20261020'
for s,y0,y1,x0,x1 in [('1029',20250,20520,150,420),('1032',21080,21860,0,700),('1017',9150,9450,120,450)]:
    stem='钻孔柱状图'+s
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    H,W=gray.shape
    crop=gray[max(0,y0):min(H,y1), max(0,x0):min(W,x1)]
    h,w=crop.shape
    if h<200: crop=cv2.resize(crop,(w*3,h*3),interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(str(OUT/f'tail_{s}.png'),crop)
    print(s,crop.shape)
