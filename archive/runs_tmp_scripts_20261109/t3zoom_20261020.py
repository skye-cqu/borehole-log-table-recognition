
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1032'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
OUT=paths.RUNS_DIR/'tmp'/'t5crop_20261020'
for tag,y0,y1 in [('a',1271,1420),('b',3202,3400),('c',5003,5160)]:
    crop=gray[y0:y1, 0:200]
    crop=cv2.resize(crop,(200*4,(y1-y0)*4),interpolation=cv2.INTER_NEAREST)
    cv2.imwrite(str(OUT/f'1032_depth_{tag}.png'),crop)
    print(tag,crop.shape)
