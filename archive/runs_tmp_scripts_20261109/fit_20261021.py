
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
print('sep_pts 各条在若干 y 处 vs 原图竖线位置')
# vertical ink census at several y
def cols_at(y,half=25,thr=0.6,xmax=1100):
    b=gray[max(0,y-half):y+half,:xmax]
    dark=(b<160).mean(axis=0)
    idx=[i for i in range(1,len(dark)-1) if dark[i]>thr and dark[i]>=dark[i-1] and dark[i]>=dark[i+1]]
    grp=[]
    for c in idx:
        if grp and c-grp[-1][-1]<=3: grp[-1].append(c)
        else: grp.append([c])
    return [round(sum(g)/len(g),1) for g in grp if len(g)<=14]
for y in [700,900,1200,1500]:
    ink=cols_at(y)
    poly=[]
    for i,sp in enumerate(hm['sep_pts']):
        ys=np.asarray(sp['ys'],float); xs=np.asarray(sp['xs'],float)
        if ys.min()<=y<=ys.max():
            poly.append((i,round(float(np.interp(y,ys,xs)),1)))
    print('y=%4d ink=%s'%(y,ink))
    print('       poly=%s'%poly)
