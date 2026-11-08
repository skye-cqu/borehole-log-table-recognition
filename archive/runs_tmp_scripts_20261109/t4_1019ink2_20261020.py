
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1019'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
print('H,W',H,W)
for y in [1200,2500,4000,5500,7000,8500,10000,12000,14000,16000,17400]:
    b=gray[y-30:y+30,:]
    dark=(b<160).mean(axis=0)
    cols=[i for i in range(1,len(dark)-1) if dark[i]>0.55 and dark[i]>=dark[i-1] and dark[i]>=dark[i+1]]
    grp=[]
    for c in cols:
        if grp and c-grp[-1][-1]<=3: grp[-1].append(c)
        else: grp.append([c])
    cen=[round(sum(g)/len(g),1) for g in grp if len(g)<=12]
    print('y=%5d x<700: %s'%(y,[c for c in cen if c<700]))
