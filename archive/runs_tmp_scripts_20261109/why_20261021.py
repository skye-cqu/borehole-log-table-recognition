
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
D=paths.RUNS_DIR/'table_reconstruct'
stem='钻孔柱状图1023'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
# my earlier naive measure: nearest column with dark fraction >0.5 within +-30
def naive(y,x_pred,half=30,win=40):
    y=int(y); x0=max(0,int(x_pred)-half); x1=min(W,int(x_pred)+half)
    b=gray[max(0,y-win):min(H,y+win), x0:x1]
    if b.size==0: return None
    dark=(b<160).mean(axis=0)
    k=int(np.argmax(dark))
    if dark[k]<0.5: return None
    return float(x0+k)
sp=hm['sep_pts'][10]
ys=np.asarray(sp['ys'],float); xs=np.asarray(sp['xs'],float)
print('sep#10 (right edge) y range',ys.min(),ys.max())
bad=[]
for y in np.linspace(ys.min()+50,ys.max()-50,25):
    xp=float(np.interp(y,ys,xs)); xk=naive(y,xp)
    if xk is not None and abs(xk-xp)>5: bad.append((round(y),round(xp,1),xk,round(abs(xk-xp),1)))
print('naive-measure outliers:',len(bad))
for b in bad: print('   y=%d pred=%.1f found=%.1f diff=%.1f'%b)
print()
print('raw pixel check near the outlier:')
if bad:
    y,pred,found,_=bad[0]
    seg=gray[y-2:y+3, int(pred)-40:int(pred)+40]
    print('  row y=%d gray min per col (x offset from %d):'%(y,int(pred)-40))
    print('  ',[int(seg[:,i].min()) for i in range(0,80,4)])
