
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1030'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
# horizontal line profile in numeric zone x 280..960 (avoid era band and pattern)
seg=gray[4480:4820, 280:960]
prof=(seg<150).mean(axis=1)
print('y    frac')
for i,v in enumerate(prof):
    y=4480+i
    if v>0.25: print('  %d %.2f %s'%(y,v,'#'*int(v*70)))
