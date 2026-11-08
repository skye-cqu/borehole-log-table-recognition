
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1030'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
for y0 in [4693,4694,4695,4696,4697, 4764,4765,4766,4767,4768]:
    seg=gray[y0, 260:960]
    dk=(seg<150)
    # fraction of columns dark
    print('y=%d dark_frac=%.3f  n=%d'%(y0, dk.mean(), dk.sum()))
print()
# horizontal run structure at 4695 and 4766
for y0 in [4695, 4766]:
    seg=(gray[y0, 200:1000]<150).astype(int)
    runs=[];s=None
    for i,v in enumerate(seg):
        if v and s is None: s=i
        elif not v and s is not None: runs.append((200+s,200+i-1)); s=None
    if s is not None: runs.append((200+s,999))
    print('y=%d runs=%s'%(y0,runs))
