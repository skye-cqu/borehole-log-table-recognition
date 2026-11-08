
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1032'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
OUT=paths.RUNS_DIR/'tmp'/'t5crop_20261020'
# x 0..40 full column downsampled to see the cut edge
col=gray[1000:22050, 0:60]
h,w=col.shape
sc=2000.0/h
small=cv2.resize(col,(max(1,int(w*sc*6)),2000),interpolation=cv2.INTER_AREA)
cv2.imwrite(str(OUT/'1032_edgecol.png'),small)
print(small.shape)
