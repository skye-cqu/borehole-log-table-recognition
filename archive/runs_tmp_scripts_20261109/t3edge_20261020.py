
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1032'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
# column dark fraction over full height for x<130
frac=(gray[:, :130]<160).mean(axis=0)
for x in range(0,130):
    if frac[x]>0.3: print('x=%3d frac=%.3f'%(x,frac[x]))
print()
# per row: leftmost dark pixel in x 20..100 (skip border)
for y0,y1 in [(1271,1365),(3202,3358),(5003,5136),(1365,3202)]:
    sub=gray[y0+4:y1-4, 0:100]
    dk=(sub<150)
    cols=np.where(dk.any(axis=0))[0]
    print('y %d-%d -> dark cols %s'%(y0,y1,list(cols[:12])))
