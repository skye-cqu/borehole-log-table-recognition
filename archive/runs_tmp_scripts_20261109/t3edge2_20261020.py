
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1032'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
# check what is at x 0..3 across whole image: is it a continuous vertical line?
col=(gray[1000:21850, 0:4]<150)
print('col 0-3 dark frac per row range:')
for y0 in range(1000,21850,2000):
    seg=col[y0-1000:y0-1000+2000]
    print('  y%5d-%-5d frac=%.3f'%(y0,y0+2000,seg.mean()))
print()
# row 1239-1251 has ink at x~23 -> that's the digit
print('so digits start around x=20-90; x=0..3 has sporadic ink')
print('ink at x 0..3 count per row (only rows with >0):')
rows=np.where((gray[1000:21850, 0:4]<150).any(axis=1))[0]
print('rows with edge ink:',len(rows),'of',21850-1000)
print('first 20:',list(rows[:20]))
