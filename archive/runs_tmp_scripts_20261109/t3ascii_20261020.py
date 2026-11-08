
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1032'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
# What's in x=0..20? Print a tiny ascii map at a few rows
for y0,y1,label in [(1271,1365,'row1'),(3202,3358,'row3'),(10421,10497,'row28')]:
    print('===',label,y0,y1)
    sub=(gray[y0:y1, 0:120]<150)
    for r in range(0,sub.shape[0],max(1,sub.shape[0]//12)):
        print('  y%5d '%(y0+r)+''.join('#' if v else '.' for v in sub[r]))
