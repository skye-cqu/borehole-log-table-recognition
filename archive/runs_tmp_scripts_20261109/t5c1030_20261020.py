
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1030'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
crop=gray[4500:4850, 140:900]
cv2.imwrite(str(paths.RUNS_DIR/'tmp'/'t5crop_20261020'/'1030_rows8_9.png'),crop)
print(crop.shape)
# ink profile of era band x 197..261
band=gray[4400:4900, 197:261]
prof=(band<150).sum(axis=1)
for i,v in enumerate(prof):
    y=4400+i
    if v>0: print(' y=%d ink=%d'%(y,v))
