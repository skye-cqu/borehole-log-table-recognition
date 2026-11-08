
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1030'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
# era band x 197..261 ; is there horizontal ink at y=4766 and 4695?
for y in [4694,4695,4696,4765,4766,4767]:
    seg=gray[y,197:261]
    print('y=%d ink=%d xs=%s'%(y,int((seg<150).sum()),[197+int(k) for k in np.where(seg<150)[0][:12]]))
# wider: x 184..400
print('--- wider x 184..420')
for y in [4694,4695,4696,4765,4766,4767]:
    seg=gray[y,184:420]
    dk=np.where(seg<150)[0]
    print('y=%d ink=%d xs=%s'%(y,len(dk),[184+int(k) for k in dk[:20]]))
