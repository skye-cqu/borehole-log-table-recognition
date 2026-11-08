
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1032'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
# per-column dark fraction over the whole table area
frac=(gray[1000:21850, :150]<150).mean(axis=0)
for x in range(0,150):
    if frac[x]>0.05: print('x=%3d frac=%.3f'%(x,frac[x]))
