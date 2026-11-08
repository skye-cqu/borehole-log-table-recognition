
# -*- coding: utf-8 -*-
"""定位 fit3 那两处离群: sep#8 的 4px, sep#10 的 27px。逐点打印。"""
import sys,json; sys.path.insert(0,'.')
import numpy as np, cv2
from src.core import paths
stem='钻孔柱状图1023'
D=paths.RUNS_DIR/'table_reconstruct'
hm=json.load(open(D/f'{stem}_表头映射.json',encoding='utf-8'))
gray=cv2.imread(str(paths.RAW_DIR/f'{stem}.JPG'),cv2.IMREAD_GRAYSCALE)
H,W=gray.shape
def nearest_ink_x(y,x_pred,half=30,win=40):
    y=int(y); x0=max(0,int(x_pred)-half); x1=min(W,int(x_pred)+half)
    b=gray[max(0,y-win):min(H,y+win), x0:x1]
    if b.size==0: return None,None
    dark=(b<160).mean(axis=0)
    k=int(np.argmax(dark))
    return (float(x0+k) if dark[k]>=0.5 else None), float(dark[k])
for idx in (8,10):
    sp=hm['sep_pts'][idx]
    ys=np.asarray(sp['ys'],float); xs=np.asarray(sp['xs'],float)
    print(f'===== sep#{idx} kind={sp.get("kind")}')
    for y in np.linspace(ys.min()+50, ys.max()-50, 25):
        xp=float(np.interp(y,ys,xs))
        xk,dk=nearest_ink_x(y,xp)
        flag='  <<<' if (xk is not None and abs(xk-xp)>3) or xk is None else ''
        print(f'   y={y:7.0f} pred={xp:8.1f} found={("None" if xk is None else f"{xk:8.1f}")} dark={dk:.2f} diff={("n/a" if xk is None else f"{xk-xp:+7.1f}")}{flag}')

