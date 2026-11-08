
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
# for each sep polyline, measure distance to nearest vertical ink at sampled y
def nearest_ink_x(y, x_pred, half=30, win=40):
    b=gray[max(0,y-win):y+win, max(0,int(x_pred)-half):int(x_pred)+half]
    if b.size==0: return None
    dark=(b<160).mean(axis=0)
    k=int(np.argmax(dark))
    if dark[k]<0.5: return None
    return float(max(0,int(x_pred)-half)+k)
res=[]
for i,sp in enumerate(hm['sep_pts']):
    ys=np.asarray(sp['ys'],float); xs=np.asarray(sp['xs'],float)
    ds=[]
    for y in np.linspace(ys.min()+50, ys.max()-50, 25):
        xp=float(np.interp(y,ys,xs))
        xk=nearest_ink_x(y,xp)
        if xk is not None: ds.append(abs(xk-xp))
    if ds:
        res.append((i,sp.get('kind'),len(ds),float(np.median(ds)),float(np.percentile(ds,90)),float(max(ds))))
print('sep  kind    n   median  p90    max   (px 偏差:折线 vs 原图墨线)')
for r in res:
    print(' #%-3d %-7s %3d  %6.2f %6.2f %6.2f'%r)
