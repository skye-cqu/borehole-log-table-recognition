
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1032'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
for y0,y1,label in [(3358,5003,'row4 read55.17'),(3202,3358,'row5 read9.14'),(6705,6932,'row9 read9.86')]:
    sub=(gray[y0+4:y1-4, 0:120]<150)
    print('===',label,y0,y1,'ink in x<8:',int(sub[:,:8].sum()))
    for r in range(0,min(sub.shape[0],40),3):
        print('  y%5d '%(y0+4+r)+''.join('#' if v else '.' for v in sub[r]))
