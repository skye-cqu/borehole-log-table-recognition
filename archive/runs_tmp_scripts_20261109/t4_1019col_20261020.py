
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1019'
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
# vertical ink column census in x<520 at several y
def cols_at(y, half=40, thr=0.6):
    b=gray[max(0,y-half):y+half,:520]
    dark=(b<160).mean(axis=0)
    idx=[i for i in range(1,len(dark)-1) if dark[i]>thr and dark[i]>=dark[i-1] and dark[i]>=dark[i+1]]
    grp=[]
    for c in idx:
        if grp and c-grp[-1][-1]<=3: grp[-1].append(c)
        else: grp.append([c])
    return [round(sum(g)/len(g),1) for g in grp if len(g)<=14]
for y in [900,1100,1300,1600,2000,3000,5000,8000,11000,12000,13000,15000,17000]:
    print('y=%5d  %s'%(y,cols_at(y)))
print()
# header band 732..934
b=gray[732:934,:520]
dens=(b<150).sum(axis=0)
bh=934-732
strokes=[]
i=0
while i<len(dens):
    if dens[i]>=0.6*bh:
        j=i
        while j<len(dens) and dens[j]>=0.6*bh: j+=1
        strokes.append((i,j-1,int(dens[i:j].max())))
        i=j
    else: i+=1
print('header full-height strokes (x0,x1,peak):',strokes)
