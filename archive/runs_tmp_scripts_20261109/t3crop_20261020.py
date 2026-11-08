
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1032'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
print('H,W',H,W)
OUT=paths.RUNS_DIR/'tmp'/'t5crop_20261020'
crop=gray[900:2200, 0:900]
cv2.imwrite(str(OUT/'1032_left.png'),crop)
print(crop.shape)
