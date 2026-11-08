
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
OUT=paths.RUNS_DIR/'tmp'/'t5crop_20261020'
stem='钻孔柱状图1019'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
crop=gray[700:1200, 180:1200]
cv2.imwrite(str(OUT/'1019_header.png'),crop)
print(crop.shape)
