
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
from src.table.track_rows import row_y
D=paths.RUNS_DIR/'table_reconstruct'

def hprof(gray, x0, x1, ya, yb):
    sub=gray[int(ya):int(yb), int(x0):int(x1)]
    return (sub<160).mean(axis=1)

for s,tgt,x0,x1 in [('1030',4626.0,252,763),('1042',4660.0,240,595)]:
    stem='钻孔柱状图'+s
    gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
    p=hprof(gray,x0,x1,tgt-30,tgt+30)
    print('===',s,'x',x0,x1)
    for i,v in enumerate(p):
        y=int(tgt-30)+i
        print('   y=%d dark=%.2f %s'%(y,v,'#'*int(v*60)))
